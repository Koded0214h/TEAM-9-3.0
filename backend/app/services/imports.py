import csv
import hashlib
import io
import json
from dataclasses import dataclass
from typing import Any

POLLING_UNIT_FIELDS = {
    "code",
    "name",
    "address",
    "ward_code",
    "latitude",
    "longitude",
    "registered_voters",
}


@dataclass
class ValidationResult:
    rows: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    checksum: str


def validate_polling_unit_csv(content: bytes) -> ValidationResult:
    checksum = hashlib.sha256(content).hexdigest()
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return ValidationResult([], [{"row": 0, "message": "File must be UTF-8 encoded"}], checksum)
    reader = csv.DictReader(io.StringIO(decoded))
    missing = POLLING_UNIT_FIELDS - set(reader.fieldnames or [])
    if missing:
        return ValidationResult(
            [], [{"row": 1, "message": f"Missing columns: {', '.join(sorted(missing))}"}], checksum
        )
    rows, errors, seen = [], [], set()
    for row_number, row in enumerate(reader, start=2):
        row_errors = []
        code = (row.get("code") or "").strip()
        if not code or code in seen:
            row_errors.append("code is blank or duplicated")
        seen.add(code)
        try:
            latitude, longitude = float(row["latitude"]), float(row["longitude"])
            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                row_errors.append("coordinates are outside valid ranges")
        except (TypeError, ValueError):
            row_errors.append("latitude and longitude must be numbers")
        try:
            if int(row["registered_voters"]) < 0:
                row_errors.append("registered_voters cannot be negative")
        except (TypeError, ValueError):
            row_errors.append("registered_voters must be an integer")
        if row_errors:
            errors.append({"row": row_number, "code": code, "message": "; ".join(row_errors)})
        else:
            rows.append(row)
    return ValidationResult(rows, errors, checksum)


def validate_geojson(content: bytes, *, administrative: bool = False) -> ValidationResult:
    checksum = hashlib.sha256(content).hexdigest()
    try:
        data = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return ValidationResult([], [{"row": 0, "message": "Invalid UTF-8 GeoJSON"}], checksum)
    if data.get("type") != "FeatureCollection" or not isinstance(data.get("features"), list):
        return ValidationResult(
            [], [{"row": 0, "message": "Expected a GeoJSON FeatureCollection"}], checksum
        )
    errors = []
    for index, feature in enumerate(data["features"], start=1):
        if feature.get("type") != "Feature" or not feature.get("geometry"):
            errors.append({"row": index, "message": "Feature has no valid geometry"})
            continue
        if administrative:
            properties = feature.get("properties") or {}
            required = {"level", "code", "name"}
            missing = required - set(properties)
            if missing:
                errors.append(
                    {"row": index, "message": f"Missing properties: {', '.join(sorted(missing))}"}
                )
            if properties.get("level") not in {"state", "lga", "ward", "registration_area"}:
                errors.append({"row": index, "message": "Invalid administrative level"})
            if properties.get("level") != "state" and not properties.get("parent_code"):
                errors.append({"row": index, "message": "parent_code is required"})
    if administrative and not errors:
        codes = {
            level: {
                feature["properties"]["code"]
                for feature in data["features"]
                if feature["properties"]["level"] == level
            }
            for level in ("state", "lga", "ward", "registration_area")
        }
        parent_level = {"lga": "state", "ward": "lga", "registration_area": "ward"}
        for index, feature in enumerate(data["features"], start=1):
            properties = feature["properties"]
            level = properties["level"]
            if level != "state" and properties["parent_code"] not in codes[parent_level[level]]:
                errors.append(
                    {
                        "row": index,
                        "message": f"Unknown parent_code: {properties['parent_code']}",
                    }
                )
    return ValidationResult(data["features"], errors, checksum)
