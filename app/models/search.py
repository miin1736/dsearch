"""
Search Related Models
"""

from typing import List, Optional, Dict, Any
from pydantic import Field
from enum import Enum

from .base import BaseModel, PaginationParams


class SearchType(str, Enum):
    """Search type enumeration."""
    TEXT = "text"
    VECTOR = "vector"
    HYBRID = "hybrid"
    FUZZY = "fuzzy"


class SortOrder(str, Enum):
    """Sort order enumeration."""
    ASC = "asc"
    DESC = "desc"


class SearchQuery(BaseModel):
    """Search query parameters."""

    query: str = Field(..., description="Search query text")
    search_type: SearchType = Field(default=SearchType.TEXT, description="Type of search")
    fields: Optional[List[str]] = Field(default=None, description="Fields to search in")

    # Filters
    categories: Optional[List[str]] = Field(default=None, description="Category filters")
    date_from: Optional[str] = Field(default=None, description="Date range start")
    date_to: Optional[str] = Field(default=None, description="Date range end")
    file_types: Optional[List[str]] = Field(default=None, description="File type filters")

    # Search options
    highlight: bool = Field(default=True, description="Enable highlighting")
    typo_correction: bool = Field(default=True, description="Enable typo correction")
    auto_complete: bool = Field(default=False, description="Enable auto completion")
    fuzzy: bool = Field(default=False, description="Enable fuzzy search")

    # Sorting
    sort_field: Optional[str] = Field(default=None, description="Sort by field")
    sort_order: SortOrder = Field(default=SortOrder.DESC, description="Sort order")

    # Pagination
    page: int = Field(default=1, ge=1, description="Page number")
    size: int = Field(default=20, ge=1, le=100, description="Page size")

    # Vector search specific
    vector_threshold: Optional[float] = Field(default=0.7, description="Vector similarity threshold")

    @property
    def skip(self) -> int:
        return (self.page - 1) * self.size


class HighlightInfo(BaseModel):
    """Highlight information."""

    field: str
    fragments: List[str]


class DocumentModel(BaseModel):
    """Document model."""

    id: str
    title: str
    filename: str
    content: Optional[str] = None
    html_content: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None

    # Metadata
    category0: Optional[str] = None
    category1: Optional[str] = None
    category2: Optional[str] = None
    tags: Optional[List[str]] = None

    # Dates
    created_date: Optional[str] = None
    modified_date: Optional[str] = None
    indexed_date: Optional[str] = None

    # Search specific
    score: Optional[float] = None
    highlights: Optional[List[HighlightInfo]] = None

    # Vector embeddings
    vector: Optional[List[float]] = None


class FacetItem(BaseModel):
    """Facet aggregation item."""

    key: str
    count: int


class FacetAggregation(BaseModel):
    """Facet aggregation result."""

    name: str
    items: List[FacetItem]


class SearchResult(BaseModel):
    """Search result model."""

    # Query info
    query: str
    search_type: SearchType
    total_hits: int
    max_score: Optional[float] = None
    took_ms: int

    # Results
    documents: List[DocumentModel]

    # Aggregations
    facets: Optional[List[FacetAggregation]] = None

    # Suggestions
    suggestions: Optional[List[str]] = None
    typo_corrections: Optional[List[str]] = None
    auto_completions: Optional[List[str]] = None

    # Pagination
    page: int
    size: int
    total_pages: int


class VectorSearchQuery(BaseModel):
    """Vector search specific query."""

    query: str
    k: int = Field(default=10, description="Number of nearest neighbors")
    threshold: float = Field(default=0.7, description="Similarity threshold")
    include_metadata: bool = Field(default=True, description="Include document metadata")
    rerank: bool = Field(default=False, description="Re-rank results using text search")


class SimilarDocumentQuery(BaseModel):
    """Similar document search query."""

    document_id: str
    k: int = Field(default=10, description="Number of similar documents")
    threshold: float = Field(default=0.7, description="Similarity threshold")
    exclude_self: bool = Field(default=True, description="Exclude the input document")


class AutoCompleteQuery(BaseModel):
    """Auto-complete query."""

    prefix: str = Field(..., min_length=1, description="Text prefix for completion")
    size: int = Field(default=10, ge=1, le=50, description="Number of suggestions")
    field: Optional[str] = Field(default="title", description="Field to search for completions")


class AutoCompleteResult(BaseModel):
    """Auto-complete result."""

    suggestions: List[str]
    took_ms: int