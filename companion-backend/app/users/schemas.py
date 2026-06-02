from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.enums import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    phone: str | None = None
    password: str
    full_name: str
    role: UserRole
    consent_given: bool = False
    preferences: dict | None = None


class CaregiverCreate(BaseModel):
    """Used when creating a caregiver directly linked to an elderly person."""
    email: EmailStr
    phone: str | None = None
    password: str
    full_name: str
    consent_given: bool = False


class UserUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    is_active: bool | None = None
    preferences: dict | None = None


class UserResponse(BaseModel):
    id: str
    email: str          # str not EmailStr — GDPR-erased accounts use example.invalid domain
    phone: str | None = None
    full_name: str
    role: UserRole
    is_active: bool
    consent_given: bool
    consent_date: datetime | None
    preferences: dict | None


class ConsentUpdate(BaseModel):
    consent_given: bool


class PasswordChange(BaseModel):
    current_password: str
    new_password: str
