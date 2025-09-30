"""
보안 및 인증 관리 모듈
"""

from typing import Optional
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta

from .config import settings


security = HTTPBearer()


class AuthenticationError(HTTPException):
    """
    인증 오류 예외 클래스.

    JWT 토큰 검증 실패나 인증 오류 시 발생하는 커스텀 예외입니다.
    """

    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    JWT 액세스 토큰을 생성합니다.

    Args:
        data (dict): 토큰에 포함될 페이로드 데이터
        expires_delta (Optional[timedelta]): 토큰 만료 시간 (기본값: 7일)

    Returns:
        str: 생성된 JWT 토큰
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def verify_token(token: str) -> dict:
    """
    JWT 토큰을 검증하고 페이로드를 반환합니다.

    Args:
        token (str): 검증할 JWT 토큰

    Returns:
        dict: 토큰에서 추출한 페이로드 데이터

    Raises:
        AuthenticationError: 토큰이 유효하지 않은 경우
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.PyJWTError:
        raise AuthenticationError("Invalid token")


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    현재 인증된 사용자 정보를 가져옵니다.

    Args:
        credentials: HTTP Bearer 인증 정보

    Returns:
        dict: 사용자 정보가 담긴 페이로드

    Raises:
        AuthenticationError: 인증이 실패한 경우
    """
    if not credentials:
        raise AuthenticationError("No credentials provided")

    return verify_token(credentials.credentials)


def verify_super_key(key: str) -> bool:
    """
    관리자 권한을 위한 슈퍼 키를 검증합니다.

    Args:
        key (str): 검증할 슈퍼 키

    Returns:
        bool: 키가 유효한 경우 True, 그렇지 않으면 False
    """
    return key == settings.SUPER_KEY


async def get_super_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    슈퍼 키 검증을 포함한 현재 사용자 정보를 가져옵니다.

    관리자 권한이 필요한 엔드포인트에서 사용되는 의존성 함수입니다.

    Args:
        credentials: HTTP Bearer 인증 정보

    Returns:
        dict: 슈퍼 권한을 가진 사용자 정보

    Raises:
        HTTPException: 슈퍼 키 검증에 실패한 경우 (403 Forbidden)
    """
    user = get_current_user(credentials)

    # Check if user has super key
    if not verify_super_key(user.get("super_key", "")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )

    return user