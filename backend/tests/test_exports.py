import json

from app.services.exports import render_comparison_csv, render_json_export


def _payload() -> dict:
    return {
        "scenario": {"id": "demo"},
        "comparison": {
            "polling_units": [
                {
                    "polling_unit_id": "pu-1",
                    "code": "25/11/01/001",
                    "change": "relocated",
                    "before": {
                        "voters": 500,
                        "status": "active",
                        "latitude": 6.5,
                        "longitude": 3.3,
                    },
                    "after": {
                        "voters": 500,
                        "status": "active",
                        "latitude": 6.51,
                        "longitude": 3.31,
                    },
                }
            ]
        },
    }


def test_json_export_is_readable() -> None:
    rendered = render_json_export(_payload())
    assert json.loads(rendered)["scenario"]["id"] == "demo"


def test_csv_export_contains_before_and_after() -> None:
    rendered = render_comparison_csv(_payload())
    assert "before_voters,after_voters" in rendered
    assert "25/11/01/001" in rendered
    assert "6.51" in rendered
