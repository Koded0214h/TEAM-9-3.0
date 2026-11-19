import csv
import io
import json
from typing import Any


def render_json_export(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, default=str) + "\n"


def render_comparison_csv(payload: dict[str, Any]) -> str:
    stream = io.StringIO(newline="")
    fields = [
        "polling_unit_id",
        "code",
        "change",
        "before_voters",
        "after_voters",
        "before_status",
        "after_status",
        "before_latitude",
        "before_longitude",
        "after_latitude",
        "after_longitude",
    ]
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in payload["comparison"]["polling_units"]:
        before, after = row.get("before") or {}, row.get("after") or {}
        writer.writerow(
            {
                "polling_unit_id": row["polling_unit_id"],
                "code": row["code"],
                "change": row["change"],
                "before_voters": before.get("voters"),
                "after_voters": after.get("voters", after.get("registered_voters")),
                "before_status": before.get("status"),
                "after_status": after.get("status"),
                "before_latitude": before.get("latitude"),
                "before_longitude": before.get("longitude"),
                "after_latitude": after.get("latitude"),
                "after_longitude": after.get("longitude"),
            }
        )
    return stream.getvalue()
