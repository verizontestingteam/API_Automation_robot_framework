import pytest

from python.csv_query_params import get_extra_query_params

KNOWN = {"related_party": "TW", "depth": "4", "code": "X1", "category_name": "Phones", "channel_name": "WEB"}
HEADER = "*** Test Cases ***,${related_party},${depth},${code},${category_name},${channel_name}"


def write_csv(tmp_path, *lines):
    path = tmp_path / "data.csv"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_returns_extra_columns_with_api_parameter_names(tmp_path):
    path = write_csv(
        tmp_path,
        HEADER + ",${limit},${q.deviceType}",
        "Row A,TW,4,X1,Phones,WEB,5,SMARTPHONE",
    )

    assert get_extra_query_params(path, "Row A", **KNOWN) == {"limit": "5", "q.deviceType": "SMARTPHONE"}


def test_skips_empty_extra_values(tmp_path):
    path = write_csv(
        tmp_path,
        HEADER + ",${limit},${q.deviceType}",
        "Row A,TW,4,X1,Phones,WEB,,SMARTPHONE",
        "Row B,TW,4,X2,Phones,WEB",
    )

    assert get_extra_query_params(path, "Row A", **KNOWN) == {"q.deviceType": "SMARTPHONE"}
    assert get_extra_query_params(path, "Row B", **KNOWN) == {}


def test_returns_nothing_without_extra_columns(tmp_path):
    path = write_csv(tmp_path, HEADER, "Row A,TW,4,X1,Phones,WEB")

    assert get_extra_query_params(path, "Row A", **KNOWN) == {}


def test_matches_unnamed_row_by_argument_values(tmp_path):
    path = write_csv(
        tmp_path,
        HEADER + ",${limit}",
        ",TW,4,X1,Phones,WEB,5",
        ",TW,4,X2,Phones,WEB,9",
    )

    assert get_extra_query_params(path, "Product Offering X1 WEB", **KNOWN) == {"limit": "5"}


def test_named_row_wins_over_unnamed_row_with_same_values(tmp_path):
    path = write_csv(tmp_path, HEADER + ",${limit}", "Smoke WEB,TW,4,X1,Phones,WEB,5", ",TW,4,X1,Phones,WEB,9")

    assert get_extra_query_params(path, "Smoke WEB", **KNOWN) == {"limit": "5"}
    assert get_extra_query_params(path, "Product Offering X1 WEB", **KNOWN) == {"limit": "9"}


def test_ignores_non_variable_columns(tmp_path):
    path = write_csv(tmp_path, HEADER + ",[Tags],${limit}", "Row A,TW,4,X1,Phones,WEB,smoke,5")

    assert get_extra_query_params(path, "Row A", **KNOWN) == {"limit": "5"}


def test_fails_when_test_row_is_missing(tmp_path):
    path = write_csv(tmp_path, HEADER, "Row A,TW,4,X1,Phones,WEB")

    with pytest.raises(AssertionError, match="No row named 'Row Z'"):
        get_extra_query_params(path, "Row Z", **KNOWN)


def test_fails_on_duplicate_test_names(tmp_path):
    path = write_csv(tmp_path, HEADER, "Row A,TW,4,X1,Phones,WEB", "Row A,TW,4,X2,Phones,WEB")

    with pytest.raises(AssertionError, match="test names must be unique"):
        get_extra_query_params(path, "Row A", **KNOWN)
