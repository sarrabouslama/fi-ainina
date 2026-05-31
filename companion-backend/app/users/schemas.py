from datetime import datetime
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str
    preferences: dict | None = None


class UserUpdate(BaseModel):
    full_name: str | None = None
    is_active: bool | None = None
    preferences: dict | None = None


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    consent_given: bool
    consent_date: datetime | None
    preferences: dict | None


class ConsentUpdate(BaseModel):
    consent_given: bool
