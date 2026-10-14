import json

import pytest

from python.api_custom_validations import (
    validate_bundled_product_offering_channels,
    validate_requested_product_offering_channels,
)


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.status_code = status_code
        self.text = payload if isinstance(payload, str) else json.dumps(payload)


def make_offering(offering_id, name, channels):
    return {"id": offering_id, "name": name, "channel": channels}


def make_response(bundled_offerings):
    return FakeResponse({"bundledProductOffering": bundled_offerings})


@pytest.mark.parametrize("channel_name", ["WEB", "AURA-CARE", "AURA-INDIRECT"])
def test_accepts_requested_channel_dynamically(channel_name):
    response = make_response(
        [make_offering("id-1", "Phone", [{"name": channel_name}])]
    )

    result = validate_bundled_product_offering_channels(response, channel_name)

    assert result == {
        "success": True,
        "requested_channel": channel_name,
        "validated_offerings": 1,
        "message": f"Validated 1 bundled product offering(s) for channel '{channel_name}'.",
    }


def test_accepts_offering_with_multiple_channels():
    response = make_response(
        [
            make_offering(
                "id-1",
                "Phone",
                [{"name": "AURA-CARE"}, {"name": "WEB"}, {"name": "AURA-INDIRECT"}],
            )
        ]
    )

    result = validate_bundled_product_offering_channels(response, "WEB")

    assert result["validated_offerings"] == 1


def test_rejects_offering_with_only_a_different_channel_and_reports_details():
    response = make_response(
        [make_offering("id-1", "Phone", [{"name": "AURA-INDIRECT"}])]
    )

    with pytest.raises(AssertionError) as error:
        validate_bundled_product_offering_channels(response, "WEB")

    message = str(error.value)
    assert "Requested channel 'WEB'" in message
    assert "id-1" in message
    assert "Phone" in message
    assert "AURA-INDIRECT" in message


@pytest.mark.parametrize(
    "channel_value",
    [
        pytest.param(None, id="null-channel"),
        pytest.param("WEB", id="non-list-channel"),
        pytest.param([None], id="invalid-channel-entry"),
        pytest.param([{"name": None}], id="missing-channel-name"),
        pytest.param([], id="empty-channel-list"),
    ],
)
def test_reports_missing_null_or_invalid_channel(channel_value):
    response = make_response([make_offering("id-1", "Phone", channel_value)])

    with pytest.raises(AssertionError, match="id-1"):
        validate_bundled_product_offering_channels(response, "WEB")


def test_collects_all_invalid_bundled_offerings():
    response = make_response(
        [
            make_offering("id-1", "Phone one", [{"name": "AURA-CARE"}]),
            make_offering("id-2", "Phone two", [{"name": "AURA-INDIRECT"}]),
        ]
    )

    with pytest.raises(AssertionError) as error:
        validate_bundled_product_offering_channels(response, "WEB")

    message = str(error.value)
    assert "id-1" in message
    assert "Phone one" in message
    assert "AURA-CARE" in message
    assert "id-2" in message
    assert "Phone two" in message
    assert "AURA-INDIRECT" in message


def test_empty_bundled_offering_list_is_valid_with_zero_count():
    result = validate_bundled_product_offering_channels(make_response([]), "WEB")

    assert result["success"] is True
    assert result["validated_offerings"] == 0


@pytest.mark.parametrize("payload", [{}, {"bundledProductOffering": None}, {"bundledProductOffering": {}}])
def test_rejects_missing_or_non_list_bundled_offerings(payload):
    with pytest.raises(AssertionError, match="bundledProductOffering"):
        validate_bundled_product_offering_channels(FakeResponse(payload), "WEB")


@pytest.mark.parametrize("payload", [[], {"items": []}])
def test_rejects_response_without_any_bundled_offering_array(payload):
    with pytest.raises(AssertionError, match="bundledProductOffering"):
        validate_bundled_product_offering_channels(FakeResponse(payload), "WEB")


def test_rejects_invalid_json():
    with pytest.raises(AssertionError, match="not valid JSON"):
        validate_bundled_product_offering_channels(FakeResponse("{not-json"), "WEB")


def test_reuses_response_status_validation():
    with pytest.raises(AssertionError, match="Expected HTTP status 200"):
        validate_bundled_product_offering_channels(
            FakeResponse({"bundledProductOffering": []}, status_code=401),
            "WEB",
        )


def make_channel_response(
    group_channels=None, simple_channels=None, price_channels=None, group_type="GroupProductOffering"
):
    return FakeResponse(
        {
            "items": [
                {
                    "@type": group_type,
                    "code": "GROUP-1",
                    "channel": (
                        group_channels
                        if group_channels is not None
                        else [{"name": "WEB"}]
                    ),
                    "bundledProductOffering": [
                        {
                            "@type": "SimpleProductOffering",
                            "code": "SIMPLE-1",
                            "channel": (
                                simple_channels
                                if simple_channels is not None
                                else [{"name": "WEB"}]
                            ),
                            "productOfferingPrice": [
                                {
                                    "code": "PRICE-1",
                                    "channel": (
                                        price_channels
                                        if price_channels is not None
                                        else [{"name": "WEB"}]
                                    ),
                                }
                            ],
                        }
                    ],
                }
            ]
        }
    )


@pytest.mark.parametrize("channel_name", ["WEB", "AURA-CARE", "AURA-INDIRECT"])
def test_channel_validation_accepts_requested_channel_dynamically(channel_name):
    validate_requested_product_offering_channels(
        make_channel_response(
            group_channels=[{"name": channel_name}],
            simple_channels=[{"name": channel_name}],
            price_channels=[{"name": channel_name}],
        ),
        channel_name,
    )


@pytest.mark.parametrize(
    ("validation_level", "kwargs", "actual_channel"),
    [
        (
            "GroupProductOffering.channel.name",
            {"group_channels": [{"name": "WEB"}, {"name": "AURA-CARE"}]},
            "AURA-CARE",
        ),
        (
            "SimpleProductOffering.channel.name",
            {"simple_channels": [{"name": "WEB"}, {"name": "AURA-INDIRECT"}]},
            "AURA-INDIRECT",
        ),
        (
            "productOfferingPrice[PRICE-1].channel.name",
            {"price_channels": [{"name": "WEB"}, {"name": "AURA-CARE"}]},
            "AURA-CARE",
        ),
        (
            "GroupProductOffering.channel.name",
            {"group_channels": [{"name": "web"}]},
            "web",
        ),
    ],
)
def test_channel_validation_rejects_unrequested_channels_at_each_level(
    validation_level, kwargs, actual_channel
):
    with pytest.raises(AssertionError) as error:
        validate_requested_product_offering_channels(
            make_channel_response(**kwargs),
            "WEB",
        )

    message = str(error.value)
    assert "Requested channel='WEB'" in message
    assert "product offering code=" in message
    assert "@type=" in message
    assert actual_channel in message
    assert validation_level in message
    assert "unexpected channel(s) returned" in message


def test_channel_validation_rejects_simple_offering_without_corresponding_price():
    response = make_channel_response()
    response_payload = json.loads(response.text)
    response_payload["items"][0]["bundledProductOffering"][0]["productOfferingPrice"] = []

    with pytest.raises(AssertionError, match="no corresponding ProductOfferingPrice"):
        validate_requested_product_offering_channels(
            FakeResponse(response_payload),
            "WEB",
        )


def test_channel_validation_rejects_group_without_corresponding_simple_offering():
    response = make_channel_response()
    response_payload = json.loads(response.text)
    response_payload["items"][0]["bundledProductOffering"] = []

    with pytest.raises(AssertionError, match="no corresponding bundled offering"):
        validate_requested_product_offering_channels(
            FakeResponse(response_payload),
            "WEB",
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"group_channels": []},
        {"simple_channels": []},
        {"price_channels": []},
    ],
)
def test_channel_validation_rejects_missing_channel_at_any_level(kwargs):
    with pytest.raises(AssertionError, match="no channel names were returned"):
        validate_requested_product_offering_channels(
            make_channel_response(**kwargs),
            "WEB",
        )


def test_channel_validation_checks_every_group_offering_and_nested_price():
    response = FakeResponse(
        {
            "items": [
                {
                    "@type": "GroupProductOffering",
                    "code": "GROUP-1",
                    "channel": [{"name": "WEB"}],
                    "bundledProductOffering": [
                        {
                            "@type": "SimpleProductOffering",
                            "code": "SIMPLE-1",
                            "channel": [{"name": "WEB"}],
                            "productOfferingPrice": [
                                {"code": "PRICE-1", "channel": [{"name": "WEB"}]},
                                {"code": "PRICE-2", "channel": [{"name": "WEB"}]},
                            ],
                        },
                        {
                            "@type": "SimpleProductOffering",
                            "code": "SIMPLE-2",
                            "channel": [{"name": "WEB"}],
                            "productOfferingPrice": [
                                {"code": "PRICE-3", "channel": [{"name": "WEB"}]}
                            ],
                        },
                    ],
                },
                {
                    "@type": "GroupProductOffering",
                    "code": "GROUP-2",
                    "channel": [{"name": "WEB"}],
                    "bundledProductOffering": [
                        {
                            "@type": "SimpleProductOffering",
                            "code": "SIMPLE-3",
                            "channel": [{"name": "WEB"}],
                            "productOfferingPrice": [
                                {"code": "PRICE-4", "channel": [{"name": "WEB"}]}
                            ],
                        }
                    ],
                },
            ]
        }
    )

    validate_requested_product_offering_channels(response, "WEB")


def test_channel_validation_finds_mismatch_in_later_group_price():
    response = FakeResponse(
        {
            "items": [
                {
                    "@type": "GroupProductOffering",
                    "code": "GROUP-1",
                    "channel": [{"name": "WEB"}],
                    "bundledProductOffering": [
                        {
                            "@type": "SimpleProductOffering",
                            "code": "SIMPLE-1",
                            "channel": [{"name": "WEB"}],
                            "productOfferingPrice": [
                                {"code": "PRICE-1", "channel": [{"name": "WEB"}]}
                            ],
                        }
                    ],
                },
                {
                    "@type": "GroupProductOffering",
                    "code": "GROUP-2",
                    "channel": [{"name": "WEB"}],
                    "bundledProductOffering": [
                        {
                            "@type": "SimpleProductOffering",
                            "code": "SIMPLE-2",
                            "channel": [{"name": "WEB"}],
                            "productOfferingPrice": [
                                {"code": "PRICE-2", "channel": [{"name": "WEB"}]},
                                {"code": "PRICE-3", "channel": [{"name": "AURA-CARE"}]},
                            ],
                        }
                    ],
                },
            ]
        }
    )

    with pytest.raises(AssertionError) as error:
        validate_requested_product_offering_channels(response, "WEB")

    message = str(error.value)
    assert "GROUP-2" not in message or "SIMPLE-2" in message
    assert "PRICE-3" in message
    assert "AURA-CARE" in message
    assert "productOfferingPrice[PRICE-3].channel.name" in message


@pytest.mark.parametrize(
    ("response", "validation_level", "actual_channel"),
    [
        (
            make_channel_response(
                group_channels=[{"name": "AURA-CARE"}]
            ),
            "GroupProductOffering.channel.name",
            "AURA-CARE",
        ),
        (
            make_channel_response(
                simple_channels=[{"name": "AURA-INDIRECT"}]
            ),
            "SimpleProductOffering.channel.name",
            "AURA-INDIRECT",
        ),
        (
            make_channel_response(
                price_channels=[{"name": "AURA-CARE"}]
            ),
            "productOfferingPrice[PRICE-1].channel.name",
            "AURA-CARE",
        ),
    ],
)
def test_channel_validation_rejects_list_without_requested_channel_and_reports_context(
    response, validation_level, actual_channel
):
    with pytest.raises(AssertionError) as error:
        validate_requested_product_offering_channels(response, "WEB")

    message = str(error.value)
    assert "Requested channel='WEB'" in message
    assert "actual channel(s)=" in message
    assert actual_channel in message
    assert "product offering code='GROUP-1'" in message or "product offering code='SIMPLE-1'" in message
    assert "@type=" in message
    assert f"validation level={validation_level}" in message
    assert "requested channel 'WEB' is absent" in message


def test_channel_validation_rejects_group_with_wrong_type():
    response = make_channel_response(group_type="SimpleProductOffering")

    with pytest.raises(AssertionError) as error:
        validate_requested_product_offering_channels(response, "WEB")

    message = str(error.value)
    assert "product offering code='GROUP-1'" in message
    assert "validation level=@type" in message
    assert "expected 'GroupProductOffering'" in message


def test_validates_bundle_items_in_items_response():
    response = FakeResponse(
        {
            "items": [
                {
                    "code": "BUNDLE-1",
                    "bundledProductOffering": [
                        make_offering("id-1", "Phone", [{"name": "WEB"}])
                    ],
                }
            ]
        }
    )

    result = validate_bundled_product_offering_channels(response, "WEB")

    assert result["validated_offerings"] == 1
