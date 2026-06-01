from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.enums import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    phone: str | None = None
    password: str
    full_name: str
    role: UserRole
    preferences: dict | None = None


class CaregiverCreate(BaseModel):
    email: EmailStr
    phone: str | None = None
    password: str
    full_name: str
    preferences: dict | None = None


class UserUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    is_active: bool | None = None
    preferences: dict | None = None


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    phone: str | None = None
    full_name: str
    role: UserRole
    is_active: bool
    consent_given: bool
    consent_date: datetime | None
    preferences: dict | None


class ConsentUpdate(BaseModel):
    consent_given: bool
