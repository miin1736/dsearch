"""
Text Analysis Service
"""

import re
from typing import List, Dict, Any, Optional
from elasticsearch import Elasticsearch
import logging

from app.core.config import settings
from app.services.elasticsearch import elasticsearch_service

logger = logging.getLogger("ds")


class TextAnalyzer:
    """Text analysis and processing service."""

    def __init__(self):
        self.detail_search_pattern = re.compile(r'[\"]{1}([^\"]*)[\"]{1}')

    async def analyze_query(self, query: str) -> str:
        """Analyze and clean query text."""
        try:
            # Remove extra whitespace
            cleaned_query = re.sub(r'\s+', ' ', query.strip())

            # Handle Korean text normalization if needed
            # This is a placeholder for more sophisticated Korean text processing

            return cleaned_query

        except Exception as e:
            logger.error(f"Error analyzing query: {e}")
            return query

    async def extract_phrases(self, query: str) -> List[str]:
        """Extract quoted phrases from query."""
        phrases = []
        matches = self.detail_search_pattern.findall(query)

        for match in matches:
            if match.strip():
                phrases.append(match.strip())

        return phrases

    async def remove_phrases(self, query: str) -> str:
        """Remove quoted phrases from query, returning the remaining text."""
        return self.detail_search_pattern.sub('', query).strip()

    async def suggest_corrections(self, query: str, index_name: str = "ds_content") -> List[str]:
        """Get spelling suggestions using Elasticsearch suggest API."""
        try:
            client = elasticsearch_service.get_client()

            # Build suggest query
            suggest_body = {
                "suggest": {
                    "text": query,
                    "simple_phrase": {
                        "phrase": {
                            "field": "title",
                            "size": 5,
                            "gram_size": 3,
                            "direct_generator": [{
                                "field": "title",
                                "suggest_mode": "always"
                            }],
                            "highlight": {
                                "pre_tag": "<em>",
                                "post_tag": "</em>"
                            }
                        }
                    }
                }
            }

            response = client.search(index=index_name, body=suggest_body)

            suggestions = []
            if "suggest" in response and "simple_phrase" in response["suggest"]:
                for suggest_item in response["suggest"]["simple_phrase"]:
                    for option in suggest_item.get("options", []):
                        suggestions.append(option["text"])

            return suggestions[:5]  # Return top 5 suggestions

        except Exception as e:
            logger.error(f"Error getting spelling suggestions: {e}")
            return []

    async def get_auto_completions(self, prefix: str, field: str = "title",
                                   index_name: str = "ds_content", size: int = 10) -> List[str]:
        """Get auto-completion suggestions."""
        try:
            client = elasticsearch_service.get_client()

            # Use completion suggester if available, otherwise use prefix query
            try:
                # Try completion suggester first
                suggest_body = {
                    "suggest": {
                        "title_suggest": {
                            "prefix": prefix,
                            "completion": {
                                "field": f"{field}_suggest",
                                "size": size
                            }
                        }
                    }
                }

                response = client.search(index=index_name, body=suggest_body)

                completions = []
                if "suggest" in response and "title_suggest" in response["suggest"]:
                    for suggest_item in response["suggest"]["title_suggest"]:
                        for option in suggest_item.get("options", []):
                            completions.append(option["text"])

                return completions

            except:
                # Fallback to prefix query
                search_body = {
                    "query": {
                        "prefix": {
                            f"{field}.keyword": prefix
                        }
                    },
                    "_source": [field],
                    "size": size
                }

                response = client.search(index=index_name, body=search_body)

                completions = []
                for hit in response["hits"]["hits"]:
                    if field in hit["_source"]:
                        text = hit["_source"][field]
                        if text and text.lower().startswith(prefix.lower()):
                            completions.append(text)

                return list(set(completions))  # Remove duplicates

        except Exception as e:
            logger.error(f"Error getting auto completions: {e}")
            return []

    async def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from text using Elasticsearch analyze API."""
        try:
            client = elasticsearch_service.get_client()

            # Use Korean analyzer (nori) for keyword extraction
            analyze_body = {
                "analyzer": "nori",
                "text": text
            }

            response = client.indices.analyze(body=analyze_body)

            # Extract tokens and filter by relevance
            keywords = []
            for token in response.get("tokens", []):
                token_text = token["token"]
                # Filter out very short tokens and common words
                if len(token_text) >= 2 and token_text not in ["있다", "하다", "되다", "이다"]:
                    keywords.append(token_text)

            # Remove duplicates and return top keywords
            unique_keywords = list(dict.fromkeys(keywords))  # Preserve order
            return unique_keywords[:max_keywords]

        except Exception as e:
            logger.error(f"Error extracting keywords: {e}")
            return []

    async def highlight_text(self, text: str, keywords: List[str],
                           pre_tag: str = "<mark>", post_tag: str = "</mark>") -> str:
        """Highlight keywords in text."""
        try:
            highlighted_text = text

            for keyword in keywords:
                # Case-insensitive highlighting
                pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                highlighted_text = pattern.sub(
                    f"{pre_tag}\\g<0>{post_tag}",
                    highlighted_text
                )

            return highlighted_text

        except Exception as e:
            logger.error(f"Error highlighting text: {e}")
            return text

    async def clean_html(self, html_content: str) -> str:
        """Clean HTML content for indexing."""
        try:
            # Remove HTML tags but keep content
            clean_text = re.sub(r'<[^>]+>', ' ', html_content)

            # Remove extra whitespace
            clean_text = re.sub(r'\s+', ' ', clean_text)

            # Remove HTML entities
            clean_text = re.sub(r'&[a-zA-Z0-9]+;', ' ', clean_text)

            return clean_text.strip()

        except Exception as e:
            logger.error(f"Error cleaning HTML: {e}")
            return html_content

    async def normalize_korean(self, text: str) -> str:
        """Normalize Korean text for better search results."""
        try:
            # This is a placeholder for Korean text normalization
            # In a real implementation, you might use libraries like
            # soynlp or konlpy for advanced Korean text processing

            # Basic normalization
            normalized = text.strip()
            normalized = re.sub(r'\s+', ' ', normalized)

            return normalized

        except Exception as e:
            logger.error(f"Error normalizing Korean text: {e}")
            return text

    async def detect_language(self, text: str) -> str:
        """Detect language of text (simplified version)."""
        try:
            # Simple Korean detection based on character ranges
            korean_chars = len(re.findall(r'[가-힣]', text))
            total_chars = len(re.sub(r'\s', '', text))

            if total_chars == 0:
                return "unknown"

            korean_ratio = korean_chars / total_chars

            if korean_ratio > 0.3:
                return "ko"
            else:
                return "en"  # Default to English

        except Exception as e:
            logger.error(f"Error detecting language: {e}")
            return "unknown"


# Global instance
text_analyzer = TextAnalyzer()