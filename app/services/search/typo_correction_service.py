"""
오타 교정 서비스
"""
import logging
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger("ds")


class TypoCorrectionService:
    """오타 교정 관련 서비스"""
    
    def __init__(self):
        self.index_name = "ds_correct_typo"
    
    def get_corrections(
        self, 
        text: str, 
        size: int = 10,
        max_edits: int = 2,
        min_word_length: int = 8,
        prefix_length: int = 2
    ) -> List[Dict[str, Any]]:
        """
        오타 교정 제안 조회
        
        Args:
            text: 교정할 텍스트
            size: 반환할 제안 수
            max_edits: 최대 편집 거리
            min_word_length: 최소 단어 길이
            prefix_length: 접두사 길이
        
        Returns:
            List[Dict]: 교정 제안 목록
        """
        try:
            logger.info(f"오타 교정 요청 - text: {text}")
            
            # TODO: Elasticsearch term suggester 구현
            # es_client = get_elasticsearch_client()
            # query = {
            #     "suggest": {
            #         "typo_correction": {
            #             "text": text,
            #             "term": {
            #                 "field": "keyword",
            #                 "size": size,
            #                 "max_edits": max_edits,
            #                 "min_word_length": min_word_length,
            #                 "prefix_length": prefix_length,
            #                 "suggest_mode": "popular"
            #             }
            #         }
            #     }
            # }
            # result = es_client.search(index=self.index_name, body=query)
            
            # 임시 응답
            if "밤죄" in text:
                mock_corrections = [
                    {"text": "범죄도시", "score": 0.8, "freq": 100},
                    {"text": "범죄영화", "score": 0.6, "freq": 50}
                ]
            else:
                mock_corrections = [
                    {"text": f"{text}_교정1", "score": 0.7, "freq": 75},
                    {"text": f"{text}_교정2", "score": 0.5, "freq": 25}
                ]
            
            return mock_corrections[:size]
            
        except Exception as e:
            logger.error(f"오타 교정 조회 오류: {e}")
            return []
    
    def add_keyword(
        self, 
        keyword: str, 
        category: str = None, 
        category_id: str = None
    ) -> Dict[str, Any]:
        """
        오타 교정 키워드 추가
        
        Args:
            keyword: 추가할 키워드
            category: 카테고리
            category_id: 카테고리 ID
        
        Returns:
            Dict: 추가 결과
        """
        try:
            logger.info(f"오타 교정 키워드 추가 - keyword: {keyword}")
            
            # TODO: Elasticsearch 인덱싱 구현
            # es_client = get_elasticsearch_client()
            # doc = {
            #     "keyword": keyword,
            #     "category": category,
            #     "category_id": category_id,
            #     "created_at": datetime.now().isoformat()
            # }
            # result = es_client.index(index=self.index_name, body=doc)
            
            # 임시 응답
            return {
                "success": True,
                "keyword": keyword,
                "document_id": f"typo_mock_id_{keyword}_{int(datetime.now().timestamp())}"
            }
            
        except Exception as e:
            logger.error(f"오타 교정 키워드 추가 오류: {e}")
            raise


# 전역 인스턴스
typo_correction_service = TypoCorrectionService()