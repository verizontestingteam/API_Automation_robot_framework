import json

import pytest

from python.api_custom_validations import (
    validate_product_offering_response,
    validate_requested_product_offering_channels,
)


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.status_code = status_code
        self.text = payload if isinstance(payload, str) else json.dumps(payload)


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


def test_channel_validation_allows_additional_channels_at_each_level():
    validate_requested_product_offering_channels(
        make_channel_response(
            group_channels=[{"name": "WEB"}, {"name": "AURA-CARE"}],
            simple_channels=[{"name": "WEB"}, {"name": "AURA-INDIRECT"}],
            price_channels=[{"name": "WEB"}, {"name": "AURA-CARE"}],
        ),
        "WEB",
    )


def test_channel_validation_allows_prices_without_channel_association():
    response = make_channel_response()
    payload = json.loads(response.text)
    price = payload["items"][0]["bundledProductOffering"][0]["productOfferingPrice"][0]
    del price["channel"]

    validate_requested_product_offering_channels(FakeResponse(payload), "WEB")


def test_channel_validation_allows_prices_with_empty_channel_association():
    response = make_channel_response(price_channels=[])

    validate_requested_product_offering_channels(response, "WEB")


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


def test_product_offering_response_with_message_and_no_items_does_not_crash():
    response = FakeResponse({"message": "No product offerings found"})

    validate_product_offering_response(response)


def test_channel_validation_matches_channel_names_case_insensitively():
    validate_requested_product_offering_channels(
        make_channel_response(
            group_channels=[{"name": "Aura-Care"}],
            simple_channels=[{"name": "aura-care"}],
            price_channels=[{"name": "AURA-CARE"}],
        ),
        "AURA-CARE",
    )


def test_channel_validation_rejects_empty_offering_list():
    with pytest.raises(AssertionError, match="No product offerings returned"):
        validate_requested_product_offering_channels(FakeResponse({"items": []}), "WEB")


def test_channel_validation_returns_summary():
    result = validate_requested_product_offering_channels(make_channel_response(), "WEB")

    assert result == "Validated 1 group offering(s) and 1 simple offering(s) for channel 'WEB'."
