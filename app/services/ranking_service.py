"""
Ranking Service - 인기검색어, 최근검색어, 인기문서 처리
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from elasticsearch_dsl import Search, Q

from app.models.ranking import (
    RankingSearchRequest,
    RankingDocumentRequest,
    RecentSearchRequest,
    RankingItem,
    DocumentRankingItem
)
from app.services.elasticsearch import elasticsearch_service

logger = logging.getLogger("ds")


class RankingService:
    """랭킹 서비스 - 검색어/문서 랭킹 및 최근 검색어"""

    def __init__(self):
        self.log_index = "ds_log"

    async def get_search_ranking(self, request: RankingSearchRequest) -> List[RankingItem]:
        """
        인기 검색어 조회

        Args:
            request: 인기검색어 요청 (일수, 상위 N개)

        Returns:
            List[RankingItem]: 인기 검색어 목록
        """
        try:
            days = request.howRequestDays
            topn = request.howRequestTopN

            now = datetime.now()
            from_date = now + timedelta(days=-days)

            logger.info(f"rankingSearch - days: {days}, topN: {topn}, fromDate: {from_date}")

            client = elasticsearch_service.get_client()

            # Search 객체 생성
            s = Search(using=client, index=self.log_index)

            # 검색어가 비어있지 않은 것만 조회
            q = Q('bool', must_not=[Q('term', whatTargetSearchWord='')])
            s = s.query(q)

            # 검색어 집계 (상위 N개)
            s.aggs.bucket('rankingSearch', 'terms', field='whatTargetSearchWord.keyword', size=topn)

            logger.info(f"Search Ranking Query: {s.to_dict()}")

            result = s.execute()

            # 결과 파싱
            ranking_array = []
            if hasattr(result, 'aggregations') and 'rankingSearch' in result.aggregations:
                for bucket in result.aggregations['rankingSearch'].buckets:
                    ranking_array.append(
                        RankingItem(
                            label=bucket.key,
                            value=bucket.key
                        )
                    )

            logger.info(f"Found {len(ranking_array)} popular search terms")
            return ranking_array

        except Exception as e:
            logger.error(f"Error getting search ranking: {e}")
            return []

    async def get_document_ranking(self, request: RankingDocumentRequest) -> List[DocumentRankingItem]:
        """
        인기 문서 조회

        Args:
            request: 인기문서 요청 (일수, 상위 N개)

        Returns:
            List[DocumentRankingItem]: 인기 문서 목록
        """
        try:
            days = request.howRequestDays
            topn = request.howRequestTopN

            now = datetime.now()
            from_date = now + timedelta(days=-days)

            logger.info(f"documentRanking - days: {days}, topN: {topn}, fromDate: {from_date}")

            client = elasticsearch_service.get_client()

            # Search 객체 생성
            s = Search(using=client, index=self.log_index)

            # view 액션이고 document 타입인 것만 조회
            q = Q('bool',
                must=[
                    Q('range', whenCreated={'gt': from_date.isoformat()}),
                    Q('term', howAction='view'),
                    Q('term', whatTargetType='document')
                ]
            )
            s = s.query(q)

            # 문서 제목으로 집계하고, 각 제목별로 문서 ID도 집계
            s.aggs.bucket('documentRanking', 'terms', field='whatTargetDocumentTitle.keyword', size=topn) \
                .bucket('id', 'terms', field='whatTargetDocumentId.keyword', size=topn)

            logger.info(f"Document Ranking Query: {s.to_dict()}")

            result = s.execute()

            # 결과 파싱
            ranking_array = []
            rank = 0

            if hasattr(result, 'aggregations') and 'documentRanking' in result.aggregations:
                for bucket in result.aggregations['documentRanking'].buckets:
                    rank += 1
                    doc_id = bucket.id.buckets[0].key if bucket.id.buckets else ""

                    ranking_array.append(
                        DocumentRankingItem(
                            doc_rank=rank,
                            doc_title=bucket.key,
                            doc_score=bucket.doc_count,
                            doc_id=doc_id
                        )
                    )

            logger.info(f"Found {len(ranking_array)} popular documents")
            return ranking_array

        except Exception as e:
            logger.error(f"Error getting document ranking: {e}")
            return []

    async def get_recent_searches(self, request: RecentSearchRequest) -> List[RankingItem]:
        """
        최근 검색어 조회

        Args:
            request: 최근검색어 요청 (사용자 ID, 일수, 개수)

        Returns:
            List[RankingItem]: 최근 검색어 목록
        """
        try:
            user_id = request.whoUserId
            target_action = 'search'
            recent_text = request.howRequestRecentText
            when_created_days = request.whenCreated

            from_date = (datetime.now() - timedelta(days=when_created_days)).isoformat()

            logger.info(f"recentSearch - userId: {user_id}, days: {when_created_days}, limit: {recent_text}")

            client = elasticsearch_service.get_client()

            # Search 객체 생성
            s = Search(using=client, index=self.log_index)

            # 쿼리 구성
            if user_id:
                q = Q('bool',
                    must=[
                        Q('range', whenCreated={'gte': from_date}),
                        Q('match', whatTargetAction=target_action),
                        Q('match', userId=user_id)
                    ]
                )
            else:
                q = Q('bool',
                    must=[
                        Q('range', whenCreated={'gte': from_date}),
                        Q('match', whatTargetAction=target_action)
                    ]
                )

            s = s.query(q)

            # 최근 순으로 정렬
            s = s.sort({'whenCreated': {'order': 'desc'}})

            # 충분한 결과 가져오기
            s = s[0:recent_text * 3]

            logger.info(f"Recent Search Query: {s.to_dict()}")

            result = s.execute()

            # 결과 파싱 (중복 제거)
            recent_array = []
            seen_words = set()

            for hit in result.hits:
                if hasattr(hit, 'whatTargetSearchWord') and hit.whatTargetSearchWord:
                    search_word = hit.whatTargetSearchWord
                    if search_word not in seen_words:
                        seen_words.add(search_word)
                        recent_array.append(
                            RankingItem(
                                label=search_word,
                                value=search_word
                            )
                        )

                    if len(recent_array) >= recent_text:
                        break

            logger.info(f"Found {len(recent_array)} recent search terms")
            return recent_array

        except Exception as e:
            logger.error(f"Error getting recent searches: {e}")
            return []


# Global instance
ranking_service = RankingService()