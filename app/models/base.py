"""
기본 모델 클래스

전체 애플리케이션에서 사용되는 기본 모델 클래스들을 정의합니다.
기본 설정, 타임스탬프 믹스인, API 응답 모델, 페이지네이션 등을 제공합니다.
"""

from pydantic import BaseModel as PydanticBaseModel, Field
from typing import Optional, Any, Dict, List
from datetime import datetime


class BaseModel(PydanticBaseModel):
    """\n    공통 설정을 가진 기본 모델.\n\n    Pydantic 기반의 기본 모델로, ORM 모드 지원, 필드 이름 별칭,\n    enum 값 사용, 할당 유효성 검사 등의 기본 설정을 제공합니다.\n    """

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        use_enum_values = True
        validate_assignment = True


class TimestampMixin(BaseModel):
    """\n    타임스탬프 필드를 위한 믹스인 모델.\n\n    생성 시간(created_at)과 수정 시간(updated_at) 필드를\n    자동으로 추가하는 믹스인 모델입니다.\n    """

    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


class ResponseModel(BaseModel):
    """기본 응답 모델"""
    success: bool = Field(default=True, description="성공 여부")
    message: str = Field(default="요청이 성공적으로 처리되었습니다", description="응답 메시지")
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "요청이 성공적으로 처리되었습니다"
            }
        }
    }


class ErrorResponse(BaseModel):
    """오류 응답 모델"""
    success: bool = Field(default=False, description="성공 여부")
    message: str = Field(..., description="오류 메시지")
    error_code: Optional[str] = Field(default=None, description="오류 코드")
    details: Optional[Any] = Field(default=None, description="상세 정보")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": False,
                "message": "요청 처리 중 오류가 발생했습니다",
                "error_code": "INTERNAL_ERROR",
                "details": None
            }
        }
    }


class PaginationParams(BaseModel):
    """\n    페이지네이션 매개변수 모델.\n\n    페이지 번호, 페이지 크기, 오프셋 등\n    페이지네이션에 필요한 매개변수들을 정의합니다.\n    """

    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

    @property
    def skip(self) -> int:
        return (self.page - 1) * self.size


class PaginatedResponse(ResponseModel):
    """페이지네이션 응답 모델"""
    total: int = Field(..., description="전체 개수")
    page: int = Field(..., description="현재 페이지")
    size: int = Field(..., description="페이지 크기")
    pages: int = Field(..., description="전체 페이지 수")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "데이터 조회 완료",
                "total": 100,
                "page": 1,
                "size": 10,
                "pages": 10
            }
        }
    }