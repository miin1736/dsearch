"""
User 모델 정의

사용자 관련 데이터 모델들을 정의합니다.
Pydantic BaseModel을 사용하여 데이터 검증 및 직렬화를 수행합니다.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator
from enum import Enum

from .base import BaseModel as Base, TimestampMixin


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


class UserBase(Base):
    """
    사용자 기본 모델.

    사용자 생성 및 업데이트에 공통으로 사용되는 필드들을 정의합니다.
    """
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[str] = Field(default=None, pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')  # 변경: regex -> pattern
    full_name: Optional[str] = Field(default=None, max_length=100)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)

    @validator('username')
    def validate_username(cls, v):
        if not v.isalnum():
            raise ValueError('Username must be alphanumeric')
        return v.lower()


class UserCreate(UserBase):
    """
    사용자 생성 모델.

    사용자 생성 시 필요한 추가 필드들을 정의합니다.
    """
    password: str = Field(..., min_length=8, max_length=100)

    @validator('password')
    def validate_password(cls, v):
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c.isalpha() for c in v):
            raise ValueError('Password must contain at least one letter')
        return v


class UserUpdate(UserBase):
    """
    사용자 업데이트 모델.

    사용자 업데이트 시 필요한 필드들을 정의합니다.
    """
    password: Optional[str] = Field(default=None, min_length=8)
    email: Optional[str] = Field(default=None, pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')  # 변경: regex -> pattern
    full_name: Optional[str] = Field(default=None, max_length=100)
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    is_superuser: Optional[bool] = None


class UserPasswordUpdate(Base):
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
    """
    사용자 모델.

    데이터베이스에서 조회된 사용자 정보를 표현합니다.
    """
    id: str
    hashed_password: str
    last_login: Optional[str] = None
    login_count: int = Field(default=0)

    # Permissions and settings
    allowed_categories: Optional[List[str]] = None
    search_preferences: Optional[dict] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # 변경: orm_mode -> from_attributes (필요 시)
        populate_by_name = True  # 변경: allow_population_by_field_name -> populate_by_name (필요 시)


class UserInDB(User):
    """User model as stored in database."""

    hashed_password: str


class UserLogin(Base):
    """User login model."""

    username: str
    password: str


class UserToken(Base):
    """User token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: User


class UserActivity(Base):
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