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


def validate_product_offering_response(
    response, related_party=None, code=None, depth=None, category_name=None, channel_name=None
):
    validate_response_status(response, 200)
    validate_response_not_empty(response)

    payload = _get_json_payload(response)
    if isinstance(payload, dict):
        items = payload.get("items")
        if items is None and payload.get("message"):
            return
        if items is not None and isinstance(items, list):
            if len(items) == 0:
                return
            first_item = items[0]
            if isinstance(first_item, dict):
                if related_party and first_item.get("relatedParty") not in [related_party, None]:
                    raise AssertionError(f"Unexpected relatedParty value: {first_item.get('relatedParty')}")
                if code and first_item.get("code") and first_item.get("code") != code:
                    raise AssertionError(f"Unexpected product code: {first_item.get('code')}")
                if category_name and first_item.get("category"):
                    category = first_item.get("category")
                    if isinstance(category, list) and category and isinstance(category[0], dict):
                        category_value = category[0].get("name")
                    elif isinstance(category, dict):
                        category_value = category.get("name")
                    else:
                        category_value = category
                    if category_value and str(category_value).lower() != str(category_name).lower():
                        raise AssertionError(
                            f"Unexpected category name: {category_value}. Expected: {category_name}"
                        )
            return

    if isinstance(payload, list):
        if not payload:
            return
        first_item = payload[0]
        if isinstance(first_item, dict):
            if code and first_item.get("code") and first_item.get("code") != code:
                raise AssertionError(f"Unexpected product code: {first_item.get('code')}")
            if category_name and first_item.get("category"):
                category = first_item.get("category")
                if isinstance(category, list) and category and isinstance(category[0], dict):
                    category_value = category[0].get("name")
                elif isinstance(category, dict):
                    category_value = category.get("name")
                else:
                    category_value = category
                if category_value and str(category_value).lower() != str(category_name).lower():
                    raise AssertionError(
                        f"Unexpected category name: {category_value}. Expected: {category_name}"
                    )
        return

    raise AssertionError(f"Unexpected response format for product offering: {payload}")


def _assert_channel_present(channels, expected_channel, context):
    if not isinstance(channels, list):
        raise AssertionError(f"{context} has no valid channel list.")

    channel_names = {
        str(channel.get("name")).strip().lower()
        for channel in channels
        if isinstance(channel, dict) and channel.get("name")
    }
    if expected_channel not in channel_names:
        raise AssertionError(
            f"{context} is missing expected channel '{expected_channel}'. "
            f"Returned channels: {sorted(channel_names)}"
        )


def validate_response_headers(response, header_name, expected_value=None):
    headers = getattr(response, "headers", {}) or {}
    value = next(
        (value for name, value in headers.items() if name.casefold() == str(header_name).casefold()),
        None,
    )
    if value is None:
        raise AssertionError(f"Expected response header '{header_name}' was not found.")
    if expected_value is not None and str(expected_value).casefold() not in str(value).casefold():
        raise AssertionError(
            f"Expected header '{header_name}' to contain '{expected_value}', but got '{value}'."
        )


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


def validate_root_offering_channels(response, requested_channel):
    validate_response_status(response, 200)
    if not requested_channel or not str(requested_channel).strip():
        raise AssertionError("Requested channel must not be empty.")

    offerings = _get_product_offerings(_get_json_payload(response))
    if not offerings:
        raise AssertionError("No product offerings found to validate root channels.")
    expected = str(requested_channel).strip().casefold()
    failures = []
    for index, offering in enumerate(offerings):
        if not isinstance(offering, dict):
            failures.append(f"Root item {index} is not an object.")
            continue
        channels = offering.get("channel")
        names = {
            channel.get("name").strip().casefold()
            for channel in channels or []
            if isinstance(channel, dict) and isinstance(channel.get("name"), str)
        } if isinstance(channels, list) else set()
        if expected not in names:
            code = offering.get("code", offering.get("id", index))
            failures.append(f"Root offering code={code!r} is missing channel '{requested_channel}'.")
    if failures:
        raise AssertionError("\n".join(failures))


def validate_product_offering_schema(response):
    for index, offering in enumerate(_get_product_offerings(_get_json_payload(response))):
        if not isinstance(offering, dict):
            raise AssertionError(f"Product offering item {index} must be an object.")
        missing = [
            field for field in ("id", "code", "name")
            if field not in offering or offering[field] is None
        ]
        if missing:
            code = offering.get("code", offering.get("id", f"item_{index}"))
            raise AssertionError(f"Product offering {code!r} is missing mandatory schema fields: {missing}")
        status = offering.get("lifecycleStatus")
        if status is not None and str(status).strip().casefold() not in {
            "active", "launched", "in study", "in-study", "in design", "indesign"
        }:
            raise AssertionError(f"Product offering {offering['code']!r} has invalid lifecycleStatus: {status!r}")


def validate_product_offering_prices(response, expected_channel=None):
    for index, offering in enumerate(_get_product_offerings(_get_json_payload(response))):
        if not isinstance(offering, dict):
            continue
        prices = offering.get("productOfferingPrice", [])
        if prices is None:
            continue
        code = offering.get("code", f"item_{index}")
        if not isinstance(prices, list):
            raise AssertionError(f"Product offering {code!r} productOfferingPrice must be a list.")
        for price in prices:
            if not isinstance(price, dict):
                raise AssertionError(f"Price entry under offering {code!r} is not an object.")
            price_value = price.get("price", {}).get("value") if isinstance(price.get("price"), dict) else None
            if price_value is not None:
                try:
                    if float(price_value) < 0:
                        raise AssertionError(f"Price value under offering {code!r} cannot be negative: {price_value}")
                except (TypeError, ValueError) as error:
                    raise AssertionError(f"Price value under offering {code!r} is non-numeric: {price_value!r}") from error
            if expected_channel and price.get("channel"):
                _assert_channel_present(
                    price.get("channel"),
                    str(expected_channel).strip().casefold(),
                    f"Price under offering {code!r}",
                )


def validate_product_offering_validity(response):
    from datetime import datetime

    for index, offering in enumerate(_get_product_offerings(_get_json_payload(response))):
        valid_for = offering.get("validFor") if isinstance(offering, dict) else None
        if not isinstance(valid_for, dict):
            continue
        for field in ("startDateTime", "endDateTime"):
            value = valid_for.get(field)
            if value:
                try:
                    datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                except ValueError as error:
                    code = offering.get("code", f"item_{index}")
                    raise AssertionError(
                        f"Product offering {code!r} has invalid validFor.{field}: {value!r}"
                    ) from error


def _strict_channel_failure(requested, actual, code, offering_type, level, reason):
    return (
        f"Requested channel={requested!r}; actual channel(s)={actual}; "
        f"product offering code={code!r}; @type={offering_type!r}; "
        f"validation level={level}; reason={reason}"
    )


def _validate_strict_offering(offering, requested, failures, expected_type=None):
    offering_type = offering.get("@type")
    code = offering.get("code", offering.get("id", "<unknown>"))
    if expected_type and offering_type != expected_type:
        failures.append(
            _strict_channel_failure(
                requested, "<not applicable>", code, offering_type, "@type",
                f"expected {expected_type!r}, got {offering_type!r}",
            )
        )
        return 0
    if offering_type not in {"GroupProductOffering", "SimpleProductOffering"}:
        failures.append(
            _strict_channel_failure(
                requested, "<not applicable>", code, offering_type, "@type",
                f"unexpected offering type {offering_type!r}",
            )
        )
        return 0

    def check_channels(channels, level, price_code=None):
        actual = []
        issues = []
        if not channels:
            issues.append("no channel names were returned")
        elif not isinstance(channels, list):
            issues.append(f"channel must be a list, got {type(channels).__name__}")
        else:
            for index, channel in enumerate(channels):
                if not isinstance(channel, dict):
                    issues.append(f"channel entry {index} is not an object")
                elif not isinstance(channel.get("name"), str) or not channel["name"].strip():
                    issues.append(f"channel entry {index} has no valid name")
                else:
                    actual.append(channel["name"].strip())
        if actual and requested.casefold() not in {name.casefold() for name in actual}:
            issues.append(f"requested channel {requested!r} is absent")
        if issues:
            level_text = f"{level}[{price_code}].channel.name" if price_code else level
            failures.append(
                _strict_channel_failure(
                    requested, repr(actual) if actual else "<missing>", code,
                    offering_type, level_text, "; ".join(issues),
                )
            )

    check_channels(offering.get("channel"), f"{offering_type}.channel.name")
    prices = offering.get("productOfferingPrice", [])
    if prices is None:
        prices = []
    if not isinstance(prices, list):
        failures.append(
            _strict_channel_failure(
                requested, repr(prices), code, offering_type,
                "productOfferingPrice.channel.name", "productOfferingPrice must be a list",
            )
        )
    else:
        if offering_type == "SimpleProductOffering" and not prices:
            failures.append(
                _strict_channel_failure(
                    requested, "<missing>", code, offering_type,
                    "productOfferingPrice.channel.name",
                    "SimpleProductOffering has no corresponding ProductOfferingPrice.",
                )
            )
        for index, price in enumerate(prices):
            if not isinstance(price, dict):
                failures.append(
                    _strict_channel_failure(
                        requested, "<invalid price>", code, offering_type,
                        "productOfferingPrice.channel.name", f"price entry {index} is not an object",
                    )
                )
                continue
            price_code = price.get("code", price.get("id", f"index {index}"))
            if price.get("channel"):
                check_channels(
                    price.get("channel"), "productOfferingPrice", price_code
                )

    count = 1 if offering_type == "SimpleProductOffering" else 0
    if offering_type == "GroupProductOffering":
        bundled = offering.get("bundledProductOffering")
        if not isinstance(bundled, list) or not bundled:
            failures.append(
                _strict_channel_failure(
                    requested, "<missing>", code, offering_type,
                    "bundledProductOffering",
                    "GroupProductOffering has no corresponding bundled offering.",
                )
            )
            return count
        for child in bundled:
            if isinstance(child, dict):
                count += _validate_strict_offering(child, requested, failures)
            else:
                failures.append(
                    _strict_channel_failure(
                        requested, "<invalid offering>", code, "<unknown>",
                        "bundledProductOffering.@type", "bundled item is not an object",
                    )
                )
        if count == 0:
            failures.append(
                _strict_channel_failure(
                    requested, "<missing>", code, offering_type,
                    "bundledProductOffering.SimpleProductOffering",
                    "GroupProductOffering has no corresponding SimpleProductOffering.",
                )
            )
    return count


def validate_requested_product_offering_channels(response, requested_channel):
    validate_response_status(response, 200)
    if not requested_channel or not str(requested_channel).strip():
        raise AssertionError("Requested channel must not be empty.")
    requested = str(requested_channel).strip()
    offerings = _get_product_offerings(_get_json_payload(response))
    failures = []
    for index, offering in enumerate(offerings):
        if not isinstance(offering, dict):
            failures.append(
                _strict_channel_failure(
                    requested, "<invalid offering>", f"item_{index}",
                    "<unknown>", "GroupProductOffering.@type",
                    f"root offering {index} is not an object",
                )
            )
        else:
            _validate_strict_offering(
                offering, requested, failures, expected_type="GroupProductOffering"
            )
    if failures:
        raise AssertionError(
            f"Strict channel filtering validation failed for requested channel "
            f"'{requested}':\n" + "\n".join(f"- {failure}" for failure in failures)
        )


def _offering_label(offering, fallback):
    if not isinstance(offering, dict):
        return fallback
    return f"offering ID={offering.get('id')!r}, name={offering.get('name')!r}"


def _available_channels(offering):
    channels = offering.get("channel")
    if channels is None:
        return [], "channel is missing or null"
    if not isinstance(channels, list):
        return [], f"channel must be a list, got {type(channels).__name__}"
    names = []
    invalid = []
    for index, channel in enumerate(channels):
        if not isinstance(channel, dict):
            invalid.append(f"channel entry {index} is not an object")
        elif not isinstance(channel.get("name"), str) or not channel["name"].strip():
            invalid.append(f"channel entry {index} has no valid name")
        else:
            names.append(channel["name"].strip())
    return names, "; ".join(invalid) or (None if names else "no channel names were returned")


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
    elif isinstance(payload, dict) and isinstance(payload.get("items"), list):
        parents = payload["items"]
    elif isinstance(payload, dict) and "bundledProductOffering" in payload:
        parents = [payload]
    else:
        raise AssertionError("Product offering response must contain a bundledProductOffering list.")
    if not parents:
        raise AssertionError("Product offering response must contain a bundledProductOffering list.")

    failures = []
    validated = 0

    def visit(items, parent_label):
        nonlocal validated
        for index, offering in enumerate(items):
            validated += 1
            label = _offering_label(offering, f"{parent_label} bundled item {index}")
            if not isinstance(offering, dict):
                failures.append(
                    f"Requested channel '{requested_channel}', {label}, available channels: <invalid offering object>."
                )
                continue
            channels, issue = _available_channels(offering)
            if issue or str(requested_channel).strip().casefold() not in {
                name.casefold() for name in channels
            }:
                available = ", ".join(channels) or "<none>"
                if issue:
                    available += f" ({issue})"
                failures.append(
                    f"Requested channel '{requested_channel}', {label}, available channels: [{available}]."
                )
            nested = offering.get("bundledProductOffering")
            if nested is not None:
                if not isinstance(nested, list):
                    failures.append(f"{label}: nested bundledProductOffering must be a list.")
                else:
                    visit(nested, label)

    for index, parent in enumerate(parents):
        if not isinstance(parent, dict):
            failures.append(f"response item {index} is not an object.")
            continue
        if "bundledProductOffering" not in parent or not isinstance(parent["bundledProductOffering"], list):
            failures.append(
                f"{_offering_label(parent, f'response item {index}')}: "
                "bundledProductOffering is missing or is not a list."
            )
            continue
        visit(parent["bundledProductOffering"], _offering_label(parent, f"response item {index}"))
    if failures:
        raise AssertionError(
            f"Bundled product offering channel validation failed for "
            f"'{requested_channel}'. Invalid offering(s):\n"
            + "\n".join(f"- {failure}" for failure in failures)
        )
    return {
        "success": True,
        "requested_channel": str(requested_channel),
        "validated_offerings": validated,
        "message": f"Validated {validated} bundled product offering(s) for channel '{requested_channel}'.",
    }


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
