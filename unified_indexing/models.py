"""
T036 Phase 4 - Pydantic Models
Data models for Unified RAG Knowledge Graph API
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class EntityType(str, Enum):
    """Entity types for knowledge graph."""
    PAPER = "paper"
    AUTHOR = "author"
    PERSON = "person"
    CONCEPT = "concept"
    PROJECT = "project"
    TASK = "task"
    NOTE = "note"
    ORGANIZATION = "organization"
    # Standard types
    COMPANY = "company"
    PRODUCT = "product"
    ROLE = "role"
    ALGORITHM = "algorithm"
    TECHNOLOGY = "technology"
    TOOL = "tool"
    LOCATION = "location"
    # Financial types
    STOCK = "STOCK"
    MONEY = "MONEY"
    PERCENTAGE = "PERCENTAGE"
    NUMBER = "NUMBER"
    DATE = "DATE"


class RelationshipType(str, Enum):
    """Relationship types for knowledge graph."""
    CITES = "cites"
    AUTHORED_BY = "authored_by"
    RELATED_TO = "related_to"
    BASED_ON = "based_on"
    ASSIGNED_TO = "assigned_to"
    CREATED_BY = "created_by"
    CONTAINS = "contains"
    EXTENDS = "extends"
    DEPENDS_ON = "depends_on"
    IMPLEMENTED_IN = "implemented_in"
    # Additional standard relations
    PART_OF = "part_of"
    USES = "uses"
    IMPLEMENTS = "implements"
    INFLUENCES = "influences"
    MEASURES = "measures"
    MENTIONS = "mentions"
    WORKS_AT = "works_at"
    # Entity-chunk relationship
    EXTRACTED_FROM = "extracted_from"
    # Financial relationship types
    TRADES_AT = "trades_at"
    HAS_MARKET_CAP = "has_market_cap"
    HAS_PRICE = "has_price"
    HAS_CHANGE = "has_change"
    HAS_VOLUME = "has_volume"
    REPORTS_ON = "reports_on"


class EntityBase(BaseModel):
    """Base entity model."""
    name: str = Field(..., min_length=1, max_length=500)
    entity_type: EntityType
    metadata: Optional[Dict[str, Any]] = None


class EntityCreate(EntityBase):
    """Model for creating an entity."""
    pass


class EntityUpdate(BaseModel):
    """Model for updating an entity."""
    name: Optional[str] = Field(None, min_length=1, max_length=500)
    entity_type: Optional[EntityType] = None
    metadata: Optional[Dict[str, Any]] = None


class EntityResponse(EntityBase):
    """Entity response model."""
    id: str
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class RelationshipBase(BaseModel):
    """Base relationship model."""
    source_entity_id: str = Field(..., min_length=1)
    target_entity_id: str = Field(..., min_length=1)
    relationship_type: RelationshipType
    confidence: float = Field(0.7, ge=0.0, le=1.0)
    metadata: Optional[Dict[str, Any]] = None


class RelationshipCreate(RelationshipBase):
    """Model for creating a relationship."""
    pass


class RelationshipResponse(RelationshipBase):
    """Relationship response model."""
    id: str
    created_at: datetime
    
    model_config = {"from_attributes": True}


class SearchQuery(BaseModel):
    """Search query model."""
    query: str = Field(..., min_length=1, max_length=1000)
    entity_types: Optional[List[EntityType]] = None
    limit: int = Field(10, ge=1, le=100)
    offset: int = Field(0, ge=0)


class SearchResponse(BaseModel):
    """Search response model."""
    results: List[Dict[str, Any]]
    total: int
    query: str


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    version: str
    database: str
    entities_count: int
    relationships_count: int
    timestamp: datetime


class ErrorResponse(BaseModel):
    """Error response model."""
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ==================== QUERY MODELS (Phase 5.4) ====================

class QueryRequest(BaseModel):
    """Knowledge graph query request model."""
    query: str = Field(..., min_length=1, max_length=2000, description="Natural language query")
    entity_types: Optional[List[EntityType]] = Field(None, description="Filter by entity types")
    max_depth: int = Field(2, ge=1, le=5, description="Graph traversal depth")
    limit: int = Field(20, ge=1, le=100, description="Maximum results")
    include_metadata: bool = Field(True, description="Include entity metadata")


class QueryResponse(BaseModel):
    """Knowledge graph query response model."""
    query_id: str
    query: str
    results: List[Dict[str, Any]]
    total_results: int
    graph_info: Optional[Dict[str, Any]] = None
    created_at: datetime


class QueryResult(BaseModel):
    """Individual query result model."""
    entity_id: str
    entity_name: str
    entity_type: str
    relevance_score: float
    path: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class EntityGraphResponse(BaseModel):
    """Entity subgraph response model."""
    entity_id: str
    entity_name: str
    entity_type: str
    neighbors: List[Dict[str, Any]]
    relationship_types: List[str]
    depth: int
    created_at: datetime
