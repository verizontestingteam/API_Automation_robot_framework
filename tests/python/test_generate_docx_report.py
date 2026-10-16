import xml.etree.ElementTree as ET

from python.generate_docx_report import _data_label, _test_data


def make_test(message):
    return ET.fromstring(
        "<test>"
        "<kw><arg>related_party=TW</arg><arg>channel_name=WEB</arg></kw>"
        f"<kw><msg level='INFO'>{message}</msg></kw>"
        "</test>"
    )


def test_test_data_includes_logged_extra_query_parameters():
    test = make_test('Extra query parameters: {"includeFacets": "true", "q.deviceType": "PHONE"}')

    assert _test_data(test) == {
        "related_party": "TW",
        "channel_name": "WEB",
        "includeFacets": "true",
        "q.deviceType": "PHONE",
    }


def test_test_data_ignores_invalid_extra_parameters_message():
    test = make_test("Extra query parameters: {not json")

    assert _test_data(test) == {"related_party": "TW", "channel_name": "WEB"}


def test_data_label_uses_friendly_and_humanized_names():
    assert _data_label("channel_name") == "Channel"
    assert _data_label("max_price") == "Max price"


def test_data_label_keeps_api_parameter_names():
    assert _data_label("q.deviceType") == "q.deviceType"
    assert _data_label("includeFacets") == "includeFacets"
