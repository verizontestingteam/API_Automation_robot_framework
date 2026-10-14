import csv


class CSVReader:

    def read_csv(self, file_path):
        return read_csv(file_path)


def read_csv(file_path):
    with open(file_path, mode="r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.reader(file))

    if not rows:
        return []

    first = rows[0]
    if first and first[0].startswith("***"):
        keys = []
        for cell in first[1:]:
            keys.append(cell.strip().replace("${", "").replace("}", "").replace(" ", ""))

        normalized = []
        for values in rows[1:]:
            if not values or not any(value.strip() for value in values):
                continue
            row = {}
            for index, key in enumerate(keys):
                value = values[index + 1] if index + 1 < len(values) else ""
                row[key] = value.strip()
            normalized.append(row)
        return normalized

    return list(csv.DictReader(rows))