"""
인증 API 엔드포인트
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.security import create_access_token, get_current_user
from app.models.base import ResponseModel

logger = logging.getLogger("ds")

router = APIRouter()


class TokenResponse(ResponseModel):
    """토큰 응답 모델"""
    access_token: str = ""
    token_type: str = "bearer"
    expires_in: int = 604800  # 7 days in seconds


@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    사용자 로그인하여 JWT 토큰을 발급합니다.

    테스트용 간단한 인증을 제공합니다.
    운영 환경에서는 실제 사용자 데이터베이스와 연동해야 합니다.

    Args:
        form_data: OAuth2 로그인 폼 데이터
            - username: 사용자 이름
            - password: 비밀번호

    Returns:
        TokenResponse: JWT 액세스 토큰

    Raises:
        HTTPException: 인증 실패 시 401 에러
    """
    # 테스트용 간단한 인증 (운영 환경에서는 실제 DB 확인 필요)
    if form_data.username == "test_user" and form_data.password == "test_password":
        access_token = create_access_token(
            data={
                "username": form_data.username,
                "user_id": "1"
            }
        )

        logger.info(f"User {form_data.username} logged in successfully")

        return TokenResponse(
            success=True,
            message="로그인 성공",
            access_token=access_token,
            token_type="bearer",
            expires_in=604800
        )

    logger.warning(f"Failed login attempt for user: {form_data.username}")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="사용자명 또는 비밀번호가 잘못되었습니다",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post("/logout")
async def logout(current_user = Depends(get_current_user)):
    """
    사용자 로그아웃 처리합니다.

    JWT 토큰은 stateless이므로 서버에서 별도 처리는 없으며,
    클라이언트에서 토큰을 삭제하면 됩니다.

    Returns:
        ResponseModel: 로그아웃 성공 메시지
    """
    logger.info(f"User {current_user.get('username')} logged out")
    return ResponseModel(
        success=True,
        message="로그아웃 성공"
    )