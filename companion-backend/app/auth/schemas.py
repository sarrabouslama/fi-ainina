from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.enums import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'


class MeResponse(BaseModel):
    id: str
    email: EmailStr
    phone: str | None = None
    full_name: str
    role: UserRole
    consent_given: bool
    consent_date: datetime | None = None
