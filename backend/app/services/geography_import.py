import csv
import io
from dataclasses import dataclass

REQUIRED = {"level", "code", "name", "parent_code"}
LEVEL_PARENT = {"state": None, "lga": "state", "ward": "lga", "polling_unit": "ward"}


@dataclass
class GeographyImportResult:
    rows: list[dict[str, str]]
    errors: list[dict]


def validate_geography_csv(content: bytes) -> GeographyImportResult:
    try:
        reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    except UnicodeDecodeError:
        return GeographyImportResult([], [{"row": 0, "message": "File must be UTF-8"}])
    missing = REQUIRED - set(reader.fieldnames or [])
    if missing:
        return GeographyImportResult(
            [], [{"row": 1, "message": f"Missing columns: {', '.join(sorted(missing))}"}]
        )
    rows, errors, keys = [], [], set()
    for line, row in enumerate(reader, 2):
        level, code = row["level"].strip(), row["code"].strip()
        if level not in LEVEL_PARENT:
            errors.append({"row": line, "message": "Invalid level"})
        elif not code or not row["name"].strip():
            errors.append({"row": line, "message": "code and name are required"})
        elif (level, code) in keys:
            errors.append({"row": line, "message": "Duplicate level/code"})
        else:
            keys.add((level, code))
            rows.append({key: (value or "").strip() for key, value in row.items()})
    if not errors:
        by_level = {
            level: {r["code"] for r in rows if r["level"] == level} for level in LEVEL_PARENT
        }
        for line, row in enumerate(rows, 2):
            parent_level = LEVEL_PARENT[row["level"]]
            if parent_level and row["parent_code"] not in by_level[parent_level]:
                errors.append(
                    {"row": line, "message": f"Unknown parent_code: {row['parent_code']}"}
                )
    return GeographyImportResult(rows, errors)
