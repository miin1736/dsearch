"""
보안 및 인증 관련 모듈
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings

logger = logging.getLogger("ds")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    JWT 액세스 토큰을 생성합니다.

    Args:
        data: 토큰에 포함할 데이터
        expires_delta: 만료 시간 (기본: 7일)

    Returns:
        str: JWT 토큰
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=7)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    현재 인증된 사용자를 가져옵니다.

    Args:
        token: JWT 토큰

    Returns:
        Dict[str, Any]: 사용자 정보

    Raises:
        HTTPException: 토큰이 유효하지 않으면 401 에러
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        username: str = payload.get("username")
        user_id: str = payload.get("user_id")

        if username is None or user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return {"username": username, "user_id": user_id}

    except JWTError as e:
        logger.error(f"JWT validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_optional(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[Dict[str, Any]]:
    """
    현재 인증된 사용자를 선택적으로 가져옵니다 (토큰 없어도 가능).

    Args:
        token: JWT 토큰 (선택사항)

    Returns:
        Optional[Dict[str, Any]]: 사용자 정보 또는 None
    """
    if not token:
        return None

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        username: str = payload.get("username")
        user_id: str = payload.get("user_id")

        if username is None or user_id is None:
            return None

        return {"username": username, "user_id": user_id}

    except JWTError as e:
        logger.error(f"JWT validation error: {e}")
        return None


async def get_super_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    슈퍼유저 권한을 확인합니다.

    Args:
        current_user: 현재 인증된 사용자

    Returns:
        Dict[str, Any]: 슈퍼유저 정보

    Raises:
        HTTPException: 슈퍼유저가 아니면 403 에러
    """
    # 간단한 슈퍼유저 확인 (실제 환경에서는 DB에서 확인)
    if current_user.get("username") == "admin" or current_user.get("user_id") == "1":
        return current_user
    
    # 설정에서 SUPER_KEY 확인 (추가 보안)
    if current_user.get("super_key") == settings.SUPER_KEY:
        return current_user

    logger.warning(f"Unauthorized super user access attempt by {current_user.get('username')}")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="슈퍼유저 권한이 필요합니다"
    )