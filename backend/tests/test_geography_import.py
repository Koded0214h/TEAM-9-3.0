from app.services.geography_import import validate_geography_csv


def test_valid_hierarchy():
    data = (
        b"level,code,name,parent_code\n"
        b"state,LA,Lagos,\n"
        b"lga,IKJ,Ikeja,LA\n"
        b"ward,W1,Ward 1,IKJ\n"
        b"polling_unit,PU1,Unit 1,W1\n"
    )
    result = validate_geography_csv(data)
    assert result.errors == []
    assert len(result.rows) == 4


def test_unknown_parent_is_rejected():
    data = b"level,code,name,parent_code\nward,W1,Ward 1,MISSING\n"
    result = validate_geography_csv(data)
    assert result.errors[0]["message"] == "Unknown parent_code: MISSING"
