"""
User Models
"""

from typing import Optional, List
from pydantic import Field, validator
from enum import Enum

from .base import BaseModel, TimestampMixin


class UserRole(str, Enum):
    """User role enumeration."""
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class UserStatus(str, Enum):
    """User status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class UserBase(BaseModel):
    """Base user model."""

    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[str] = Field(default=None, regex=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    full_name: Optional[str] = Field(default=None, max_length=100)
    role: UserRole = Field(default=UserRole.USER)
    status: UserStatus = Field(default=UserStatus.ACTIVE)
    is_superuser: bool = Field(default=False)

    @validator('username')
    def validate_username(cls, v):
        if not v.isalnum():
            raise ValueError('Username must be alphanumeric')
        return v.lower()


class UserCreate(UserBase):
    """User creation model."""

    password: str = Field(..., min_length=8, max_length=100)

    @validator('password')
    def validate_password(cls, v):
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c.isalpha() for c in v):
            raise ValueError('Password must contain at least one letter')
        return v


class UserUpdate(BaseModel):
    """User update model."""

    email: Optional[str] = Field(default=None, regex=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    full_name: Optional[str] = Field(default=None, max_length=100)
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    is_superuser: Optional[bool] = None


class UserPasswordUpdate(BaseModel):
    """User password update model."""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @validator('new_password')
    def validate_password(cls, v):
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c.isalpha() for c in v):
            raise ValueError('Password must contain at least one letter')
        return v


class User(UserBase, TimestampMixin):
    """Full user model."""

    id: str
    hashed_password: str
    last_login: Optional[str] = None
    login_count: int = Field(default=0)

    # Permissions and settings
    allowed_categories: Optional[List[str]] = None
    search_preferences: Optional[dict] = None

    class Config:
        orm_mode = True


class UserInDB(User):
    """User model as stored in database."""

    hashed_password: str


class UserLogin(BaseModel):
    """User login model."""

    username: str
    password: str


class UserToken(BaseModel):
    """User token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: User


class UserActivity(BaseModel):
    """User activity log."""

    user_id: str
    action: str
    resource: Optional[str] = None
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: str

    class Config:
        orm_mode = True