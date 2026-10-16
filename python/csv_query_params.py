import csv
import json
import re

from robot.api import logger


def _column_name(header):
    """'${q.deviceType}' -> 'q.deviceType'; None for other headers such as [Tags]."""
    match = re.fullmatch(r"\$\{(.+)\}", header.strip())
    return match.group(1).strip() if match else None


def get_extra_query_params(csv_file, test_name, **known_values):
    """Return the non-empty ${...} CSV columns of this test's row that are not the
    keyword's own arguments (known_values), as API query parameters
    (header ${q.deviceType} -> q.deviceType)."""
    with open(csv_file, encoding="utf-8-sig", newline="") as file:
        rows = [row for row in csv.reader(file) if any(cell.strip() for cell in row)]
    if not rows:
        raise AssertionError(f"CSV file {csv_file} is empty.")

    headers = [_column_name(cell) for cell in rows[0][1:]]
    named, unnamed = [], []
    for row in rows[1:]:
        values = {header: cell.strip() for header, cell in zip(headers, row[1:]) if header}
        name = row[0].strip()
        if name == str(test_name).strip():
            named.append(values)
        elif not name and all(values.get(c, "") == str(v).strip() for c, v in known_values.items()):
            # Unnamed row: DataDriver names the test from the template, so match on argument values
            unnamed.append(values)
    matches = named or unnamed
    if not matches:
        raise AssertionError(f"No row named {test_name!r} found in {csv_file}.")
    if len(matches) > 1:
        raise AssertionError(
            f"{len(matches)} rows are named {test_name!r} in {csv_file}; test names must be unique."
        )

    params = {name: value for name, value in matches[0].items() if name not in known_values and value}

    logger.info(f"Extra query parameters: {json.dumps(params)}")
    return params
