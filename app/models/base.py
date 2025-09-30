"""
기본 모델 클래스

전체 애플리케이션에서 사용되는 기본 모델 클래스들을 정의합니다.
기본 설정, 타임스탬프 믹스인, API 응답 모델, 페이지네이션 등을 제공합니다.
"""

from pydantic import BaseModel as PydanticBaseModel, Field
from typing import Optional, Any, Dict
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
    """\n    표준 API 응답 모델.\n\n    API에서 공통적으로 사용되는 응답 형식을 정의합니다.\n    성공 여부, 메시지, 데이터, 오류 정보를 포함합니다.\n    """

    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None
    errors: Optional[Dict[str, Any]] = None


class PaginationParams(BaseModel):
    """\n    페이지네이션 매개변수 모델.\n\n    페이지 번호, 페이지 크기, 오프셋 등\n    페이지네이션에 필요한 매개변수들을 정의합니다.\n    """

    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

    @property
    def skip(self) -> int:
        return (self.page - 1) * self.size


class PaginatedResponse(BaseModel):
    """\n    페이지네이션 응답 모델.\n\n    페이지네이션이 적용된 데이터와 함께 총 개수, 현재 페이지,\n    전체 페이지 수 등의 메타데이터를 포함한 응답 모델입니다.\n    """

    total: int
    page: int
    size: int
    pages: int
    items: list

    @classmethod
    def create(cls, items: list, total: int, page: int, size: int):
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size
        )