import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pyotp
from pwdlib import PasswordHash

from app.core.config import get_settings
from app.core.errors import AppError

password_hasher = PasswordHash.recommended()


def hash_password(value: str) -> str:
    return password_hasher.hash(value)


def verify_password(value: str, digest: str) -> bool:
    return password_hasher.verify(value, digest)


def hash_token(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def random_token() -> str:
    return secrets.token_urlsafe(48)


def create_access_token(user_id: uuid.UUID, *, mfa: bool) -> tuple[str, int]:
    settings = get_settings()
    lifetime = timedelta(minutes=settings.access_token_minutes)
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(user_id),
            "type": "access",
            "mfa": mfa,
            "iat": now,
            "exp": now + lifetime,
            "jti": str(uuid.uuid4()),
        },
        settings.auth_secret_key,
        algorithm="HS256",
    )
    return token, int(lifetime.total_seconds())


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, get_settings().auth_secret_key, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise AppError("invalid_token", "Access token is invalid or expired", 401) from exc
    if payload.get("type") != "access":
        raise AppError("invalid_token", "Access token is invalid", 401)
    return payload


def create_mfa_challenge(user_id: uuid.UUID) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "type": "mfa_challenge",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        get_settings().auth_secret_key,
        algorithm="HS256",
    )


def decode_mfa_challenge(token: str) -> uuid.UUID:
    try:
        payload = jwt.decode(token, get_settings().auth_secret_key, algorithms=["HS256"])
        if payload.get("type") != "mfa_challenge":
            raise ValueError
        return uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise AppError("invalid_mfa_challenge", "MFA challenge is invalid or expired", 401) from exc


def new_totp_secret() -> str:
    return pyotp.random_base32()


def verify_totp(secret: str, code: str) -> bool:
    return pyotp.TOTP(secret).verify(code, valid_window=1)


def provisioning_uri(secret: str, email: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(email, issuer_name=get_settings().totp_issuer)
