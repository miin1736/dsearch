"""
Ranking Models - 인기검색어, 최근검색어, 문서 랭킹
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class RankingSearchRequest(BaseModel):
    """검색어 랭킹 요청 모델"""
    howRequestDays: int = Field(default=7, ge=1, le=365, description="조회 기간(일)")
    howRequestTopN: int = Field(default=10, ge=1, le=100, description="상위 N개")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "howRequestDays": 7,
                "howRequestTopN": 10
            }
        }
    }


class RankingDocumentRequest(BaseModel):
    """인기 문서 요청 모델"""
    howRequestDays: int = Field(default=7, description="조회할 일수")
    howRequestTopN: int = Field(default=10, description="상위 N개 문서")


class RecentSearchRequest(BaseModel):
    """최근 검색어 요청 모델"""
    whoUserId: Optional[str] = Field(default=None, description="사용자 ID")
    whoUserName: Optional[str] = Field(default=None, description="사용자 이름/팀")
    howRequestRecentText: int = Field(default=10, description="최근 검색어 개수")
    whenCreated: int = Field(default=7, description="조회할 일수")


class RankingItem(BaseModel):
    """랭킹 아이템"""
    label: str = Field(..., description="표시 라벨")
    value: str = Field(..., description="값")


class DocumentRankingItem(BaseModel):
    """문서 랭킹 아이템"""
    doc_rank: int = Field(..., description="순위")
    doc_title: str = Field(..., description="문서 제목")
    doc_score: int = Field(..., description="조회수")
    doc_id: str = Field(..., description="문서 ID")


class RankingSearchResponse(BaseModel):
    """인기 검색어 응답"""
    ds_response: List[RankingItem]


class RankingDocumentResponse(BaseModel):
    """인기 문서 응답"""
    ds_response: List[DocumentRankingItem]


class RecentSearchResponse(BaseModel):
    """최근 검색어 응답"""
    ds_response: List[RankingItem]