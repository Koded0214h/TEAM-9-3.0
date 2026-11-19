import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def email_lower(cls, value: str) -> str:
        return value.strip().lower()


class MFAChallengeRequest(BaseModel):
    challenge_token: str
    code: str = Field(min_length=6, max_length=20)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    status: str = "authenticated"
    access_token: str | None = None
    refresh_token: str | None = None
    challenge_token: str | None = None
    token_type: str = "bearer"
    expires_in: int | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    is_platform_admin: bool
    mfa_enabled: bool
    created_at: datetime


class MFASetupResponse(BaseModel):
    secret: str
    provisioning_uri: str


class MFACodeRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)


class MFAConfirmResponse(BaseModel):
    recovery_codes: list[str]


class MFADisableRequest(BaseModel):
    password: str
    code: str = Field(min_length=6, max_length=20)


class InvitationAccept(BaseModel):
    token: str
    full_name: str = Field(min_length=1, max_length=160)
    password: str = Field(min_length=12, max_length=128)
