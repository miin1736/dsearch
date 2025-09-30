"""
Text Highlighting Service
"""

import re
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger("ds")


class HighlightService:
    """Service for highlighting search terms in text and HTML content."""

    def __init__(self):
        # Default highlight styles
        self.search_pre_tag = "<span style='color: rgb(216, 90, 100)'>"
        self.search_post_tag = "</span>"

        self.view_pre_tag = "<span class='highlight' style='color: red'>"
        self.view_post_tag = "</span>"

        self.typo_pre_tag = "<span style='color: rgb(216, 90, 100)'>"
        self.typo_post_tag = "</span>"

        self.auto_pre_tag = "<span style='color: rgb(216, 90, 100)'>"
        self.auto_post_tag = "</span>"

    def highlight_search_results(self, text: str, keywords: List[str]) -> str:
        """Highlight keywords in search results."""
        return self._highlight_keywords(
            text, keywords,
            self.search_pre_tag,
            self.search_post_tag
        )

    def highlight_document_view(self, html_content: str, keywords: List[str]) -> str:
        """Highlight keywords in document viewer."""
        return self._highlight_keywords(
            html_content, keywords,
            self.view_pre_tag,
            self.view_post_tag
        )

    def highlight_typo_corrections(self, text: str, corrections: List[str]) -> str:
        """Highlight typo corrections."""
        return self._highlight_keywords(
            text, corrections,
            self.typo_pre_tag,
            self.typo_post_tag
        )

    def highlight_auto_completions(self, text: str, completions: List[str]) -> str:
        """Highlight auto-completion suggestions."""
        return self._highlight_keywords(
            text, completions,
            self.auto_pre_tag,
            self.auto_post_tag
        )

    def _highlight_keywords(self, text: str, keywords: List[str],
                           pre_tag: str, post_tag: str) -> str:
        """Generic keyword highlighting method."""
        if not text or not keywords:
            return text

        try:
            highlighted_text = text

            # Sort keywords by length (longest first) to avoid partial matches
            sorted_keywords = sorted(keywords, key=len, reverse=True)

            for keyword in sorted_keywords:
                if not keyword.strip():
                    continue

                # Escape special regex characters
                escaped_keyword = re.escape(keyword.strip())

                # Create case-insensitive pattern
                # Use word boundaries to avoid partial matches where appropriate
                if keyword.isalnum():
                    pattern = re.compile(f"\\b{escaped_keyword}\\b", re.IGNORECASE)
                else:
                    pattern = re.compile(escaped_keyword, re.IGNORECASE)

                # Replace with highlighted version
                highlighted_text = pattern.sub(
                    f"{pre_tag}\\g<0>{post_tag}",
                    highlighted_text
                )

            return highlighted_text

        except Exception as e:
            logger.error(f"Error highlighting keywords: {e}")
            return text

    def extract_highlights_from_elasticsearch(self, elasticsearch_highlight: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """Extract and process highlights from Elasticsearch response."""
        highlights = []

        try:
            for field, fragments in elasticsearch_highlight.items():
                if fragments:
                    highlights.append({
                        "field": field,
                        "fragments": fragments
                    })

            return highlights

        except Exception as e:
            logger.error(f"Error extracting Elasticsearch highlights: {e}")
            return []

    def create_text_fragments(self, text: str, keywords: List[str],
                            fragment_size: int = 150, max_fragments: int = 3) -> List[str]:
        """Create text fragments around keywords."""
        if not text or not keywords:
            return [text[:fragment_size]] if text else []

        try:
            fragments = []
            text_lower = text.lower()
            keyword_positions = []

            # Find all keyword positions
            for keyword in keywords:
                if not keyword.strip():
                    continue

                keyword_lower = keyword.lower()
                start = 0
                while True:
                    pos = text_lower.find(keyword_lower, start)
                    if pos == -1:
                        break
                    keyword_positions.append((pos, pos + len(keyword)))
                    start = pos + 1

            if not keyword_positions:
                # No keywords found, return beginning of text
                return [text[:fragment_size]]

            # Sort positions and merge overlapping ones
            keyword_positions.sort()
            merged_positions = []
            for start, end in keyword_positions:
                if merged_positions and start <= merged_positions[-1][1] + fragment_size // 4:
                    # Merge with previous position
                    merged_positions[-1] = (merged_positions[-1][0], max(merged_positions[-1][1], end))
                else:
                    merged_positions.append((start, end))

            # Create fragments around keyword positions
            for i, (kw_start, kw_end) in enumerate(merged_positions[:max_fragments]):
                # Calculate fragment boundaries
                fragment_start = max(0, kw_start - fragment_size // 2)
                fragment_end = min(len(text), kw_end + fragment_size // 2)

                # Adjust to word boundaries if possible
                if fragment_start > 0:
                    # Look for word boundary before fragment_start
                    for j in range(fragment_start, min(fragment_start + 20, len(text))):
                        if text[j].isspace():
                            fragment_start = j + 1
                            break

                if fragment_end < len(text):
                    # Look for word boundary after fragment_end
                    for j in range(fragment_end, max(fragment_end - 20, 0), -1):
                        if text[j].isspace():
                            fragment_end = j
                            break

                fragment = text[fragment_start:fragment_end].strip()
                if fragment:
                    # Add ellipsis if fragment doesn't start/end at text boundaries
                    if fragment_start > 0:
                        fragment = "..." + fragment
                    if fragment_end < len(text):
                        fragment = fragment + "..."

                    fragments.append(fragment)

            return fragments[:max_fragments]

        except Exception as e:
            logger.error(f"Error creating text fragments: {e}")
            return [text[:fragment_size]] if text else []

    def clean_highlight_tags(self, text: str) -> str:
        """Remove all highlight tags from text."""
        try:
            # Remove common highlight tags
            clean_text = text
            tags_to_remove = [
                self.search_pre_tag, self.search_post_tag,
                self.view_pre_tag, self.view_post_tag,
                self.typo_pre_tag, self.typo_post_tag,
                self.auto_pre_tag, self.auto_post_tag
            ]

            for tag in tags_to_remove:
                clean_text = clean_text.replace(tag, "")

            # Remove any remaining span tags with style attributes
            clean_text = re.sub(r"<span[^>]*>", "", clean_text)
            clean_text = re.sub(r"</span>", "", clean_text)

            return clean_text

        except Exception as e:
            logger.error(f"Error cleaning highlight tags: {e}")
            return text

    def convert_highlights_to_plain_text(self, highlighted_text: str) -> str:
        """Convert highlighted HTML to plain text with markers."""
        try:
            # Replace HTML highlight tags with simple markers
            text = highlighted_text
            text = re.sub(r"<span[^>]*>", "**", text)
            text = re.sub(r"</span>", "**", text)

            # Remove any other HTML tags
            text = re.sub(r"<[^>]+>", "", text)

            return text

        except Exception as e:
            logger.error(f"Error converting highlights to plain text: {e}")
            return highlighted_text


# Global instance
highlight_service = HighlightService()