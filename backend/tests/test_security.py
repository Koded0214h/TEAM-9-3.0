import pyotp

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    new_totp_secret,
    verify_password,
    verify_totp,
)


def test_password_hash_and_access_token_round_trip():
    encoded = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("wrong", encoded)
    token, _ = create_access_token("00000000-0000-0000-0000-000000000001", mfa=True)
    payload = decode_access_token(token)
    assert payload["mfa"] is True


def test_totp_round_trip():
    secret = new_totp_secret()
    assert verify_totp(secret, pyotp.TOTP(secret).now())
