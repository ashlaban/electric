"""User Pydantic schemas for request/response validation."""

from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    """Base user schema."""

    username: str
    email: EmailStr


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str


class UserResponse(UserBase):
    """Schema for user response."""

    id: int
    created_at: datetime
    is_active: bool
    phone_number: str | None = None
    default_property_id: int | None = None
    default_meter_id: int | None = None

    model_config = {"from_attributes": True}


class UserPreferencesUpdate(BaseModel):
    """Schema for updating user meter preferences."""

    phone_number: str | None = None
    default_property_id: int | None = None
    default_meter_id: int | None = None


class Token(BaseModel):
    """Schema for JWT token response."""

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Schema for token payload data."""

    username: str | None = None


class LoginRequest(BaseModel):
    """Schema for login request."""

    username: str
    password: str
