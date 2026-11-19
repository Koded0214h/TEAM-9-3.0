import uuid

import pytest

from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


def test_password_hash_round_trip() -> None:
    password_hash = hash_password("a-strong-test-password")
    assert password_hash != "a-strong-test-password"
    assert verify_password("a-strong-test-password", password_hash)
    assert not verify_password("incorrect-password", password_hash)


def test_access_token_round_trip() -> None:
    user_id = uuid.uuid4()
    token, expires_in = create_access_token(user_id, ["reviewer"])
    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["roles"] == ["reviewer"]
    assert expires_in == 900


def test_invalid_access_token_is_rejected() -> None:
    with pytest.raises(AppError) as error:
        decode_access_token("not-a-token")
    assert error.value.code == "invalid_token"


def test_refresh_tokens_are_hashed_deterministically() -> None:
    assert hash_refresh_token("secret") == hash_refresh_token("secret")
    assert hash_refresh_token("secret") != hash_refresh_token("other")
