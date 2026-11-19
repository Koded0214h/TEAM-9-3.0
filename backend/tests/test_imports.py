from app.services.imports import validate_geojson, validate_polling_unit_csv


def test_valid_polling_unit_csv() -> None:
    result = validate_polling_unit_csv(
        b"code,name,address,ward_code,latitude,longitude,registered_voters\n"
        b"PU1,Alpha,Main Road,W1,6.5,3.4,100\n"
    )
    assert len(result.rows) == 1
    assert result.errors == []
    assert len(result.checksum) == 64


def test_polling_unit_csv_reports_row_errors() -> None:
    result = validate_polling_unit_csv(
        b"code,name,address,ward_code,latitude,longitude,registered_voters\nPU1,Alpha,Road,W1,200,3.4,-1\n"
    )
    assert result.rows == []
    assert result.errors[0]["row"] == 2


def test_geojson_requires_feature_collection() -> None:
    result = validate_geojson(b'{"type":"Point","coordinates":[3,6]}')
    assert result.errors


def test_valid_geojson() -> None:
    result = validate_geojson(
        b'{"type":"FeatureCollection","features":[{"type":"Feature","properties":{},"geometry":{"type":"Point","coordinates":[3,6]}}]}'
    )
    assert len(result.rows) == 1
    assert result.errors == []
