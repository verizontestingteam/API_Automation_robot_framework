import json


def validate_response_status(response, expected_status=200):
    status_code = getattr(response, "status_code", None)
    if status_code is None:
        raise AssertionError("Response object does not contain a status_code value.")
    if int(status_code) != int(expected_status):
        raise AssertionError(
            f"Expected HTTP status {expected_status}, but got {status_code}. Response: {getattr(response, 'text', '')}"
        )


def validate_json_has_keys(response, expected_keys):
    if isinstance(expected_keys, str):
        expected_keys = [expected_keys]

    payload = _get_json_payload(response)
    missing = [key for key in expected_keys if key not in payload]
    if missing:
        raise AssertionError(f"Response JSON missing keys: {missing}. Payload: {payload}")


def validate_response_not_empty(response):
    text = getattr(response, "text", "")
    if text is None or str(text).strip() == "":
        raise AssertionError("Response body is empty.")


def validate_response_time(response, max_milliseconds=500):
    elapsed = getattr(response, "elapsed", None)
    if elapsed is None:
        raise AssertionError("Response timing is unavailable. Cannot validate response time.")

    try:
        duration_ms = elapsed.total_seconds() * 1000
    except AttributeError:
        try:
            duration_ms = float(elapsed) * 1000
        except (TypeError, ValueError):
            raise AssertionError(f"Unable to parse response elapsed time: {elapsed}")

    if duration_ms > float(max_milliseconds):
        raise AssertionError(
            f"Response took {duration_ms:.0f}ms, exceeding the allowed {max_milliseconds}ms."
        )


def validate_response_fields(response, *fields):
    payload = _get_json_payload(response)
    missing = [field for field in fields if not _field_exists_in_payload(payload, field)]
    if missing:
        raise AssertionError(f"Response JSON missing fields: {missing}. Payload: {payload}")


def _field_exists_in_payload(payload, field_name):
    if field_name is None:
        return False

    field_name = str(field_name).strip()
    if not field_name:
        return True

    path = field_name.split('.')

    def _exists(current, parts):
        if not parts:
            return True

        part = parts[0]

        if isinstance(current, list):
            return any(_exists(item, parts) for item in current if isinstance(item, (dict, list)))

        if not isinstance(current, dict):
            return False

        if part not in current:
            return False

        return _exists(current[part], parts[1:])

    if isinstance(payload, list):
        return any(_exists(item, path) for item in payload)

    return _exists(payload, path)


def validate_response_headers(response, header_name, expected_value=None):
    headers = getattr(response, "headers", {}) or {}
    # Case-insensitive header lookup
    matched_value = None
    for k, v in headers.items():
        if k.casefold() == str(header_name).casefold():
            matched_value = v
            break

    if matched_value is None:
        raise AssertionError(
            f"Expected header '{header_name}' was not found in response headers: {dict(headers)}"
        )

    if expected_value is not None and str(expected_value).casefold() not in str(matched_value).casefold():
        raise AssertionError(
            f"Expected header '{header_name}' to contain '{expected_value}', but got '{matched_value}'"
        )


def validate_root_offering_channels(response, requested_channel):
    validate_response_status(response, 200)
    if not requested_channel or not str(requested_channel).strip():
        raise AssertionError("Requested channel must not be empty.")

    payload = _get_json_payload(response)
    offerings = _get_product_offerings(payload)
    if not offerings:
        raise AssertionError(f"No product offerings found to validate root channels for '{requested_channel}'.")

    invalid_root_offerings = []
    expected_channel = str(requested_channel).strip().casefold()

    for idx, offering in enumerate(offerings):
        if not isinstance(offering, dict):
            invalid_root_offerings.append(f"Root item {idx} is not an object.")
            continue

        offering_code = offering.get("code", offering.get("id", f"item_{idx}"))
        channels, issue = _get_available_channels(offering)
        normalized = {c.casefold() for c in channels}

        if issue or expected_channel not in normalized:
            display_channels = ", ".join(channels) or "<none>"
            if issue:
                display_channels = f"{display_channels} ({issue})"
            invalid_root_offerings.append(
                f"Root offering code={offering_code!r} missing requested channel '{requested_channel}'. Available: [{display_channels}]"
            )

    if invalid_root_offerings:
        details = "\n".join(f"- {failure}" for failure in invalid_root_offerings)
        raise AssertionError(
            f"Root product offering channel validation failed for '{requested_channel}':\n{details}"
        )


def validate_product_offering_schema(response):
    payload = _get_json_payload(response)
    offerings = _get_product_offerings(payload)

    mandatory_fields = ["id", "code", "name"]
    for idx, offering in enumerate(offerings):
        if not isinstance(offering, dict):
            raise AssertionError(f"Product offering item {idx} must be a dictionary object.")

        offering_code = offering.get("code", offering.get("id", f"item_{idx}"))
        missing = [field for field in mandatory_fields if field not in offering or offering[field] is None]
        if missing:
            raise AssertionError(
                f"Product offering {offering_code!r} is missing mandatory schema fields: {missing}"
            )

        if "lifecycleStatus" in offering and offering["lifecycleStatus"] is not None:
            status = str(offering["lifecycleStatus"]).strip()
            valid_statuses = {"active", "launched", "in study", "in-study", "in design", "indesign"}
            if status.casefold() not in valid_statuses:
                raise AssertionError(
                    f"Product offering {offering_code!r} has invalid or inactive lifecycleStatus: {status!r}"
                )


def validate_product_offering_prices(response, expected_channel=None):
    payload = _get_json_payload(response)
    offerings = _get_product_offerings(payload)

    for idx, offering in enumerate(offerings):
        if not isinstance(offering, dict):
            continue
        offering_code = offering.get("code", f"item_{idx}")
        prices = offering.get("productOfferingPrice", [])
        if prices is None:
            continue
        if not isinstance(prices, list):
            raise AssertionError(f"Product offering {offering_code!r} productOfferingPrice must be a list.")

        for p_idx, price in enumerate(prices):
            if not isinstance(price, dict):
                raise AssertionError(f"Price entry {p_idx} under offering {offering_code!r} is not an object.")

            if "price" in price and isinstance(price["price"], dict):
                price_val = price["price"].get("value")
                if price_val is not None:
                    try:
                        if float(price_val) < 0:
                            raise AssertionError(
                                f"Price value under offering {offering_code!r} cannot be negative: {price_val}"
                            )
                    except (ValueError, TypeError):
                        raise AssertionError(
                            f"Price value under offering {offering_code!r} is non-numeric: {price_val!r}"
                        )

            if expected_channel:
                _assert_channel_present(
                    price.get("channel"),
                    str(expected_channel).strip().casefold(),
                    f"Price under offering {offering_code!r}",
                )


def validate_product_offering_validity(response):
    from datetime import datetime

    payload = _get_json_payload(response)
    offerings = _get_product_offerings(payload)
    now = datetime.now()

    for idx, offering in enumerate(offerings):
        if not isinstance(offering, dict):
            continue
        valid_for = offering.get("validFor")
        if not isinstance(valid_for, dict):
            continue

        offering_code = offering.get("code", f"item_{idx}")
        start_str = valid_for.get("startDateTime")
        end_str = valid_for.get("endDateTime")

        if start_str and isinstance(start_str, str):
            try:
                # Basic ISO format parse check
                start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=now.tzinfo)
            except ValueError:
                pass

        if end_str and isinstance(end_str, str):
            try:
                end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
            except ValueError:
                pass


def validate_invalid_channel_response(response, requested_channel):
    status_code = int(getattr(response, "status_code", 0))
    if status_code == 404:
        return
    if status_code == 200:
        payload = _get_json_payload(response)
        offerings = []
        if isinstance(payload, list):
            offerings = payload
        elif isinstance(payload, dict):
            items = payload.get("items")
            if isinstance(items, list):
                offerings = items
        if not offerings:
            return
        raise AssertionError(
            f"Expected empty offerings list or 404 for invalid channel '{requested_channel}', but got {len(offerings)} item(s)."
        )
    raise AssertionError(
        f"Expected status 404 or 200 for invalid channel query, but got status {status_code}."
    )


def validate_unauthorized_response(response):
    status_code = int(getattr(response, "status_code", 0))
    if status_code not in (401, 403):
        raise AssertionError(f"Expected HTTP status 401 or 403 for unauthorized request, but got {status_code}.")


def validate_product_offering_response(
    response, related_party=None, code=None, depth=None, category_name=None, channel_name=None
):
    validate_response_status(response, 200)
    validate_response_not_empty(response)
    validate_response_headers(response, "Content-Type", "application/json")

    payload = _get_json_payload(response)
    offerings = _get_product_offerings(payload)
    if not offerings:
        raise AssertionError(f"No product offerings returned for code {code!r}.")

    validate_product_offering_schema(response)
    validate_product_offering_prices(response, expected_channel=channel_name)
    validate_product_offering_validity(response)

    for offering in offerings:
        if not isinstance(offering, dict):
            raise AssertionError(f"Product offering entry must be an object, got: {type(offering).__name__}")

        actual_code = offering.get("code")
        if code and actual_code != code:
            raise AssertionError(f"Unexpected product code: {actual_code!r}. Expected: {code!r}")

        if related_party:
            _validate_related_party(offering.get("relatedParty"), related_party, actual_code)

        if category_name:
            _validate_category(offering.get("category"), category_name, actual_code)

        if channel_name:
            _validate_offering_channels([offering], channel_name)


def validate_requested_product_offering_channels(response, requested_channel):
    validate_response_status(response, 200)
    if not requested_channel or not str(requested_channel).strip():
        raise AssertionError("Requested channel must not be empty.")

    payload = _get_json_payload(response)
    offerings = _get_product_offerings(payload)
    if not offerings:
        raise AssertionError("No product offerings found for strict channel filtering validation.")

    expected_channel = str(requested_channel).strip()
    failures = []
    for index, offering in enumerate(offerings):
        if not isinstance(offering, dict):
            failures.append(
                _strict_channel_failure(
                    expected_channel,
                    "<invalid offering>",
                    "<unknown>",
                    "GroupProductOffering.@type",
                    f"root offering {index} is not an object",
                )
            )
            continue

        _validate_strict_offering_channels(
            offering,
            expected_channel,
            failures,
            expected_type="GroupProductOffering",
        )

    if failures:
        details = "\n".join(f"- {failure}" for failure in failures)
        raise AssertionError(
            f"Strict channel filtering validation failed for requested channel "
            f"'{expected_channel}':\n{details}"
        )


def _validate_strict_offering_channels(
    offering, expected_channel, failures, expected_type=None
):
    offering_type = offering.get("@type")
    offering_code = offering.get("code", offering.get("id", "<unknown>"))
    supported_types = {"GroupProductOffering", "SimpleProductOffering"}

    if expected_type and offering_type != expected_type:
        failures.append(
            _strict_channel_failure(
                expected_channel,
                "<not applicable>",
                offering_code,
                offering_type,
                "@type",
                f"expected {expected_type!r}, got {offering_type!r}",
            )
        )
    elif offering_type not in supported_types:
        failures.append(
            _strict_channel_failure(
                expected_channel,
                "<not applicable>",
                offering_code,
                offering_type,
                "@type",
                f"expected one of {sorted(supported_types)!r}, got {offering_type!r}",
            )
        )
        return 0

    _validate_exact_channel_names(
        offering.get("channel"),
        expected_channel,
        offering_code,
        offering_type,
        f"{offering_type or expected_type}.channel.name",
        failures,
    )
    _validate_strict_price_channels(
        offering,
        expected_channel,
        offering_type,
        failures,
        require_prices=offering_type == "SimpleProductOffering",
    )

    simple_offering_count = 0
    if offering_type == "GroupProductOffering" or "bundledProductOffering" in offering:
        bundled = offering.get("bundledProductOffering", [])
        if not isinstance(bundled, list):
            failures.append(
                _strict_channel_failure(
                    expected_channel,
                    repr(bundled),
                    offering_code,
                    offering_type,
                    "bundledProductOffering",
                    "bundledProductOffering must be a list",
                )
            )
            return simple_offering_count
        if offering_type == "GroupProductOffering" and not bundled:
            failures.append(
                _strict_channel_failure(
                    expected_channel,
                    "<missing>",
                    offering_code,
                    offering_type,
                    "bundledProductOffering",
                    "GroupProductOffering has no corresponding bundled offering.",
                )
            )
            return simple_offering_count

        for index, child in enumerate(bundled):
            if not isinstance(child, dict):
                failures.append(
                    _strict_channel_failure(
                        expected_channel,
                        "<invalid offering>",
                        offering_code,
                        "<unknown>",
                        "bundledProductOffering.@type",
                        f"bundled item {index} is not an object",
                    )
                )
                continue
            simple_offering_count += _validate_strict_offering_channels(
                child,
                expected_channel,
                failures,
            )
        if offering_type == "GroupProductOffering" and simple_offering_count == 0:
            failures.append(
                _strict_channel_failure(
                    expected_channel,
                    "<missing>",
                    offering_code,
                    offering_type,
                    "bundledProductOffering.SimpleProductOffering",
                    "GroupProductOffering has no corresponding SimpleProductOffering.",
                )
            )

    return 1 if offering_type == "SimpleProductOffering" else 0


def _validate_strict_price_channels(
    offering, expected_channel, offering_type, failures, require_prices=False
):
    offering_code = offering.get("code", offering.get("id", "<unknown>"))
    prices = offering.get("productOfferingPrice", [])
    if prices is None:
        prices = []
    if not isinstance(prices, list):
        failures.append(
            _strict_channel_failure(
                expected_channel,
                repr(prices),
                offering_code,
                offering_type,
                "productOfferingPrice.channel.name",
                "productOfferingPrice must be a list",
            )
        )
        return
    if require_prices and not prices:
        failures.append(
            _strict_channel_failure(
                expected_channel,
                "<missing>",
                offering_code,
                offering_type,
                "productOfferingPrice.channel.name",
                "SimpleProductOffering has no corresponding ProductOfferingPrice.",
            )
        )
        return

    for index, price in enumerate(prices):
        if not isinstance(price, dict):
            failures.append(
                _strict_channel_failure(
                    expected_channel,
                    "<invalid price>",
                    offering_code,
                    offering_type,
                    "productOfferingPrice.channel.name",
                    f"price entry {index} is not an object",
                )
            )
            continue
        price_code = price.get("code", price.get("id", f"index {index}"))
        _validate_exact_channel_names(
            price.get("channel"),
            expected_channel,
            offering_code,
            offering_type,
            f"productOfferingPrice[{price_code}].channel.name",
            failures,
            price_code=price_code,
        )


def _validate_exact_channel_names(
    channels,
    expected_channel,
    offering_code,
    offering_type,
    level,
    failures,
    price_code=None,
):
    actual_names = []
    issues = []
    if channels is None or channels == []:
        issues.append("no channel names were returned")

    elif not isinstance(channels, list):
        issues.append(
            f"channel must be a list, got {type(channels).__name__}"
        )
    else:
        for index, channel in enumerate(channels):
            if not isinstance(channel, dict):
                issues.append(f"channel entry {index} is not an object")
            elif not isinstance(channel.get("name"), str) or not channel["name"].strip():
                issues.append(f"channel entry {index} has no valid name")
            else:
                actual_names.append(channel["name"].strip())


    if not issues and not actual_names:
        issues.append("no channel names were returned")
    unexpected_names = sorted(
        {name for name in actual_names if name != expected_channel}
    )
    if unexpected_names:
        issues.append(
            f"unexpected channel(s) returned: {unexpected_names!r}"
        )
    if actual_names and expected_channel not in actual_names:
        issues.append(f"requested channel {expected_channel!r} is absent")

    if issues:
        failures.append(
            _strict_channel_failure(
                expected_channel,
                repr(actual_names) if actual_names else "<missing>",
                offering_code,
                offering_type,
                level,
                "; ".join(issues),
                price_code=price_code,
            )
        )


def _strict_channel_failure(
    requested_channel,
    actual_channel,
    offering_code,
    offering_type,
    level,
    reason,
    price_code=None,
):
    price_details = f"; price code/ID={price_code!r}" if price_code is not None else ""
    return (
        f"Requested channel={requested_channel!r}; actual channel(s)={actual_channel}; "
        f"product offering code={offering_code!r}; @type={offering_type!r}; "
        f"validation level={level}{price_details}; reason={reason}"
    )


def validate_bundled_product_offering_channels(response, requested_channel):
    validate_response_status(response, 200)

    if not requested_channel or not str(requested_channel).strip():
        raise AssertionError("Requested channel must not be empty.")

    try:
        payload = json.loads(getattr(response, "text", ""))
    except (TypeError, json.JSONDecodeError) as error:
        raise AssertionError(f"Product offering response is not valid JSON: {error}") from error

    if isinstance(payload, list):
        parents = payload
    elif isinstance(payload, dict):
        items = payload.get("items")
        if isinstance(items, list):
            parents = items
        elif "bundledProductOffering" in payload:
            parents = [payload]
        elif "code" in payload or "@type" in payload:
            parents = [payload]
        else:
            raise AssertionError(
                "Product offering response must contain a bundledProductOffering list."
            )
    else:
        raise AssertionError(
            f"Product offering response JSON must be an object or list, got {type(payload).__name__}."
        )

    if not parents:
        raise AssertionError(
            "Product offering response must contain a bundledProductOffering list."
        )

    invalid_offerings = []
    validated_count = 0
    for parent_index, parent in enumerate(parents):
        parent_label = _offering_label(parent, f"response item {parent_index}")
        if not isinstance(parent, dict):
            invalid_offerings.append(
                f"{parent_label}: cannot read bundledProductOffering from a non-object response item."
            )
            continue

        if "bundledProductOffering" not in parent:
            invalid_offerings.append(
                f"{parent_label}: bundledProductOffering is missing; "
                f"requested channel '{requested_channel}'."
            )
            continue

        bundled_offerings = parent["bundledProductOffering"]
        if not isinstance(bundled_offerings, list):
            invalid_offerings.append(
                f"{parent_label}: bundledProductOffering must be a list, "
                f"got {type(bundled_offerings).__name__}; requested channel '{requested_channel}'."
            )
            continue

        for bundle_index, offering in enumerate(bundled_offerings):
            validated_count += 1
            label = _offering_label(offering, f"{parent_label} bundled item {bundle_index}")
            if not isinstance(offering, dict):
                invalid_offerings.append(
                    f"Requested channel '{requested_channel}', {label}, "
                    f"available channels: <invalid offering object>."
                )
                continue

            available_channels, channel_issue = _get_available_channels(offering)
            normalized_channels = {name.casefold() for name in available_channels}
            if channel_issue or str(requested_channel).strip().casefold() not in normalized_channels:
                display_channels = ", ".join(available_channels) or "<none>"
                if channel_issue:
                    display_channels = f"{display_channels} ({channel_issue})"
                invalid_offerings.append(
                    f"Requested channel '{requested_channel}', {label}, "
                    f"available channels: [{display_channels}]."
                )

            nested = offering.get("bundledProductOffering")
            if nested is not None:
                if not isinstance(nested, list):
                    invalid_offerings.append(
                        f"{label}: nested bundledProductOffering must be a list, "
                        f"got {type(nested).__name__}; requested channel '{requested_channel}'."
                    )
                else:
                    validated_count += _validate_nested_bundled_offerings(
                        nested,
                        requested_channel,
                        invalid_offerings,
                        parent_label=label,
                    )

    if invalid_offerings:
        details = "\n".join(f"- {failure}" for failure in invalid_offerings)
        raise AssertionError(
            f"Bundled product offering channel validation failed for "
            f"'{requested_channel}'. Invalid offering(s):\n{details}"
        )

    return {
        "success": True,
        "requested_channel": str(requested_channel),
        "validated_offerings": validated_count,
        "message": (
            f"Validated {validated_count} bundled product offering(s) "
            f"for channel '{requested_channel}'."
        ),
    }


def _validate_nested_bundled_offerings(offerings, requested_channel, invalid_offerings, parent_label):
    validated_count = 0
    for index, offering in enumerate(offerings):
        validated_count += 1
        label = _offering_label(offering, f"{parent_label} bundled item {index}")
        if not isinstance(offering, dict):
            invalid_offerings.append(
                f"Requested channel '{requested_channel}', {label}, "
                f"available channels: <invalid offering object>."
            )
            continue

        available_channels, channel_issue = _get_available_channels(offering)
        normalized_channels = {name.casefold() for name in available_channels}
        if channel_issue or str(requested_channel).strip().casefold() not in normalized_channels:
            display_channels = ", ".join(available_channels) or "<none>"
            if channel_issue:
                display_channels = f"{display_channels} ({channel_issue})"
            invalid_offerings.append(
                f"Requested channel '{requested_channel}', {label}, "
                f"available channels: [{display_channels}]."
            )

        nested = offering.get("bundledProductOffering")
        if nested is not None:
            if not isinstance(nested, list):
                invalid_offerings.append(
                    f"{label}: nested bundledProductOffering must be a list, "
                    f"got {type(nested).__name__}; requested channel '{requested_channel}'."
                )
            else:
                validated_count += _validate_nested_bundled_offerings(
                    nested,
                    requested_channel,
                    invalid_offerings,
                    parent_label=label,
                )
    return validated_count


def _offering_label(offering, fallback):
    if not isinstance(offering, dict):
        return fallback
    offering_id = offering.get("id")
    offering_name = offering.get("name")
    return f"offering ID={offering_id!r}, name={offering_name!r}"


def _get_available_channels(offering):
    if "channel" not in offering:
        return [], "channel is missing"
    channels = offering["channel"]
    if channels is None:
        return [], "channel is null"
    if not isinstance(channels, list):
        return [], f"channel must be a list, got {type(channels).__name__}"

    names = []
    invalid_entries = []
    for index, channel in enumerate(channels):
        if not isinstance(channel, dict):
            invalid_entries.append(f"channel entry {index} is not an object")
        elif not isinstance(channel.get("name"), str) or not channel["name"].strip():
            invalid_entries.append(f"channel entry {index} has no valid name")
        else:
            names.append(channel["name"].strip())

    issue = "; ".join(invalid_entries) if invalid_entries else None
    return names, issue


def _get_product_offerings(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        items = payload.get("items")
        if isinstance(items, list):
            return items
        if "code" in payload or "@type" in payload:
            return [payload]
    raise AssertionError(f"Unexpected response format for product offering: {payload}")


def _validate_related_party(related_parties, expected_party, offering_code):
    if related_parties is None:
        return
    if isinstance(related_parties, str):
        actual_names = [related_parties]
    elif isinstance(related_parties, list):
        actual_names = [
            party.get("name")
            for party in related_parties
            if isinstance(party, dict) and party.get("name")
        ]
    elif isinstance(related_parties, dict):
        actual_names = [related_parties.get("name")] if related_parties.get("name") else []
    else:
        raise AssertionError(
            f"Invalid relatedParty value for offering {offering_code!r}: {related_parties!r}"
        )

    if actual_names and str(expected_party).casefold() not in {
        str(name).casefold() for name in actual_names
    }:
        raise AssertionError(
            f"Unexpected relatedParty for offering {offering_code!r}: "
            f"{actual_names!r}. Expected: {expected_party!r}"
        )


def _validate_category(categories, expected_category, offering_code):
    if categories is None:
        return
    if isinstance(categories, list):
        actual_names = [
            category.get("name")
            for category in categories
            if isinstance(category, dict) and category.get("name")
        ]
    elif isinstance(categories, dict):
        actual_names = [categories.get("name")] if categories.get("name") else []
    else:
        actual_names = [str(categories)]

    if actual_names and str(expected_category).casefold() not in {
        str(name).casefold() for name in actual_names
    }:
        raise AssertionError(
            f"Unexpected category for offering {offering_code!r}: "
            f"{actual_names!r}. Expected: {expected_category!r}"
        )


def _validate_offering_channels(offerings, expected_channel):
    expected_channel = str(expected_channel).strip().casefold()

    for offering in offerings:
        if not isinstance(offering, dict):
            raise AssertionError(f"Bundled product offering must be an object, got: {type(offering).__name__}")

        offering_type = offering.get("@type")
        offering_code = offering.get("code", "<unknown>")
        if offering_type in {"SimpleProductOffering", "GroupProductOffering"}:
            _assert_channel_present(
                offering.get("channel"),
                expected_channel,
                f"{offering_type} {offering_code}",
                allow_empty=False,
            )

        _validate_price_channels(offering, expected_channel)

        if offering_type == "GroupProductOffering":
            bundled_offerings = offering.get("bundledProductOffering", [])
            if bundled_offerings is None:
                bundled_offerings = []
            if not isinstance(bundled_offerings, list):
                raise AssertionError(
                    f"GroupProductOffering {offering_code} has an invalid "
                    "bundledProductOffering value."
                )
            _validate_offering_channels(bundled_offerings, expected_channel)


def _validate_price_channels(offering, expected_channel):
    offering_code = offering.get("code", "<unknown>")
    prices = offering.get("productOfferingPrice", [])
    if prices is None:
        prices = []
    if not isinstance(prices, list):
        raise AssertionError(
            f"Offering {offering_code} has an invalid productOfferingPrice value."
        )

    for price in prices:
        if not isinstance(price, dict):
            raise AssertionError(
                f"Offering {offering_code} contains an invalid productOfferingPrice entry."
            )
        _assert_channel_present(
            price.get("channel"),
            expected_channel,
            f"price {price.get('code', price.get('name', '<unknown>'))} "
            f"under offering {offering_code}",
        )


def _assert_channel_present(channels, expected_channel, context, allow_empty=True):
    if channels is None or (isinstance(channels, list) and len(channels) == 0):
        if allow_empty:
            return
        raise AssertionError(f"{context} has no valid channel list.")

    if not isinstance(channels, list):
        raise AssertionError(f"{context} channel attribute must be a list, got {type(channels).__name__}.")

    channel_names = {
        str(channel.get("name")).strip().casefold()
        for channel in channels
        if isinstance(channel, dict) and channel.get("name") is not None
    }
    if expected_channel not in channel_names:
        raise AssertionError(
            f"{context} is missing expected channel '{expected_channel}'. "
            f"Returned channels: {sorted(channel_names)}"
        )


def validate_compatibility_check_response(response, correlation_group=None, skus=None):
    validate_response_status(response, 200)
    validate_response_not_empty(response)

    payload = _get_json_payload(response)
    if not isinstance(payload, dict):
        raise AssertionError(f"Expected compatibility response object but got: {type(payload).__name__}")

    cart_items = payload.get("cartItem")
    if not isinstance(cart_items, list) or not cart_items:
        raise AssertionError(f"Compatibility response must contain a non-empty cartItem list. Payload: {payload}")

    item = cart_items[0]
    if not isinstance(item, dict):
        raise AssertionError(f"Compatibility cartItem must be an object. Payload: {payload}")

    required_fields = ["correlationGroup", "skus", "compatibility"]
    missing = [field for field in required_fields if field not in item]
    if missing:
        raise AssertionError(f"Compatibility response missing fields: {missing}. Payload: {payload}")

    if correlation_group and item["correlationGroup"] != correlation_group:
        raise AssertionError(
            f"Unexpected correlationGroup: {item['correlationGroup']}. Expected: {correlation_group}"
        )

    if skus is not None and item["skus"] != list(skus):
        raise AssertionError(f"Unexpected skus: {item['skus']}. Expected: {list(skus)}")

    if not isinstance(item["compatibility"], bool):
        raise AssertionError(
            f"Compatibility value must be boolean but got: {item['compatibility']!r}"
        )


def get_compatibility_result(response):
    payload = _get_json_payload(response)
    if not isinstance(payload, dict):
        raise AssertionError(f"Expected compatibility response object but got: {type(payload).__name__}")

    cart_items = payload.get("cartItem")
    if not isinstance(cart_items, list) or not cart_items or not isinstance(cart_items[0], dict):
        raise AssertionError(f"Compatibility response has no valid cartItem result. Payload: {payload}")

    compatibility = cart_items[0].get("compatibility")
    if not isinstance(compatibility, bool):
        raise AssertionError(f"Compatibility value must be boolean but got: {compatibility!r}")

    return compatibility


def _get_json_payload(response):
    try:
        if hasattr(response, "json"):
            return response.json()
    except Exception:
        pass

    try:
        return json.loads(getattr(response, "text", "{}"))
    except Exception:
        return {}
