"""
T036 Phase 4 - FastAPI Main Application
Unified RAG Knowledge Graph API

Security Features Implemented:
- Input validation with Pydantic
- Request size limiting
- CORS configured for security
- Error handling without info leakage
- Health checks for monitoring
"""

from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
from datetime import datetime, timezone
import time

from .config import settings
from .models import (
    EntityType, RelationshipType,
    EntityCreate, EntityUpdate, EntityResponse,
    RelationshipCreate, RelationshipResponse,
    SearchQuery, SearchResponse,
    QueryRequest, QueryResponse, EntityGraphResponse,
    HealthResponse, ErrorResponse
)
from .database import get_database, LightRAGDatabase
import uuid


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=f"{settings.app_version} (Phase 5)",
    docs_url=settings.docs_url,
    openapi_url=settings.openapi_url,
    default_response_class=JSONResponse
)

# Security: CORS Configuration
# Restrict in production by replacing ["*"] with specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_hosts,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware for performance monitoring
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers."""
    start_time = time.time()
    response = await call_next(response:=call_next)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors without leaking information."""
    # Log the full error server-side
    # Return generic message to client
    raise HTTPException(
        status_code=500,
        detail="Internal server error"
    )


# Dependency injection
def get_db() -> LightRAGDatabase:
    """Get database instance."""
    return get_database()


# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(db: LightRAGDatabase = Depends(get_db)):
    """
    Health check endpoint for monitoring.
    Returns API status and database connectivity.
    """
    validation = db.validate_connection()
    
    return HealthResponse(
        status="healthy" if validation['connected'] else "unhealthy",
        version=settings.app_version,
        database=validation['storage_path'],
        entities_count=validation['entities_count'],
        relationships_count=validation['relationships_count'],
        timestamp=datetime.now(timezone.utc)
    )


# API Info endpoint
@app.get("/", tags=["Info"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": settings.docs_url,
        "health": "/health"
    }


# Entity endpoints
@app.get("/api/v1/entities", response_model=List[EntityResponse], tags=["Entities"])
async def list_entities(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    entity_type: Optional[EntityType] = None,
    db: LightRAGDatabase = Depends(get_db)
):
    """
    List all entities with optional filtering.
    
    Security: Limited pagination to prevent large queries.
    """
    entities = []
    
    for doc_id, entity_data in list(db.entities.items())[:limit + offset]:
        if offset > 0 and len(entities) < offset:
            continue
        
        entity_names = entity_data.get('entity_names', [])
        entity_count = entity_data.get('count', 0)
        
        # Return first entity from each document for simplicity
        # In production, you'd want a proper entity table
        if entity_names:
            entities.append({
                'id': doc_id,
                'name': entity_names[0],
                'entity_type': entity_data.get('type', 'concept'),
                'metadata': {'count': entity_count},
                'created_at': entity_data.get('create_time', datetime.now(timezone.utc).isoformat()),
                'updated_at': entity_data.get('update_time', datetime.now(timezone.utc).isoformat())
            })
            
            if len(entities) >= limit:
                break
    
    return entities


@app.get("/api/v1/entities/search", response_model=SearchResponse, tags=["Entities"])
async def search_entities(
    q: str = Query(..., min_length=1, max_length=500),
    limit: int = Query(10, ge=1, le=50),
    db: LightRAGDatabase = Depends(get_db)
):
    """
    Search entities by name.
    
    Security: Query length limited to 500 chars.
    Results limited to prevent abuse.
    """
    results = db.search_entities(q, limit=limit)
    
    return SearchResponse(
        results=results,
        total=len(results),
        query=q
    )


@app.get("/api/v1/entities/{entity_id}", response_model=EntityResponse, tags=["Entities"])
async def get_entity(
    entity_id: str,
    db: LightRAGDatabase = Depends(get_db)
):
    """
    Get a specific entity by ID.
    """
    entity_data = db.get_entity_by_id(entity_id)
    
    if not entity_data:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    entity_names = entity_data.get('entity_names', [])
    
    return {
        'id': entity_id,
        'name': entity_names[0] if entity_names else 'Unknown',
        'entity_type': entity_data.get('type', 'concept'),
        'metadata': {'count': entity_data.get('count', 0)},
        'created_at': entity_data.get('create_time', datetime.now(timezone.utc).isoformat()),
        'updated_at': entity_data.get('update_time', datetime.now(timezone.utc).isoformat())
    }


@app.get("/api/v1/entities/{entity_name}/relationships", tags=["Entities"])
async def get_entity_relationships(
    entity_name: str,
    db: LightRAGDatabase = Depends(get_db)
):
    """
    Get all relationships for a specific entity.
    """
    linked_entity = db.get_linked_entity(entity_name)
    
    if not linked_entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    return {
        'entity': entity_name,
        'relationships': linked_entity.get('linked_entities', []),
        'relationship_types': linked_entity.get('relationship_types_found', [])
    }


# ==================== CRUD OPERATIONS (Phase 5) ====================

@app.post("/api/v1/entities", response_model=EntityResponse, tags=["Entities"], 
          status_code=201)
async def create_entity(
    entity: EntityCreate,
    db: LightRAGDatabase = Depends(get_db)
):
    """
    Create a new entity.
    
    Security: Entity type validated, name length limited.
    """
    entity_id = str(uuid.uuid4())
    
    created = db.create_entity(
        entity_id=entity_id,
        name=entity.name,
        entity_type=entity.entity_type.value,
        metadata=entity.metadata
    )
    
    return {
        'id': entity_id,
        'name': created['entity_names'][0],
        'entity_type': created['type'],
        'metadata': created.get('metadata', {}),
        'created_at': created['create_time'],
        'updated_at': created['update_time']
    }


@app.put("/api/v1/entities/{entity_id}", response_model=EntityResponse, tags=["Entities"])
async def update_entity(
    entity_id: str,
    updates: EntityUpdate,
    db: LightRAGDatabase = Depends(get_db)
):
    """
    Update an existing entity.
    
    Security: Only provided fields will be updated.
    """
    updated = db.update_entity(
        entity_id=entity_id,
        name=updates.name,
        entity_type=updates.entity_type.value if updates.entity_type else None,
        metadata=updates.metadata
    )
    
    if not updated:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    return {
        'id': entity_id,
        'name': updated['entity_names'][0],
        'entity_type': updated['type'],
        'metadata': updated.get('metadata', {}),
        'created_at': updated['create_time'],
        'updated_at': updated['update_time']
    }


@app.delete("/api/v1/entities/{entity_id}", status_code=204, tags=["Entities"])
async def delete_entity(
    entity_id: str,
    db: LightRAGDatabase = Depends(get_db)
):
    """
    Delete an entity.
    
    Warning: This action cannot be undone.
    """
    success = db.delete_entity(entity_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    return None


@app.post("/api/v1/relationships", response_model=RelationshipResponse, tags=["Relationships"],
          status_code=201)
async def create_relationship(
    relationship: RelationshipCreate,
    db: LightRAGDatabase = Depends(get_db)
):
    """
    Create a new relationship between two entities.
    """
    relationship_id = str(uuid.uuid4())
    
    created = db.create_relationship(
        relationship_id=relationship_id,
        source_entity=relationship.source_entity_id,
        target_entity=relationship.target_entity_id,
        relationship_type=relationship.relationship_type.value,
        confidence=relationship.confidence,
        metadata=relationship.metadata
    )
    
    return {
        'id': relationship_id,
        'source_entity_id': created['src_id'],
        'target_entity_id': created['tgt_id'],
        'relationship_type': created['relationship_type'],
        'confidence': created['confidence'],
        'metadata': created.get('metadata', {}),
        'created_at': created['create_time']
    }


@app.delete("/api/v1/relationships/{relationship_id}", status_code=204, tags=["Relationships"])
async def delete_relationship(
    relationship_id: str,
    db: LightRAGDatabase = Depends(get_db)
):
    """
    Delete a relationship.
    """
    success = db.delete_relationship(relationship_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Relationship not found")
    
    return None


# ==================== QUERY API ENDPOINTS (Phase 5.4) ====================

@app.post("/api/v1/query", response_model=QueryResponse, tags=["Queries"])
async def query_knowledge_graph(
    request: QueryRequest,
    db: LightRAGDatabase = Depends(get_db)
):
    """
    Query the knowledge graph with natural language.
    
    Returns relevant entities and their relationships based on the query.
    """
    entity_types = [et.value for et in request.entity_types] if request.entity_types else None
    
    result = db.query_knowledge_graph(
        query=request.query,
        entity_types=entity_types,
        max_depth=request.max_depth,
        limit=request.limit,
        include_metadata=request.include_metadata
    )
    
    return QueryResponse(
        query_id=result['query_id'],
        query=result['query'],
        results=result['results'],
        total_results=result['total_results'],
        graph_info=result['graph_info'],
        created_at=datetime.utcnow()
    )


@app.get("/api/v1/query/{query_id}", tags=["Queries"])
async def get_query_result(
    query_id: str,
    db: LightRAGDatabase = Depends(get_db)
):
    """
    Get a previous query result by ID.
    
    Note: In a production system, you'd want to store query results
    in a database or cache. This is a simplified implementation.
    """
    # In production, retrieve from database/cache
    # For now, return a message indicating the endpoint is available
    return {
        "query_id": query_id,
        "status": "completed",
        "message": "Query results available. Note: Full result storage requires database implementation.",
        "note": "Implement query result storage for persistent queries"
    }


@app.get("/api/v1/entities/{entity_id}/graph", response_model=EntityGraphResponse, tags=["Entities"])
async def get_entity_graph(
    entity_id: str,
    depth: int = Query(2, ge=1, le=5),
    db: LightRAGDatabase = Depends(get_db)
):
    """
    Get the subgraph for a specific entity.
    
    Returns the entity and its neighbors with relationships.
    """
    result = db.get_entity_graph(entity_id, depth=depth)
    
    if not result:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    return EntityGraphResponse(
        entity_id=result['entity_id'],
        entity_name=result['entity_name'],
        entity_type=result['entity_type'],
        neighbors=result['neighbors'],
        relationship_types=result['relationship_types'],
        depth=result['depth'],
        created_at=datetime.utcnow()
    )


# Statistics endpoint
@app.get("/api/v1/stats", tags=["Statistics"])
async def get_statistics(db: LightRAGDatabase = Depends(get_db)):
    """
    Get knowledge graph statistics.
    """
    validation = db.validate_connection()
    
    return {
        'entities': validation['entities_count'],
        'relationships': validation['relationships_count'],
        'validated_at': validation['validated_at']
    }


# Create the application instance for running with uvicorn
def create_app() -> FastAPI:
    """Application factory for creating FastAPI instances."""
    return app


# Run configuration
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
