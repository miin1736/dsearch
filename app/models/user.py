"""
User Models - 사용자 관리
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class UserRole(str, Enum):
    """사용자 역할"""
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class UserStatus(str, Enum):
    """사용자 상태"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class UserBase(BaseModel):
    """기본 사용자 모델"""
    username: str = Field(..., min_length=3, max_length=50, description="사용자명")
    email: Optional[str] = Field(default=None, pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$', description="이메일")
    full_name: Optional[str] = Field(default=None, max_length=100, description="전체 이름")
    role: UserRole = Field(default=UserRole.USER, description="사용자 역할")
    status: UserStatus = Field(default=UserStatus.ACTIVE, description="사용자 상태")
    is_superuser: bool = Field(default=False, description="슈퍼유저 여부")

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        """사용자명 검증"""
        if not v.isalnum():
            raise ValueError('사용자명은 영문, 숫자만 가능합니다')
        return v.lower()


class UserCreate(UserBase):
    """사용자 생성 모델"""
    password: str = Field(..., min_length=8, max_length=100, description="비밀번호")

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """비밀번호 검증"""
        if not any(c.isdigit() for c in v):
            raise ValueError('비밀번호는 최소 1개의 숫자를 포함해야 합니다')
        if not any(c.isalpha() for c in v):
            raise ValueError('비밀번호는 최소 1개의 문자를 포함해야 합니다')
        return v


class UserUpdate(BaseModel):
    """사용자 업데이트 모델"""
    email: Optional[str] = Field(default=None, pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    full_name: Optional[str] = Field(default=None, max_length=100)
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    is_superuser: Optional[bool] = None


class UserPasswordUpdate(BaseModel):
    """사용자 비밀번호 변경 모델"""
    current_password: str = Field(..., description="현재 비밀번호")
    new_password: str = Field(..., min_length=8, max_length=100, description="새 비밀번호")

    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v):
        """비밀번호 검증"""
        if not any(c.isdigit() for c in v):
            raise ValueError('비밀번호는 최소 1개의 숫자를 포함해야 합니다')
        if not any(c.isalpha() for c in v):
            raise ValueError('비밀번호는 최소 1개의 문자를 포함해야 합니다')
        return v


class User(UserBase):
    """전체 사용자 모델"""
    id: str = Field(..., description="사용자 ID")
    last_login: Optional[datetime] = Field(default=None, description="마지막 로그인 시간")
    login_count: int = Field(default=0, description="로그인 횟수")
    allowed_categories: Optional[List[str]] = Field(default=None, description="허용된 카테고리")
    search_preferences: Optional[dict] = Field(default=None, description="검색 선호도")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="생성 시간")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="업데이트 시간")

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """사용자 로그인 모델"""
    username: str = Field(..., description="사용자명")
    password: str = Field(..., description="비밀번호")


class UserToken(BaseModel):
    """사용자 토큰 응답"""
    access_token: str = Field(..., description="액세스 토큰")
    token_type: str = Field(default="bearer", description="토큰 타입")
    expires_in: int = Field(..., description="만료 시간(초)")
    user: User = Field(..., description="사용자 정보")


class UserActivity(BaseModel):
    """사용자 활동 로그"""
    user_id: str = Field(..., description="사용자 ID")
    action: str = Field(..., description="액션 유형")
    resource: Optional[str] = Field(default=None, description="리소스")
    details: Optional[dict] = Field(default=None, description="상세 정보")
    ip_address: Optional[str] = Field(default=None, description="IP 주소")
    user_agent: Optional[str] = Field(default=None, description="User Agent")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="타임스탬프")

    class Config:
        from_attributes = True