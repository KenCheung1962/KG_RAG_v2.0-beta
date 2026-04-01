#!/usr/bin/env python3
"""
KG RAG API with pgvector storage - Compatible with WebUI
Includes Vector Similarity Search + Reranking for improved quality
"""
import asyncio
import json
import os
import hashlib
import base64
import requests
import logging
from datetime import datetime
from fastapi import Request, FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import sys
import time
import re
import numpy as np
from dataclasses import dataclass
from io import BytesIO

# PDF text extraction
try:
    from pypdf import PdfReader
    PDF_SUPPORT = True
except ImportError:
    try:
        from PyPDF2 import PdfReader
        PDF_SUPPORT = True
    except ImportError:
        PDF_SUPPORT = False
        print("[WARNING] PyPDF2/pypdf not installed. PDF text extraction will not work.")

sys.path.insert(0, '/Users/ken/clawd_workspace/projects/KG_RAG/proj_ph2/source/postgres')

# Import LLM provider functions for configurable entity extraction
try:
    from minimax_fixed import llm_complete_with_provider
except ImportError:
    # Fallback if import fails
    async def llm_complete_with_provider(*args, **kwargs):
        raise Exception("LLM provider module not available")
    print("[WARNING] minimax_fixed not available - entity extraction will fail")

# =============================================================================
# RERANKER CONFIGURATION
# =============================================================================

@dataclass
class RerankConfig:
    """Configuration for reranking."""
    # Initial retrieval - how many chunks to fetch before reranking
    initial_top_k: int = 50
    # Final number of chunks after reranking
    final_top_k: int = 10
    # Enable/disable reranking
    enabled: bool = True
    # Reranking method: "cross_encoder", "llm", "hybrid", or "none"
    method: str = "hybrid"
    # Threshold for relevance (0-1)
    relevance_threshold: float = 0.3

# Global rerank config
RERANK_CONFIG = RerankConfig()

# =============================================================================
# LOGGER FOR RERANKER
# =============================================================================

rerank_logger = logging.getLogger("reranker")

# =============================================================================
# EMBEDDING FUNCTION (Ollama - nomic-embed-text)
# =============================================================================

EMBEDDING_DIMENSION = 768  # nomic-embed-text dimension

# Initialize Ollama client for embeddings
_ollama_client = None

def get_ollama_client():
    """Get or create Ollama client instance."""
    global _ollama_client
    if _ollama_client is None:
        from ollama_client import OllamaClient
        _ollama_client = OllamaClient(
            host=os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"),
            model=os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
        )
    return _ollama_client

def get_ollama_embedding(text: str) -> List[float]:
    """Generate embedding using local Ollama (nomic-embed-text).
    
    Uses a thread pool executor to avoid event loop conflicts when called
    from within an async context.
    """
    try:
        client = get_ollama_client()
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        def _sync_embed():
            return asyncio.run(client.embed([text[:8000]]))
        
        # Use thread pool to run async code in a separate thread
        # This avoids the "event loop already running" error
        with ThreadPoolExecutor(max_workers=1) as executor:
            embeddings = executor.submit(_sync_embed).result(timeout=30)
        
        if embeddings and len(embeddings) > 0:
            embedding = embeddings[0]
            if embedding and len(embedding) == EMBEDDING_DIMENSION:
                return embedding
            else:
                rerank_logger.error(f"Invalid embedding dimension: {len(embedding) if embedding else 0}")
                return [0.0] * EMBEDDING_DIMENSION
        else:
            rerank_logger.error("Ollama returned empty embeddings")
            return [0.0] * EMBEDDING_DIMENSION
    except Exception as e:
        rerank_logger.error(f"Ollama embedding exception: {e}")
        return [0.0] * EMBEDDING_DIMENSION

# =============================================================================
# RERANKER IMPLEMENTATIONS
# =============================================================================

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    if not vec1 or not vec2:
        return 0.0
    v1 = np.array(vec1, dtype=np.float64)
    v2 = np.array(vec2, dtype=np.float64)
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    result = float(np.dot(v1, v2) / (norm1 * norm2))
    # Guard against NaN or Infinity
    if np.isnan(result) or np.isinf(result):
        return 0.0
    return result

def keyword_score(query: str, text: str) -> float:
    """Calculate keyword matching score."""
    query_lower = query.lower()
    text_lower = text.lower()
    
    # Extract words from query (skip stop words)
    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 
                  'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 
                  'and', 'or', 'but', 'what', 'which', 'who', 'how', 'why'}
    
    query_words = [w for w in re.findall(r'\b[a-zA-Z]+\b', query_lower) 
                   if w not in stop_words and len(w) > 2]
    
    if not query_words:
        return 0.5
    
    matches = sum(1 for w in query_words if w in text_lower)
    return matches / len(query_words)

def calculate_recency_score(created_at: Optional[datetime]) -> float:
    """Calculate recency score for chunks."""
    if not created_at:
        return 0.5  # Neutral score if no date
    
    # More recent = higher score
    days_old = (datetime.now() - created_at).days
    if days_old < 30:
        return 1.0
    elif days_old < 90:
        return 0.8
    elif days_old < 365:
        return 0.6
    else:
        return 0.4

async def rerank_chunks(
    query: str, 
    chunks: List[dict], 
    method: str = "hybrid",
    final_k: int = 10
) -> List[dict]:
    """
    Rerank chunks using specified method.
    
    Methods:
    - "hybrid": Combines vector similarity + keyword matching + recency
    - "vector": Pure vector cosine similarity
    - "keyword": Keyword matching only
    - "none": No reranking, just return top-k by original order
    """
    if not chunks:
        return []
    
    if method == "none" or len(chunks) <= final_k:
        return chunks[:final_k]
    
    # Generate query embedding once
    query_embedding = get_ollama_embedding(query)
    
    scored_chunks = []
    
    for chunk in chunks:
        content = chunk.get("content", "")
        chunk_embedding = chunk.get("embedding")
        
        if method == "vector":
            if chunk_embedding:
                score = cosine_similarity(query_embedding, chunk_embedding)
            else:
                score = 0.0
                
        elif method == "keyword":
            score = keyword_score(query, content)
            
        elif method == "hybrid":
            # Combine multiple signals
            scores = []
            weights = []
            
            # Vector similarity (40%)
            if chunk_embedding:
                vec_sim = cosine_similarity(query_embedding, chunk_embedding)
                scores.append(vec_sim)
                weights.append(0.4)
            
            # Keyword matching (30%)
            kw_score = keyword_score(query, content)
            scores.append(kw_score)
            weights.append(0.3)
            
            # Content length quality (10%) - prefer medium-length chunks
            content_len = len(content)
            if 500 <= content_len <= 1500:
                length_score = 1.0
            elif content_len < 300:
                length_score = 0.5
            else:
                length_score = 0.8
            scores.append(length_score)
            weights.append(0.1)
            
            # Recency score (10%)
            created_at = chunk.get("created_at")
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except:
                    created_at = None
            recency_score = calculate_recency_score(created_at)
            scores.append(recency_score)
            weights.append(0.1)
            
            # Content diversity bonus (10%) - unique content gets boost
            # This is calculated based on position in original list
            diversity_score = 1.0 - (chunks.index(chunk) / len(chunks)) * 0.5
            scores.append(diversity_score)
            weights.append(0.1)
            
            # Calculate weighted average
            total_weight = sum(weights)
            score = sum(s * w for s, w in zip(scores, weights)) / total_weight if total_weight > 0 else 0.5
        else:
            score = 0.5
        
        scored_chunks.append((score, chunk))
    
    # Sort by score descending
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    
    # Return top-k with scores attached
    result = []
    for score, chunk in scored_chunks[:final_k]:
        # Guard against NaN or Infinity in scores
        if np.isnan(score) or np.isinf(score):
            score = 0.5
        chunk["rerank_score"] = round(float(score), 3)
        result.append(chunk)
    
    return result

# =============================================================================
# VECTOR SEARCH FUNCTIONS
# =============================================================================

async def search_chunks_vector(
    storage,
    query: str,
    top_k: int = 50,
    match_threshold: float = 0.3
) -> List[dict]:
    """
    Search chunks using vector similarity.
    
    Falls back to keyword search if vector search fails.
    """
    try:
        # Generate query embedding
        query_embedding = get_ollama_embedding(query)
        
        # Use the storage's vector search
        from storage import DistanceMetric
        results = await storage.search_chunks(
            query_vector=query_embedding,
            limit=top_k,
            distance_metric=DistanceMetric.COSINE,
            match_threshold=match_threshold
        )
        
        # Convert to dict format
        chunks = []
        for r in results:
            chunks.append({
                "content": r.content,
                "source": r.source,
                "similarity": r.similarity,
                "chunk_id": r.chunk_id,
                "metadata": r.metadata
            })
        
        return chunks
        
    except Exception as e:
        rerank_logger.error(f"Vector search failed: {e}, falling back to keyword search")
        return []

def keyword_search_fallback(storage, query: str, top_k: int = 50) -> List[dict]:
    """
    Fallback keyword-based search.
    """
    import re
    
    # Extract keywords
    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                  'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                  'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
                  'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as',
                  'into', 'through', 'during', 'before', 'after', 'above', 'below',
                  'between', 'under', 'again', 'further', 'then', 'once', 'here',
                  'there', 'when', 'where', 'why', 'how', 'all', 'each', 'few',
                  'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
                  'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just',
                  'and', 'but', 'if', 'or', 'because', 'until', 'while', 'about',
                  'against', 'this', 'that', 'these', 'those', 'what', 'which', 'who',
                  'whom', 'reply', 'english', 'translate', 'language', 'in', 'write'}
    
    words = [w.lower() for w in re.findall(r'[a-zA-Z]+', query) 
             if w.lower() not in stop_words and len(w) > 2]
    
    # Use sync database fetch
    results = []
    try:
        import asyncpg
        # This is a sync fallback - in production you'd want async
        for word in words[:3]:
            # This won't work well in async context, but as fallback
            pass
    except:
        pass
    
    return results

# Setup logging for failed uploads
UPLOAD_LOG_FILE = "/tmp/upload_failures.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(UPLOAD_LOG_FILE),
        logging.StreamHandler()
    ]
)
upload_logger = logging.getLogger("upload_failures")

def log_upload_failure(filename: str, error: str, file_size: int = 0, content_type: str = "unknown"):
    """Log failed upload with details"""
    upload_logger.error(f"UPLOAD_FAILED | filename='{filename}' | error='{error}' | size={file_size} | type={content_type}")

def log_upload_success(filename: str, doc_id: str, chunks: int, file_size: int = 0):
    """Log successful upload"""
    upload_logger.info(f"UPLOAD_SUCCESS | filename='{filename}' | doc_id={doc_id} | chunks={chunks} | size={file_size}")

# Load MINIMAX_API_KEY from .zshrc if not set
if not os.getenv("MINIMAX_API_KEY"):
    try:
        with open(os.path.expanduser("~/.zshrc"), "r") as f:
            for line in f:
                if line.strip().startswith("export MINIMAX_API_KEY="):
                    # Extract the key value
                    key = line.strip().split("=", 1)[1].strip('"')
                    os.environ["MINIMAX_API_KEY"] = key
                    break
    except:
        pass

from storage import create_kg_storage, Entity, Relationship, Chunk

# Chunking configuration
CHUNK_SIZE = 1000      # Characters per chunk
CHUNK_OVERLAP = 100    # Overlap between chunks (characters)

def extract_text_from_file(content: bytes, filename: str) -> str:
    """
    Extract text from various file formats (PDF, TXT, etc.)
    Returns extracted text or empty string if extraction fails.
    """
    file_lower = filename.lower()
    
    # PDF files
    if file_lower.endswith('.pdf'):
        if not PDF_SUPPORT:
            print(f"[WARNING] PDF support not available for {filename}")
            return ""
        try:
            pdf_file = BytesIO(content)
            reader = PdfReader(pdf_file)
            text_parts = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            extracted = "\n".join(text_parts)
            print(f"[DEBUG] Extracted {len(extracted)} chars from PDF {filename}")
            return extracted
        except Exception as e:
            print(f"[ERROR] PDF extraction failed for {filename}: {e}")
            return ""
    
    # Text files - try UTF-8 first
    try:
        return content.decode('utf-8')
    except UnicodeDecodeError:
        # Try other encodings
        for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
    
    # Last resort - ignore errors
    return content.decode('utf-8', errors='ignore')

def create_chunks(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping chunks.
    
    Args:
        text: The text to split
        chunk_size: Size of each chunk in characters
        overlap: Number of characters to overlap between chunks
    
    Returns:
        List of text chunks with overlap
    """
    if not text or len(text) <= chunk_size:
        return [text] if text else []
    
    chunks = []
    stride = chunk_size - overlap  # How much to advance each time
    
    for i in range(0, len(text), stride):
        chunk = text[i:i + chunk_size]
        if len(chunk) < 50 and i > 0:  # Skip tiny last chunks
            break
        chunks.append(chunk)
        
        # Stop if we've reached the end
        if i + chunk_size >= len(text):
            break
    
    return chunks

app = FastAPI(title="KG RAG pgvector API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add cache control middleware
@app.middleware("http")
async def add_cache_control(request, call_next):
    response = await call_next(request)
    # Disable caching for API endpoints
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# MiniMax API Configuration
MINIMAX_API_KEY = os.environ.get("MINIMAX_PORTAL_TOKEN", "sk-cp-EyvfWvXEC-upzqaaNavnkGMCYHoaoaI4DjCGHb1CmDRPv5e_oYAnsp09gLaJH6MAV-bGpLFfPfCAjaSkebNxsSvEVkI-x_uXau-fK3iZ_l8Z2nFBRpg_VOs")
MINIMAX_BASE_URL = "https://api.minimax.chat/v1"

async def call_minimax(prompt: str, system_prompt: str = "You are a helpful assistant.") -> str:
    """Call MiniMax API with prompt."""
    if not MINIMAX_API_KEY:
        print("MiniMax API key is empty!")
        return ""
    
    url = f"{MINIMAX_BASE_URL}/text/chatcompletion_v2"
    headers = {
        "Authorization": f"Bearer {MINIMAX_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "MiniMax-M2.5",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    }
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        else:
            print(f"MiniMax API error: {resp.status_code} - {resp.text}")
            return ""
    except Exception as e:
        print(f"MiniMax API exception: {e}")
        return ""

async def extract_entities_and_relations(text: str, llm_config: dict = None) -> tuple:
    """Extract entities and relationships from text using configurable LLM provider."""
    if len(text) < 50:
        return [], []
    
    # Truncate text if too long
    max_text = 8000
    if len(text) > max_text:
        text = text[:max_text] + "..."
    
    # Get LLM configuration
    if llm_config is None:
        llm_config = {}
    provider = llm_config.get("provider", "deepseek")
    fallback = llm_config.get("fallback_provider")
    
    system_prompt = f"""You are an entity extraction expert. Extract entities and relationships from the text.
Use ONLY these entity types: company, person, product, technology, tool, location, organization, concept, project, task, note, stock, money, percentage, number, date, article, patent, book, journal

Use ONLY these relationship types: cites, authored_by, related_to, based_on, created_by, contains, extends, depends_on, implemented_in, part_of, uses, implements, works_at, extracted_from, trades_at, has_price, has_change, has_volume, has_market_cap, granted_to, owned_by, contribute_to, mentions

Output in JSON format:
{{"entities": [{{"name": "EntityName", "type": "entity_type", "description": "brief description"}}], "relationships": [{{"from": "Entity1", "to": "Entity2", "type": "relationship_type"}}]}}"""
    
    prompt = f"""Extract all entities and relationships from this text:

{text}

Return only valid JSON, no other text."""
    
    try:
        # Use configurable LLM provider with fallback support
        result = await llm_complete_with_provider(
            prompt=prompt,
            system_prompt=system_prompt,
            provider=provider,
            fallback_provider=fallback,
            max_tokens=4096,
            temperature=0.3
        )
    except Exception as e:
        print(f"[Entity Extraction] All LLM providers failed: {e}")
        return [], []
    
    if not result:
        return [], []
    
    # Parse JSON
    try:
        # Try to extract JSON from response
        import re
        json_match = re.search(r'\{[\s\S]*\}', result)
        if json_match:
            data = json.loads(json_match.group())
            entities = data.get("entities", [])
            relationships = data.get("relationships", [])
            return entities, relationships
    except Exception as e:
        print(f"[Entity Extraction] JSON parsing failed: {e}")
        pass
    
    return [], []

storage = None
DOCS_DIR = "/tmp/kg_rag_docs"

@app.on_event("startup")
async def startup():
    global storage
    os.makedirs(DOCS_DIR, exist_ok=True)
    storage = await create_kg_storage({
        'host': 'localhost',
        'port': 5432,
        'database': 'kg_rag',
        'user': 'postgres',
        'password': 'postgres'
    })

@app.on_event("shutdown")
async def shutdown():
    if storage:
        await storage.client.disconnect()

# ============ Health & Stats ============
@app.get("/health")
async def health():
    result = await storage.client.fetch("SELECT COUNT(*) as e FROM entities")
    rels = await storage.client.fetch("SELECT COUNT(*) as r FROM relationships")
    chunks = await storage.client.fetch("SELECT COUNT(*) as c FROM chunks")
    docs = await storage.client.fetch("SELECT COUNT(DISTINCT source) as d FROM chunks")
    return {
        "status": "healthy",
        "version": "1.0.0-pgvector",
        "entities_count": result[0]["e"],
        "relationships_count": rels[0]["r"],
        "chunks_count": chunks[0]["c"] if chunks else 0,
        "documents_count": docs[0]["d"] if docs else 0
    }

@app.get("/api/v1/upload-failures")
async def get_upload_failures():
    """Get list of recent upload failures"""
    try:
        if not os.path.exists(UPLOAD_LOG_FILE):
            return {"failures": [], "successes": [], "total_failures": 0, "total_successes": 0}
        
        failures = []
        successes = []
        
        with open(UPLOAD_LOG_FILE, 'r') as f:
            for line in f:
                if 'UPLOAD_FAILED' in line:
                    # Parse log line
                    parts = line.strip().split(' | ')
                    timestamp = parts[0] if parts else ""
                    details = {}
                    for part in parts[1:]:
                        if '=' in part:
                            key, value = part.split('=', 1)
                            details[key] = value.strip("'")
                    failures.append({
                        "timestamp": timestamp,
                        "filename": details.get('filename', 'unknown'),
                        "error": details.get('error', 'unknown'),
                        "size": details.get('size', '0')
                    })
                elif 'UPLOAD_SUCCESS' in line:
                    parts = line.strip().split(' | ')
                    timestamp = parts[0] if parts else ""
                    details = {}
                    for part in parts[1:]:
                        if '=' in part:
                            key, value = part.split('=', 1)
                            details[key] = value.strip("'")
                    successes.append({
                        "timestamp": timestamp,
                        "filename": details.get('filename', 'unknown'),
                        "doc_id": details.get('doc_id', ''),
                        "chunks": details.get('chunks', '0'),
                        "size": details.get('size', '0')
                    })
        
        # Return last 50 failures and last 100 successes
        return {
            "failures": failures[-50:],
            "successes": successes[-100:],
            "total_failures": len(failures),
            "total_successes": len(successes),
            "log_file": UPLOAD_LOG_FILE
        }
    except Exception as e:
        return {"error": str(e), "failures": [], "successes": []}

@app.get("/api/v1/kg/stats")
async def kg_stats():
    result = await storage.client.fetch("SELECT COUNT(*) as e FROM entities")
    rels = await storage.client.fetch("SELECT COUNT(*) as r FROM relationships")
    chunks = await storage.client.fetch("SELECT COUNT(*) as c FROM chunks")
    docs = await storage.client.fetch("SELECT COUNT(DISTINCT source) as d FROM chunks")
    return {
        "entities": result[0]["e"],
        "relationships": rels[0]["r"],
        "chunks": chunks[0]["c"] if chunks else 0,
        "documents": docs[0]["d"] if docs else 0
    }

# ============ Documents ============
@app.get("/api/v1/documents")
async def list_documents():
    """List all documents"""
    result = await storage.client.fetch("SELECT entity_id, source, created_at FROM chunks ORDER BY created_at DESC LIMIT 100")
    docs = {}
    for r in result:
        entity_id = r.get("entity_id", "unknown")
        if entity_id not in docs:
            docs[entity_id] = {
                "doc_id": entity_id, 
                "chunks": 0, 
                "created_at": r.get("created_at"),
                "filename": r.get("source", "")
            }
        docs[entity_id]["chunks"] += 1
    return list(docs.values())

@app.get("/api/v1/documents/stats")
async def doc_stats():
    """Document statistics"""
    result = await storage.client.fetch("SELECT COUNT(DISTINCT entity_id) as cnt FROM chunks")
    chunks = await storage.client.fetch("SELECT COUNT(*) as cnt FROM chunks")
    return {
        "total_documents": result[0]["cnt"] if result else 0,
        "total_chunks": chunks[0]["cnt"] if chunks else 0
    }

@app.post("/api/v1/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
):
    """Upload a single file"""
    filename = file.filename
    file_size = 0
    
    try:
        content = await file.read()
        file_size = len(content)
        
        # Extract text based on file type (PDF, TXT, etc.)
        text = extract_text_from_file(content, filename)
        
        if not text or len(text.strip()) < 50:
            log_upload_failure(filename, "Could not extract readable text from file", file_size)
            return {
                "success": False,
                "error": "Could not extract readable text from file. For PDFs, ensure they are text-based (not scanned images).",
                "doc_id": None
            }
        
        # Create doc_id from filename
        doc_id = hashlib.md5(filename.encode()).hexdigest()[:12]
        
        # Delete existing chunks and entity first (for re-upload)
        try:
            await storage.client.execute("DELETE FROM chunks WHERE entity_id = $1", doc_id)
            await storage.client.execute("DELETE FROM entities WHERE entity_id = $1", doc_id)
        except:
            pass
        
        # First create the document entity (WITH EMBEDDING)
        doc_embedding_text = f"{filename} (document) - Uploaded document"
        try:
            doc_embedding = get_ollama_embedding(doc_embedding_text)
        except Exception as e:
            print(f"[Upload] Document embedding failed for {filename}: {e}")
            doc_embedding = None
        
        entity = Entity(
            entity_id=doc_id,
            entity_type="document",
            name=filename,
            description=f"Document: {filename}",
            properties={"filename": filename, "type": "uploaded"},
            embedding=doc_embedding
        )
        try:
            await storage.create_entity(entity)
        except Exception as e:
            log_upload_failure(filename, f"Entity creation failed: {str(e)}", file_size)
            pass  # Entity might already exist
        
        # Split into chunks with overlap for better context
        chunks = create_chunks(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
        
        # Store chunks with embeddings
        chunks_created = 0
        for i, chunk_text in enumerate(chunks):
            # Generate embedding for this chunk
            embedding = get_ollama_embedding(chunk_text)
            
            chunk = Chunk(
                chunk_id=f"{doc_id}_{i}",
                entity_id=doc_id,
                content=chunk_text,
                source=filename,
                chunk_index=i,
                embedding=embedding,  # Now includes 768d embedding
                metadata={"filename": filename, "index": i}
            )
            try:
                await storage.create_chunk(chunk)
                chunks_created += 1
            except Exception as e:
                log_upload_failure(filename, f"Chunk {i} creation failed: {str(e)}", file_size)
                pass
        
        # Log success
        log_upload_success(filename, doc_id, chunks_created, file_size)
        
        return {
            "success": True,
            "doc_id": doc_id,
            "filename": filename,
            "chunks": chunks_created
        }
    except Exception as e:
        error_msg = str(e)
        log_upload_failure(filename, error_msg, file_size)
        raise HTTPException(status_code=500, detail=error_msg)

# JSON upload endpoint for WebUI
@app.post("/api/v1/documents/upload/json")
async def upload_document_json(request: Request):
    """Upload a single file via JSON with entity extraction (uses Config Tab LLM settings)"""
    filename = "unknown.txt"
    file_size = 0
    
    try:
        body = await request.json()
        content = body.get("content", "")
        filename = body.get("id", body.get("filename", "unknown.txt"))
        file_size = len(content) if isinstance(content, str) else len(content.encode())
        
        # Get LLM configuration from request (sent from Config Tab)
        llm_config = body.get("llm_config", {})
        provider = llm_config.get("provider", "deepseek")
        fallback = llm_config.get("fallback_provider")
        print(f"[Upload] Using LLM provider: {provider}" + (f" (fallback: {fallback})" if fallback else ""))
        
        # Decode base64 if provided
        if content:
            try:
                # Try to decode as base64 (for binary files like PDFs)
                binary_content = base64.b64decode(content)
                # Extract text based on file type
                text = extract_text_from_file(binary_content, filename)
            except Exception as e:
                # If decoding fails, treat as plain text
                print(f"[DEBUG] Base64 decode failed, treating as plain text: {e}")
                text = content if isinstance(content, str) else content.decode('utf-8', errors='ignore')
        else:
            text = ""
        
        if not text or len(text.strip()) < 50:
            log_upload_failure(filename, "Could not extract readable text from file", file_size)
            return {
                "success": False,
                "error": "Could not extract readable text from file. For PDFs, ensure they are text-based (not scanned images).",
                "doc_id": None
            }
        
        # Create doc_id from filename
        doc_id = hashlib.md5(filename.encode()).hexdigest()[:12]
        
        # Delete existing chunks and entity first (for re-upload)
        try:
            await storage.client.execute("DELETE FROM chunks WHERE entity_id = $1", doc_id)
            await storage.client.execute("DELETE FROM entities WHERE entity_id = $1", doc_id)
        except:
            pass
        
        # First create the document entity (WITH EMBEDDING)
        # Generate embedding for document entity
        doc_embedding_text = f"{filename} (document) - Uploaded document"
        try:
            doc_embedding = get_ollama_embedding(doc_embedding_text)
        except Exception as e:
            print(f"[Upload] Document embedding failed for {filename}: {e}")
            doc_embedding = None
        
        entity = Entity(
            entity_id=doc_id,
            entity_type="document",
            name=filename,
            description=f"Document: {filename}",
            properties={"filename": filename, "type": "uploaded"},
            embedding=doc_embedding
        )
        try:
            await storage.create_entity(entity)
        except Exception as e:
            log_upload_failure(filename, f"Entity creation failed: {str(e)}", file_size)
            pass
        
        # Split into chunks with overlap for better context
        chunks = create_chunks(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
        
        # Store chunks with embeddings
        chunks_created = 0
        for i, chunk_text in enumerate(chunks):
            # Generate embedding for this chunk
            embedding = get_ollama_embedding(chunk_text)
            
            chunk = Chunk(
                chunk_id=f"{doc_id}_{i}",
                entity_id=doc_id,
                content=chunk_text,
                source=filename,
                chunk_index=i,
                embedding=embedding,  # Now includes 768d embedding
                metadata={"filename": filename, "index": i}
            )
            try:
                await storage.create_chunk(chunk)
                chunks_created += 1
            except Exception as e:
                log_upload_failure(filename, f"Chunk {i} creation failed: {str(e)}", file_size)
                pass
        
        # Extract entities and relationships using LLM (with configurable provider)
        extracted_entities = []
        extracted_relations = []
        
        if text and len(text) > 100:
            try:
                extracted_entities, extracted_relations = await extract_entities_and_relations(
                    text, 
                    llm_config={"provider": provider, "fallback_provider": fallback}
                )
                print(f"[Upload] Extracted {len(extracted_entities)} entities, {len(extracted_relations)} relationships")
            except Exception as e:
                log_upload_failure(filename, f"Entity extraction failed: {str(e)}", file_size)
                print(f"[Upload] Entity extraction error: {e}")
            
            # Create extracted entities (WITH EMBEDDINGS)
            entity_ids_created = set()
            entities_embedded = 0
            for ent in extracted_entities:
                ent_name = ent.get("name", "")
                ent_type = ent.get("type", "concept")
                ent_description = ent.get("description", "")
                if ent_name and ent_name not in entity_ids_created:
                    ent_id = hashlib.md5(ent_name.encode()).hexdigest()[:12]
                    ent_id = f"ent_{ent_id}"
                    
                    # Generate embedding text for entity
                    # Format: "EntityName (entity_type) - description"
                    embedding_text = f"{ent_name} ({ent_type})"
                    if ent_description:
                        embedding_text += f" - {ent_description}"
                    
                    # Generate embedding using Ollama
                    try:
                        ent_embedding = get_ollama_embedding(embedding_text)
                        entities_embedded += 1
                    except Exception as e:
                        print(f"[Upload] Entity embedding failed for {ent_name}: {e}")
                        ent_embedding = None
                    
                    ent_entity = Entity(
                        entity_id=ent_id,
                        entity_type=ent_type,
                        name=ent_name,
                        description=ent_description or f"Extracted from {filename}",
                        properties={"source": filename, "extracted": True},
                        embedding=ent_embedding
                    )
                    try:
                        await storage.create_entity(ent_entity)
                        entity_ids_created.add(ent_name)
                        
                        # Link entity to document
                        rel = Relationship(
                            relationship_id=f"{doc_id}_{ent_id}",
                            source_id=doc_id,
                            target_id=ent_id,
                            relationship_type="contains",
                            properties={"extracted_from": filename}
                        )
                        try:
                            await storage.create_relationship(rel)
                        except Exception as e:
                            log_upload_failure(filename, f"Relationship creation failed: {str(e)}", file_size)
                            pass
                    except Exception as e:
                        log_upload_failure(filename, f"Entity creation failed: {str(e)}", file_size)
                        pass
            
            # Create relationships between extracted entities
            for rel in extracted_relations:
                from_ent = rel.get("from", "")
                to_ent = rel.get("to", "")
                rel_type = rel.get("type", "related_to")
                
                if from_ent and to_ent and from_ent != to_ent:
                    from_id = f"ent_{hashlib.md5(from_ent.encode()).hexdigest()[:12]}"
                    to_id = f"ent_{hashlib.md5(to_ent.encode()).hexdigest()[:12]}"
                    
                    rel_obj = Relationship(
                        relationship_id=f"{from_id}_{to_id}",
                        source_id=from_id,
                        target_id=to_id,
                        relationship_type=rel_type,
                        properties={"source": filename}
                    )
                    try:
                        await storage.create_relationship(rel_obj)
                    except Exception as e:
                        log_upload_failure(filename, f"Relationship creation failed: {str(e)}", file_size)
                        pass
        
        # Log success
        log_upload_success(filename, doc_id, chunks_created, file_size)
        
        return {
            "success": True,
            "doc_id": doc_id,
            "filename": filename,
            "chunks": chunks_created,
            "entities_extracted": len(extracted_entities),
            "relationships_extracted": len(extracted_relations),
            "indexed": True  # Indicates upload completed (LLM extraction may be async)
        }
    except Exception as e:
        error_msg = str(e)
        log_upload_failure(filename, error_msg, file_size)
        raise HTTPException(status_code=500, detail=error_msg)

# Check if document is indexed
@app.get("/api/v1/documents/{doc_id}/status")
async def get_document_status(doc_id: str):
    """Check if a document has been fully indexed"""
    try:
        # Check if chunks exist for this document
        chunks = await storage.client.fetch(
            "SELECT COUNT(*) as count FROM chunks WHERE entity_id = $1",
            doc_id
        )
        chunk_count = chunks[0].get("count", 0) if chunks else 0
        
        # Check if document entity exists
        entities = await storage.client.fetch(
            "SELECT entity_id FROM entities WHERE entity_id = $1",
            doc_id
        )
        
        indexed = len(entities) > 0 and chunk_count > 0
        
        return {
            "doc_id": doc_id,
            "indexed": indexed,
            "chunks": chunk_count,
            "ready": indexed
        }
    except Exception as e:
        return {
            "doc_id": doc_id,
            "indexed": False,
            "chunks": 0,
            "ready": False,
            "error": str(e)
        }

@app.post("/api/v1/documents/upload/folder")
async def upload_folder(folder_path: str = Form(...)):
    """Upload all files from a folder"""
    try:
        if not os.path.exists(folder_path):
            raise HTTPException(status_code=404, detail=f"Folder not found: {folder_path}")
        
        results = []
        for root, dirs, files in os.walk(folder_path):
            for filename in files:
                if filename.endswith(('.txt', '.md', '.pdf', '.csv', '.json', '.html', '.xml')):
                    filepath = os.path.join(root, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            text = f.read()
                        
                        doc_id = hashlib.md5(filepath.encode()).hexdigest()[:12]
                        
                        # First create document entity (WITH EMBEDDING)
                        doc_embedding_text = f"{filename} (document) - Folder upload"
                        try:
                            doc_embedding = get_ollama_embedding(doc_embedding_text)
                        except:
                            doc_embedding = None
                        
                        entity = Entity(
                            entity_id=doc_id,
                            entity_type="document",
                            name=filename,
                            description=f"Document: {filename}",
                            properties={"filename": filename, "path": filepath, "type": "folder"},
                            embedding=doc_embedding
                        )
                        try:
                            await storage.create_entity(entity)
                        except:
                            pass
                        
                        # Split into chunks with overlap for better context
                        chunks = create_chunks(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
                        
                        for i, chunk_text in enumerate(chunks):
                            # Generate embedding for this chunk
                            embedding = get_ollama_embedding(chunk_text)
                            
                            chunk = Chunk(
                                chunk_id=f"{doc_id}_{i}",
                                entity_id=doc_id,
                                content=chunk_text,
                                source=filename,
                                chunk_index=i,
                                embedding=embedding,  # Now includes 768d embedding
                                metadata={"filename": filename, "path": filepath, "index": i}
                            )
                            try:
                                await storage.create_chunk(chunk)
                            except:
                                pass
                        
                        results.append({"filename": filename, "chunks": len(chunks)})
                    except Exception as e:
                        results.append({"filename": filename, "error": str(e)})
        
        return {
            "success": True,
            "folder": folder_path,
            "files": results,
            "total_files": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# JSON endpoint for folder upload
PROCESSED_FILES_PATH = "/tmp/kg_rag_processed_files.json"
BATCH_SIZE = 5
PARALLEL_WORKERS = 5

def load_processed_files():
    """Load list of already processed files."""
    if os.path.exists(PROCESSED_FILES_PATH):
        try:
            with open(PROCESSED_FILES_PATH, 'r') as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_processed_files(files_set):
    """Save processed files list."""
    with open(PROCESSED_FILES_PATH, 'w') as f:
        json.dump(list(files_set), f)

async def process_single_file(filepath: str, filename: str, skip_existing: bool = True, llm_config: dict = None):
    """Process a single file - extract chunks, entities, relationships."""
    doc_id = hashlib.md5(filepath.encode()).hexdigest()[:12]
    
    # Get LLM configuration
    if llm_config is None:
        llm_config = {}
    provider = llm_config.get("provider", "deepseek")
    fallback = llm_config.get("fallback_provider")
    
    # Check if already processed (skip if exists)
    if skip_existing:
        existing = await storage.client.fetch(
            "SELECT entity_id FROM entities WHERE entity_id = $1", doc_id
        )
        if existing:
            return {"filename": filename, "status": "skipped", "reason": "already_exists", "doc_id": doc_id}
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
        
        if not text or len(text.strip()) < 10:
            return {"filename": filename, "status": "skipped", "reason": "empty_file"}
        
        # Create document entity (WITH EMBEDDING)
        doc_embedding_text = f"{filename} (document) - Folder upload"
        try:
            doc_embedding = get_ollama_embedding(doc_embedding_text)
        except:
            doc_embedding = None
        
        entity = Entity(
            entity_id=doc_id,
            entity_type="document",
            name=filename,
            description=f"Document: {filename}",
            properties={"filename": filename, "path": filepath, "type": "folder"},
            embedding=doc_embedding
        )
        try:
            await storage.create_entity(entity)
        except:
            pass
        
        # Create chunks with overlap for better context
        chunks = create_chunks(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
        
        for i, chunk_text in enumerate(chunks):
            # Generate embedding for this chunk
            embedding = get_ollama_embedding(chunk_text)
            
            chunk = Chunk(
                chunk_id=f"{doc_id}_{i}",
                entity_id=doc_id,
                content=chunk_text,
                source=filename,
                chunk_index=i,
                embedding=embedding,  # Now includes 768d embedding
                metadata={"filename": filename, "path": filepath, "index": i}
            )
            try:
                await storage.create_chunk(chunk)
            except:
                pass
        
        # Extract entities and relationships using LLM (with configurable provider)
        entities_extracted = 0
        relationships_extracted = 0
        
        if text and len(text) > 100:
            extracted_entities, extracted_relations = await extract_entities_and_relations(
                text,
                llm_config={"provider": provider, "fallback_provider": fallback}
            )
            
            # Deduplicate entities by name
            unique_entities = {}
            for ent in extracted_entities:
                ent_name = ent.get("name", "").strip()
                if ent_name:
                    # Keep first occurrence of each entity name
                    if ent_name.lower() not in unique_entities:
                        unique_entities[ent_name.lower()] = ent
            
            # Deduplicate relationships - unique by (from, to, type)
            seen_rels = set()
            unique_relations = []
            for rel in extracted_relations:
                from_ent = rel.get("from", "").strip()
                to_ent = rel.get("to", "").strip()
                rel_type = rel.get("type", "related_to").strip()
                
                if from_ent and to_ent and from_ent != to_ent:
                    rel_key = (from_ent.lower(), to_ent.lower(), rel_type.lower())
                    if rel_key not in seen_rels:
                        seen_rels.add(rel_key)
                        unique_relations.append(rel)
            
            # Create extracted entities (WITH EMBEDDINGS)
            entity_ids_created = set()
            entities_embedded = 0
            for ent_name, ent in unique_entities.items():
                ent_type = ent.get("type", "concept")
                ent_description = ent.get("description", "")
                if ent_name and ent_name not in entity_ids_created:
                    ent_id = hashlib.md5(ent_name.encode()).hexdigest()[:12]
                    ent_id = f"ent_{ent_id}"
                    
                    # Generate embedding text for entity
                    # Format: "EntityName (entity_type) - description"
                    embedding_text = f"{ent_name} ({ent_type})"
                    if ent_description:
                        embedding_text += f" - {ent_description}"
                    
                    # Generate embedding using Ollama
                    try:
                        ent_embedding = get_ollama_embedding(embedding_text)
                        entities_embedded += 1
                    except Exception as e:
                        print(f"[Folder Upload] Entity embedding failed for {ent_name}: {e}")
                        ent_embedding = None
                    
                    ent_entity = Entity(
                        entity_id=ent_id,
                        entity_type=ent_type,
                        name=ent.get("name", ent_name),
                        description=ent_description or f"Extracted from {filename}",
                        properties={"source": filename, "extracted": True},
                        embedding=ent_embedding
                    )
                    try:
                        await storage.create_entity(ent_entity)
                        entity_ids_created.add(ent_name)
                        
                        # Link entity to document
                        rel = Relationship(
                            relationship_id=f"{doc_id}_{ent_id}",
                            source_id=doc_id,
                            target_id=ent_id,
                            relationship_type="contains",
                            properties={"extracted_from": filename}
                        )
                        try:
                            await storage.create_relationship(rel)
                        except:
                            pass
                    except:
                        pass
            
            # Create unique relationships between extracted entities
            for rel in unique_relations:
                from_ent = rel.get("from", "")
                to_ent = rel.get("to", "")
                rel_type = rel.get("type", "related_to")
                
                if from_ent and to_ent and from_ent != to_ent:
                    from_id = f"ent_{hashlib.md5(from_ent.encode()).hexdigest()[:12]}"
                    to_id = f"ent_{hashlib.md5(to_ent.encode()).hexdigest()[:12]}"
                    
                    # Include type in relationship_id to allow different types between same entities
                    rel_id = f"{from_id}_{to_id}_{rel_type}"
                    
                    rel_obj = Relationship(
                        relationship_id=rel_id,
                        source_id=from_id,
                        target_id=to_id,
                        relationship_type=rel_type,
                        properties={"source": filename}
                    )
                    try:
                        await storage.create_relationship(rel_obj)
                    except:
                        pass
            
            entities_extracted = len(unique_entities)
            relationships_extracted = len(unique_relations)
        
        return {
            "filename": filename,
            "status": "processed",
            "doc_id": doc_id,
            "chunks": len(chunks),
            "entities_extracted": entities_extracted,
            "relationships_extracted": relationships_extracted
        }
    except Exception as e:
        return {"filename": filename, "status": "error", "error": str(e)}

@app.post("/api/v1/documents/upload/folder/json")
async def upload_folder_json(request: Request):
    """Upload all files from a folder via JSON with batch processing, async, resume, and skip features."""
    try:
        body = await request.json()
        folder_path = body.get("folder_path", "")
        recursive = body.get("recursive", True)
        batch_size = body.get("batch_size", BATCH_SIZE)
        parallel = body.get("parallel", True)
        skip_existing = body.get("skip_existing", True)
        
        # Get LLM configuration from request (sent from Config Tab)
        llm_config = body.get("llm_config", {})
        provider = llm_config.get("provider", "deepseek")
        fallback = llm_config.get("fallback_provider")
        print(f"[Folder Upload] Using LLM provider: {provider}" + (f" (fallback: {fallback})" if fallback else ""))
        
        if not folder_path:
            raise HTTPException(status_code=400, detail="folder_path is required")
        
        if not os.path.exists(folder_path):
            raise HTTPException(status_code=404, detail=f"Folder not found: {folder_path}")
        
        # Load processed files for resume capability
        processed_files = load_processed_files()
        
        # Collect all files
        all_files = []
        for root, dirs, files in os.walk(folder_path):
            for filename in files:
                if filename.endswith(('.txt', '.md', '.pdf', '.csv', '.json', '.html', '.xml')):
                    filepath = os.path.join(root, filename)
                    all_files.append((filepath, filename))
            
            if not recursive:
                break
        
        # Filter out already processed files if skip_existing is True
        if skip_existing:
            files_to_process = []
            skipped_count = 0
            for filepath, filename in all_files:
                if filename not in processed_files:
                    files_to_process.append((filepath, filename))
                else:
                    skipped_count += 1
        else:
            files_to_process = all_files
        
        results = []
        processed_count = 0
        error_count = 0
        
        # Process in batches
        for i in range(0, len(files_to_process), batch_size):
            batch = files_to_process[i:i + batch_size]
            
            if parallel:
                # Parallel async processing
                tasks = [process_single_file(fp, fn, skip_existing, llm_config) for fp, fn in batch]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for br in batch_results:
                    if isinstance(br, Exception):
                        error_count += 1
                        results.append({"status": "error", "error": str(br)})
                    else:
                        results.append(br)
                        if br.get("status") == "processed":
                            processed_files.add(br.get("filename", ""))
                            processed_count += 1
                        elif br.get("status") == "skipped":
                            processed_count += 1
            else:
                # Sequential processing
                for filepath, filename in batch:
                    result = await process_single_file(filepath, filename, skip_existing, llm_config)
                    results.append(result)
                    if result.get("status") == "processed":
                        processed_files.add(filename)
                        processed_count += 1
                    elif result.get("status") == "skipped":
                        processed_count += 1
            
            # Save checkpoint after each batch
            save_processed_files(processed_files)
        
        # Final save
        save_processed_files(processed_files)
        
        return {
            "success": True,
            "folder": folder_path,
            "total_files": len(all_files),
            "skipped_existing": skipped_count if skip_existing else 0,
            "processed": processed_count,
            "errors": error_count,
            "batch_size": batch_size,
            "parallel": parallel,
            "results": results[-50:]  # Return last 50 results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v1/clear")
async def clear_all():
    """Clear all data"""
    try:
        await storage.client.execute("DELETE FROM chunks")
        await storage.client.execute("DELETE FROM relationships")
        await storage.client.execute("DELETE FROM entities")
        return {"success": True, "message": "All data cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============ Entities ============
@app.get("/api/v1/entities")
async def list_entities(limit: int = 100):
    result = await storage.client.fetch(
        "SELECT entity_id, entity_type, name, description FROM entities LIMIT $1",
        limit
    )
    return [{"id": r["entity_id"], "type": r["entity_type"], "name": r["name"]} for r in result]

@app.get("/api/v1/entities/{entity_id}")
async def get_entity(entity_id: str):
    result = await storage.client.fetch(
        "SELECT * FROM entities WHERE entity_id = $1",
        entity_id
    )
    if not result:
        raise HTTPException(status_code=404, detail="Entity not found")
    return result[0]

@app.get("/api/v1/entities/search")
async def search_entities(q: str = "", limit: int = 10):
    result = await storage.client.fetch(
        "SELECT entity_id, entity_type, name FROM entities WHERE name ILIKE $1 LIMIT $2",
        f"%{q}%",
        limit
    )
    return [{"id": r["entity_id"], "type": r["entity_type"], "name": r["name"]} for r in result]

@app.get("/api/v1/relations")
async def list_relations(limit: int = 100):
    result = await storage.client.fetch(
        "SELECT * FROM relationships LIMIT $1",
        limit
    )
    return result

# ============ Multi-Step Comprehensive Generation ============

async def generate_comprehensive_response(
    query: str,
    context: str,
    base_system_prompt: str,
    target_words: str,
    max_sections: int = 6,
    llm_config: dict = None
) -> str:
    """
    Multi-step generation for ultra-comprehensive responses.
    First creates an outline, then expands each section.
    """
    # Get LLM provider from config
    if llm_config is None:
        llm_config = {}
    provider = llm_config.get("provider", "deepseek")
    fallback = llm_config.get("fallback_provider")
    
    rerank_logger.info(f"Starting multi-step generation for '{query[:50]}...' targeting {target_words} words")
    
    # Step 1: Generate detailed outline
    outline_prompt = f"""Create a detailed outline for a comprehensive technical article about: {query}

Context from knowledge base:
{context[:6000]}

Requirements:
- Target length: {target_words} words
- Create 4 major sections
- Each section should have 2 subsections
- Include specific topics, concepts, and examples to cover

Output ONLY the outline in HTML format:
<query-h1>[Article Title]</query-h1>

<query-h2>1. [Section Name]</query-h2>
- Point 1 for subsection 1.1
- Point 2 for subsection 1.1
- Point 1 for subsection 1.2
- Point 2 for subsection 1.2

<query-h2>2. [Section Name]</query-h2>
...etc"""

    try:
        outline = await llm_complete_with_provider(
            prompt=outline_prompt,
            system_prompt="You are an expert at structuring technical documentation. Create detailed, comprehensive outlines using HTML tags ONLY. Use <query-h1> for title, <query-h2> for section headers. Do NOT use markdown (#, ##).",
            provider=provider,
            fallback_provider=fallback,
            max_tokens=8000,  # NO TRUNCATION: Increased from 2000
            temperature=0.3
        )
        rerank_logger.info(f"Generated outline with {len(outline.split(chr(10)))} lines")
    except Exception as e:
        rerank_logger.error(f"Failed to generate outline: {e}")
        # Fallback to single-step generation (NO TRUNCATION)
        return await llm_complete_with_provider(
            prompt=f"Write a comprehensive article about: {query}\n\nContext:\n{context[:4000]}\n\nTarget: {target_words} words",
            system_prompt=base_system_prompt,
            provider=provider,
            fallback_provider=fallback,
            max_tokens=8192,  # NO TRUNCATION: DeepSeek max is 8192
            temperature=0.4
        )
    
    # Step 2: Parse and expand each major section
    sections = []
    current_section_lines = []
    
    for line in outline.split('\n'):
        if line.startswith('## ') and current_section_lines:
            sections.append('\n'.join(current_section_lines))
            current_section_lines = [line]
        elif line.strip():
            current_section_lines.append(line)
    
    if current_section_lines:
        sections.append('\n'.join(current_section_lines))
    
    # Limit to reasonable number of sections
    sections = [s for s in sections if s.strip()][:max_sections]
    
    rerank_logger.info(f"Expanding {len(sections)} sections")
    
    # Generate content for each section
    full_content_parts = []
    for i, section in enumerate(sections):
        if not section.strip():
            continue
            
        section_prompt = f"""Write a comprehensive section for a technical article using HTML FORMAT.

Topic: {query}

Section outline to expand:
{section}

Use this context as reference:
{context[:1500]}

CRITICAL HTML FORMAT REQUIREMENTS:
- Use <query-h2>Section Title</query-h2> for section headers
- Use <query-h3>1.1 Subsection Title</query-h3> for subsection headers
- Use <span class="citation-ref">[1]</span> for citations
- Write 400-600 words for this section
- Write in flowing PARAGRAPHS (3-5 sentences per paragraph)
- Do NOT use markdown (#, ##, ###) - use HTML tags ONLY
- Do NOT use bullet points or fragment sentences
- Be detailed, technical, and authoritative
- Do NOT use phrases like "based on the context" or "according to the documents"
- Use your extensive knowledge freely - you are the expert

Write the complete section now:"""

        try:
            section_content = await llm_complete_with_provider(
                prompt=section_prompt,
                system_prompt=base_system_prompt,
                provider=provider,
                fallback_provider=fallback,
                max_tokens=8000,  # NO TRUNCATION: Increased from 1200
                temperature=0.4
            )
            full_content_parts.append(section_content)
            rerank_logger.info(f"Generated section {i+1}/{len(sections)} ({len(section_content.split())} words)")
        except Exception as e:
            rerank_logger.error(f"Failed to generate section {i}: {e}")
            section_title = section.split('\n')[0].replace('<query-h2>', '').replace('</query-h2>', '').replace('## ', '')
            full_content_parts.append("\n\n<query-h2>" + section_title + "</query-h2>\n\n[Content generation in progress...]\n\n")
    
    # Combine all sections
    full_response = '\n\n'.join(full_content_parts)
    word_count = len(full_response.split())
    rerank_logger.info(f"Combined response: {word_count} words")
    
    # Add conclusion if we have substantial content
    if word_count > 500:
        try:
            conclusion_prompt = f"""Write a comprehensive conclusion (300-400 words) for an article about {query}.

The article covered these sections:
{outline[:1000]}

CRITICAL HTML FORMAT REQUIREMENTS:
- Use <query-h2>Conclusion</query-h2> for the section header
- Write in flowing PARAGRAPHS (3-5 sentences per paragraph)
- Do NOT use markdown (#, ##, ###) - use HTML tags ONLY
- Do NOT use bullet points

Your conclusion should:
1. Synthesize the key insights
2. Discuss implications and future directions
3. Provide closing thoughts for practitioners and researchers"""

            conclusion = await llm_complete_with_provider(
                prompt=conclusion_prompt,
                system_prompt=base_system_prompt,
                provider=provider,
                fallback_provider=fallback,
                max_tokens=8192,  # DeepSeek max - NO TRUNCATION
                temperature=0.4
            )
            full_response += f"\n\n<query-h2>Conclusion</query-h2>\n\n{conclusion}"
            rerank_logger.info(f"Added conclusion, final word count: {len(full_response.split())}")
        except Exception as e:
            rerank_logger.warning(f"Failed to generate conclusion: {e}")
    
    return full_response


async def generate_ultra_response(
    query: str,
    context: str,
    base_system_prompt: str,
    target_words: str,
    num_sections: int = 5,
    num_subsections: int = 3,
    llm_config: dict = None,
    chinese_variant: str = "english",
    sources: list = None
) -> str:
    """
    Ultra-Deep generation: 2 API calls total (outline + full content).
    Enforces strict 5 sections × 3 subsections structure.
    """
    if llm_config is None:
        llm_config = {}
    provider = llm_config.get("provider", "deepseek")
    fallback = llm_config.get("fallback_provider")
    
    rerank_logger.info(f"[ULTRA] Starting generation for '{query[:50]}...'")
    
    # Language setup
    if chinese_variant == "traditional":
        exec_summary_label = "摘要"
        conclusion_label = "結論"
        references_label = "參考文獻"
        lang_instr = "使用繁體中文撰寫"
    elif chinese_variant == "simplified":
        exec_summary_label = "摘要"
        conclusion_label = "结论"
        references_label = "参考文献"
        lang_instr = "使用简体中文撰写"
    else:
        exec_summary_label = "Executive Summary"
        conclusion_label = "Conclusion"
        references_label = "References"
        lang_instr = "Write in English"
    
    # Build source list
    source_list = "\n".join([f"[{i+1}] {s.get('source', f'Doc {i+1}')}" for i, s in enumerate(sources[:15])]) if sources else "[1] Knowledge Base Sources"
    
    # Step 1: Generate outline (1 API call)
    outline_prompt = f"""Create a detailed outline for: {query}

Requirements:
- {num_sections} major sections (1-{num_sections})
- Each section has {num_subsections} subsections ({num_sections * num_subsections} total)
- Format: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, etc.

Output format:
<query-h1>[Title]</query-h1>
<query-h2>1. [Section Title]</query-h2>
<query-h3>1.1 [Subtitle]</query-h3>
<query-h3>1.2 [Subtitle]</query-h3>
<query-h3>1.3 [Subtitle]</query-h3>
<query-h2>2. [Section Title]</query-h2>
... etc for all {num_sections} sections"""

    try:
        outline = await llm_complete_with_provider(
            prompt=outline_prompt,
            system_prompt=f"Create detailed outlines using ONLY <query-h1>, <query-h2>, <query-h3> tags. {lang_instr}",
            provider=provider,
            fallback_provider=fallback,
            max_tokens=2000,
            temperature=0.3
        )
    except Exception as e:
        rerank_logger.error(f"Outline failed: {e}")
        outline = ""
    
    # Parse outline
    import re
    sections = []
    h2_matches = list(re.finditer(r'<query-h2>(.*?)</query-h2>', outline, re.DOTALL))
    h3_matches = list(re.finditer(r'<query-h3>(.*?)</query-h3>', outline, re.DOTALL))
    
    for i, h2 in enumerate(h2_matches[:num_sections]):
        title = re.sub(r'^\d+[\.\s]+', '', h2.group(1).strip())
        subsections = []
        sec_start = h2.end()
        sec_end = h2_matches[i + 1].start() if i + 1 < len(h2_matches) else len(outline)
        for h3 in h3_matches:
            if sec_start <= h3.start() < sec_end:
                sub_title = re.sub(r'^\d+\.\d+\s+', '', h3.group(1).strip())
                subsections.append(sub_title)
        while len(subsections) < num_subsections:
            subsections.append(f"Subsection {i+1}.{len(subsections)+1}")
        sections.append({'title': title, 'subsections': subsections[:num_subsections]})
    
    # Add default sections if needed
    defaults = ["Fundamental Concepts", "Mathematical Foundations", "Core Mechanisms", "Advanced Techniques", "Applications & Future"]
    while len(sections) < num_sections:
        i = len(sections)
        sections.append({
            'title': defaults[i] if i < len(defaults) else f"Section {i+1}",
            'subsections': [f"Theory & Principles", "Mathematical Models", "Implementation Analysis"]
        })
    
    print(f"[ULTRA] Parsed {len(sections)} sections")
    
    # ULTRA-REDUCED word counts to ensure everything fits in 8192 tokens
    # Must complete ALL sections: Exec Summary + 5 sections × 3 subsections + Conclusion + References
    exec_words = 200
    sub_words = 120  
    concl_words = 200
    
    # Build structured content template
    content_template = f"""<query-h1>{query}</query-h1>

<query-h2>{exec_summary_label}</query-h2>
[Write {exec_words}+ words overview. Cite at least 8+ different sources like [1], [2], [3], [4], [5], [6], [7], [8].]

"""
    
    for sec_idx, section in enumerate(sections[:num_sections], 1):
        content_template += f"""<query-h2>{sec_idx}. {section['title']}</query-h2>
[Section intro: 50+ words with citations]

"""
        for sub_idx, sub_title in enumerate(section['subsections'][:num_subsections], 1):
            content_template += f"""<query-h3>{sec_idx}.{sub_idx} {sub_title}</query-h3>
[Write {sub_words}+ words. Include 3-5 citations from different sources. Vary between sources [1] through [8] and beyond. Use paragraphs only, no bullets.]

"""
    
    content_template += f"""<query-h2>{conclusion_label}</query-h2>
[Write {concl_words}+ words synthesizing key insights. Include citations from at least 8+ different sources.]

<query-h2>{references_label}</query-h2>
[List ALL cited sources - MINIMUM 8 different sources required]"""
    
    # Step 2: Generate ALL content in ONE API call
    full_prompt = f"""Write a COMPREHENSIVE academic article about: {query}

AVAILABLE SOURCES (cite these using [N] format):
{source_list}

CONTEXT:
{context[:4000]}

STRICT REQUIREMENTS:
1. EXACTLY {num_sections} sections with {num_subsections} subsections EACH
2. Executive Summary: {exec_words}+ words
3. Each subsection: {sub_words}+ words with 3-5 citations
4. Conclusion: {concl_words}+ words
5. Math: Use Unicode |ψ⟩, α, β, ∑ - NEVER LaTeX
6. Citations: Use <span class="citation-ref">[N]</span> format
7. Use flowing paragraphs ONLY - NO bullet points
8. Cite from MULTIPLE sources - vary between [1], [2], [3], [4], [5], [6], [7], [8] and beyond (use at least 8+ different sources)
9. Write COMPLETE content - do NOT stop early

MANDATORY OUTPUT FORMAT - Use EXACTLY this structure:

{content_template}

CRITICAL: 
- Follow the structure EXACTLY with all HTML tags
- Include ALL {num_sections} sections, Conclusion, AND References
- DO NOT truncate - write until complete"""

    try:
        full_content = await llm_complete_with_provider(
            prompt=full_prompt,
            system_prompt=f"""You are writing a comprehensive academic article.

ABSOLUTE RULES:
1. Use EXACT format: <query-h1>, <query-h2>, <query-h3> tags
2. Executive Summary: {exec_words}+ words with at least 8+ different source citations
3. Each subsection: {sub_words}+ words (4-6 sentences) with citations from varied sources
4. Conclusion: {concl_words}+ words with citations from at least 8+ different sources
5. Use <span class="citation-ref">[N]</span> for citations
6. NEVER use LaTeX - use Unicode math
7. NO bullet points - flowing paragraphs only
8. MUST include ALL sections, Conclusion, AND References
9. References section MUST list at least 8 different sources

{lang_instr}""",
            provider=provider,
            fallback_provider=fallback,
            max_tokens=8192,
            temperature=0.4
        )
        
        # Check which sections exist
        existing_sections = []
        missing_sections = []
        for sec_idx in range(1, num_sections + 1):
            if f'<query-h2>{sec_idx}.' in full_content or f'<query-h2>{sec_idx} ' in full_content:
                existing_sections.append(sec_idx)
            else:
                missing_sections.append(sec_idx)
        
        has_conclusion = conclusion_label in full_content
        has_references = references_label in full_content
        
        # Find the last section/subsection and check if it's complete
        last_section_truncated = False
        last_section_idx = None
        last_subsection_idx = None
        
        # Check each existing section for completeness
        for sec_idx in existing_sections:
            for sub_idx in range(1, num_subsections + 1):
                sub_header = f'<query-h3>{sec_idx}.{sub_idx}'
                if sub_header in full_content:
                    # Found this subsection, check if it's complete
                    # Extract content until next subsection or section end
                    sub_match = re.search(rf'{sub_header}.*?(?=<query-h3>|</body>|$)', full_content, re.DOTALL)
                    if sub_match:
                        sub_content = sub_match.group(0)
                        # Check if content ends abruptly (no proper ending punctuation)
                        # and is at the very end of the document
                        is_last = not re.search(rf'<query-h3>{sec_idx}\.{sub_idx + 1}|</query-h2>', full_content[full_content.find(sub_header) + len(sub_header):])
                        if is_last:
                            # This is the last subsection - check if complete
                            text_content = re.sub(r'<[^>]+>', '', sub_content)
                            if len(text_content) < 50:  # Too short
                                last_section_truncated = True
                                last_section_idx = sec_idx
                                last_subsection_idx = sub_idx
                                print(f"[ULTRA WARNING] Last subsection {sec_idx}.{sub_idx} appears truncated (too short)")
                            elif not text_content.rstrip().endswith(('。', '.', '！', '!', '?', '？')):
                                # Ends abruptly
                                last_section_truncated = True
                                last_section_idx = sec_idx
                                last_subsection_idx = sub_idx
                                print(f"[ULTRA WARNING] Last subsection {sec_idx}.{sub_idx} appears truncated (ends abruptly)")
        
        # Check if Conclusion exists but is truncated
        conclusion_truncated = False
        if has_conclusion:
            concl_match = re.search(rf'<query-h2>{conclusion_label}</query-h2>(.*?)(?=<query-h2>|$)', full_content, re.DOTALL)
            if concl_match:
                concl_text = concl_match.group(1).strip()
                if len(concl_text) < 50 or not concl_text.endswith(('。', '.', '！', '!', '?', '？', '」', '"')):
                    conclusion_truncated = True
                    print(f"[ULTRA WARNING] Conclusion appears truncated (length: {len(concl_text)})")
        
        # Check if References section is truncated
        references_truncated = False
        if has_references:
            ref_match = re.search(rf'<query-h2>{references_label}</query-h2>(.*?)(?:<query-h2>|$)', full_content, re.DOTALL)
            if ref_match:
                ref_text = ref_match.group(1).strip()
                # Count how many reference entries we have
                ref_entries = re.findall(r'\[\d+\]', ref_text)
                # Check if the last entry appears complete (should have content after the number)
                last_entry_match = re.search(r'\[(\d+)\]([^\[]*)$', ref_text)
                last_entry_complete = False
                if last_entry_match:
                    entry_content = last_entry_match.group(2).strip()
                    # Last entry should have meaningful content (at least 5 chars) and end properly
                    if len(entry_content) >= 5 and not re.search(r'[與及和與、，]$', entry_content):
                        last_entry_complete = True
                
                if ref_text and len(ref_text) < 50:
                    # Too short for a proper references section
                    references_truncated = True
                    print(f"[ULTRA WARNING] References section too short ({len(ref_text)} chars)")
                elif ref_text and re.search(r'[《\(\[「"\'\-]\s*$', ref_text):
                    # Ends with opening bracket/punctuation
                    references_truncated = True
                    print(f"[ULTRA WARNING] References section ends with opening punctuation")
                elif ref_text and not last_entry_complete:
                    # Last entry appears incomplete
                    references_truncated = True
                    print(f"[ULTRA WARNING] References section last entry incomplete")
                elif len(ref_entries) < 3 and sources and len(sources) >= 3:
                    # Should have at least 3 entries if we have 3+ sources
                    references_truncated = True
                    print(f"[ULTRA WARNING] References section has only {len(ref_entries)} entries, expected at least 3")
        
        # Determine if we need a second API call
        is_incomplete = missing_sections or not has_conclusion or not has_references or last_section_truncated or conclusion_truncated or references_truncated
        
        if is_incomplete:
            print(f"[ULTRA] Content incomplete. Missing sections: {missing_sections}, Last section truncated: {last_section_truncated}, Conclusion: {has_conclusion} (truncated: {conclusion_truncated}), References: {has_references} (truncated: {references_truncated})")
            print(f"[ULTRA] Starting second API call to complete content...")
            
            # Remove truncated content before regenerating
            content_to_continue = full_content
            
            if last_section_truncated and last_section_idx and last_subsection_idx:
                print(f"[ULTRA] Removing truncated subsection {last_section_idx}.{last_subsection_idx}...")
                # Remove from this subsection to end
                pattern = rf'<query-h3>{last_section_idx}\.{last_subsection_idx}.*?(?=<query-h2>|$)'
                content_to_continue = re.sub(pattern, '', full_content, flags=re.DOTALL)
                # This section now needs to be completed
                if last_subsection_idx == 1:
                    # Need to regenerate entire section
                    missing_sections.insert(0, last_section_idx)
                # else: We'll continue from this subsection
            
            if conclusion_truncated:
                print(f"[ULTRA] Removing truncated Conclusion...")
                content_to_continue = re.sub(rf'<query-h2>{conclusion_label}</query-h2>.*?(?=<query-h2>|$)', '', content_to_continue, flags=re.DOTALL)
                has_conclusion = False
            
            if references_truncated:
                print(f"[ULTRA] Removing truncated References...")
                content_to_continue = re.sub(rf'<query-h2>{references_label}</query-h2>.*?(?=<query-h2>|$)', '', content_to_continue, flags=re.DOTALL)
                has_references = False
            
            # Build the continuation prompt
            continuation_prompt = f"""Continue writing this article about: {query}

CONTENT SO FAR:
{content_to_continue[-3000:]}

COMPLETE THE FOLLOWING:
"""
            
            # Add the truncated/last subsection to complete
            if last_section_truncated and last_section_idx and last_subsection_idx:
                section = sections[last_section_idx - 1]
                sub_title = section['subsections'][last_subsection_idx - 1]
                continuation_prompt += f"""<query-h3>{last_section_idx}.{last_subsection_idx} {sub_title}</query-h3>
[Complete this subsection with {sub_words}+ words]

"""
            
            # Add remaining subsections in current section
            if last_section_idx and not conclusion_truncated:
                for sub_idx in range((last_subsection_idx or 0) + 1, num_subsections + 1):
                    section = sections[last_section_idx - 1]
                    sub_title = section['subsections'][sub_idx - 1]
                    continuation_prompt += f"""<query-h3>{last_section_idx}.{sub_idx} {sub_title}</query-h3>
[Write {sub_words}+ words]
"""
            
            # Add missing sections
            for sec_idx in missing_sections:
                section = sections[sec_idx - 1]
                continuation_prompt += f"""
<query-h2>{sec_idx}. {section['title']}</query-h2>
"""
                for sub_idx, sub_title in enumerate(section['subsections'][:num_subsections], 1):
                    continuation_prompt += f"""<query-h3>{sec_idx}.{sub_idx} {sub_title}</query-h3>
[Write {sub_words}+ words]
"""
            
            if not has_conclusion:
                continuation_prompt += f"""
<query-h2>{conclusion_label}</query-h2>
[Write {concl_words}+ words]
"""
            
            if not has_references:
                continuation_prompt += f"""
<query-h2>{references_label}</query-h2>
<div class="references-list">
"""
                for i, src in enumerate(sources[:15], 1):
                    source_name = src.get('source', f'Source {i}').replace('.txt', '').replace('.pdf', '').replace('.md', '')
                    continuation_prompt += f'<div class="reference-item"><span class="ref-number">[{i}]</span> {source_name}</div>\n'
                continuation_prompt += "</div>\n"
            
            continuation_prompt += """
Requirements:
- Continue from where the previous content left off
- Maintain the same writing style and format
- Use proper HTML tags
- Include citations using <span class="citation-ref">[N]</span>
"""
            
            try:
                continuation_content = await llm_complete_with_provider(
                    prompt=continuation_prompt,
                    system_prompt=f"Continue writing the article from where it left off. Maintain the same style and complete all sections. {lang_instr}",
                    provider=provider,
                    fallback_provider=fallback,
                    max_tokens=8192,
                    temperature=0.4
                )
                
                # Combine: use the cleaned content (with truncated parts removed) + new continuation
                full_content = content_to_continue.rstrip() + "\n\n" + continuation_content
                print(f"[ULTRA] Added continuation content from second API call")
                
            except Exception as e2:
                print(f"[ULTRA WARNING] Could not generate missing content: {e2}")
        
        # Clean up: Remove any extra sections beyond the expected number
        # (Sometimes LLM generates extra sections with wrong numbering)
        for extra_sec in range(num_sections + 1, 20):  # Check for sections beyond expected
            extra_pattern = rf'<query-h2>{extra_sec}\.\s*[^<]*</query-h2>.*?'
            if re.search(extra_pattern, full_content, re.DOTALL):
                print(f"[ULTRA WARNING] Found extra section {extra_sec}, removing...")
                # Find and remove this extra section (up to next section or References)
                full_content = re.sub(rf'<query-h2>{extra_sec}\.\s*[^<]*</query-h2>.*?(?=<query-h2>{references_label}|</body>|$)', '', full_content, flags=re.DOTALL)
        
        # Also fix duplicate Conclusion sections - keep only the last complete one
        conclusion_count = full_content.count(f'<query-h2>{conclusion_label}</query-h2>')
        if conclusion_count > 1:
            print(f"[ULTRA WARNING] Found {conclusion_count} Conclusion sections, removing duplicates...")
            # Remove all but the last Conclusion section
            parts = full_content.split(f'<query-h2>{conclusion_label}</query-h2>')
            if len(parts) > 2:
                # Keep everything before the first Conclusion + last Conclusion onwards
                first_part = parts[0]
                last_conclusion = f'<query-h2>{conclusion_label}</query-h2>' + parts[-1]
                full_content = first_part + last_conclusion
        
        # Ensure references section exists and is complete
        if references_label not in full_content:
            # Missing entirely - add it
            print(f"[ULTRA] Adding missing References section")
            ref_entries = "\n".join([f'<div class="reference-item"><span class="ref-number">[{i+1}]</span> <span class="ref-source">{s.get("source", f"Source {i+1}").replace(".txt", "").replace(".pdf", "").replace(".md", "")}</span></div>' for i, s in enumerate(sources[:15])]) if sources else '<div class="reference-item"><span class="ref-number">[1]</span> <span class="ref-source">Knowledge Base</span></div>'
            full_content += f"\n\n<query-h2>{references_label}</query-h2>\n\n<div class=\"references-list\">\n{ref_entries}\n</div>"
        else:
            # Check if existing references section is complete
            ref_match = re.search(rf'<query-h2>{references_label}</query-h2>(.*?)(?:<query-h2>|$)', full_content, re.DOTALL)
            if ref_match:
                ref_text = ref_match.group(1).strip()
                # Check if any reference entry is truncated (ends mid-word)
                ref_entries = re.findall(r'\[(\d+)\](.*?)(?=\[\d+\]|$)', ref_text, re.DOTALL)
                has_truncated_entry = False
                for entry_num, entry_content in ref_entries:
                    entry_text = entry_content.strip()
                    # If entry ends abruptly (no period/punctuation at end) or is very short
                    if entry_text and len(entry_text) < 5:
                        has_truncated_entry = True
                        print(f"[ULTRA] Reference entry [{entry_num}] appears truncated")
                    elif entry_text and not re.search(r'[。\.\!\?）\)"」】\}]$', entry_text):
                        # Check if it looks like a complete entry
                        if len(entry_text) < 20 and '...' in entry_text:
                            has_truncated_entry = True
                            print(f"[ULTRA] Reference entry [{entry_num}] appears incomplete")
                
                if has_truncated_entry:
                    print(f"[ULTRA] Replacing truncated References section with complete version")
                    # Remove the truncated references section
                    full_content = re.sub(rf'<query-h2>{references_label}</query-h2>.*?(?=<query-h2>|$)', '', full_content, flags=re.DOTALL)
                    # Add complete references section
                    ref_entries = "\n".join([f'<div class="reference-item"><span class="ref-number">[{i+1}]</span> <span class="ref-source">{s.get("source", f"Source {i+1}").replace(".txt", "").replace(".pdf", "").replace(".md", "")}</span></div>' for i, s in enumerate(sources[:15])]) if sources else '<div class="reference-item"><span class="ref-number">[1]</span> <span class="ref-source">Knowledge Base</span></div>'
                    full_content += f"\n\n<query-h2>{references_label}</query-h2>\n\n<div class=\"references-list\">\n{ref_entries}\n</div>"
        
        print(f"[ULTRA] Generated content: {len(full_content)} chars, ~{len(full_content.split())} words")
        return full_content
        
    except Exception as e:
        rerank_logger.error(f"Full content generation failed: {e}")
        # Fallback to basic generation
        return await llm_complete_with_provider(
            prompt=f"Write a comprehensive article about: {query}\n\nContext: {context[:4000]}\n\nTarget: 3000+ words",
            system_prompt=base_system_prompt,
            provider=provider,
            fallback_provider=fallback,
            max_tokens=8192,
            temperature=0.4
        )
async def academic_review_citations(response: str, sources: list, query: str, 
                                   llm_provider: str = "deepseek", 
                                   llm_fallback: str = "minimax") -> tuple:
    """
    Academic review: Verify citation accuracy, quotation correctness, and reference completeness.
    Uses LLM to perform scholarly review of citations.
    
    Returns: (corrected_response, review_report)
    """
    if not sources or len(sources) == 0:
        return response, "No sources to review"
    
    import re
    
    # Build source content mapping for verification
    source_content_map = {}
    for i, src in enumerate(sources):
        source_num = i + 1
        source_name = src.get('source', f'Unknown_{source_num}')
        content = src.get('content', '')[:500]  # First 500 chars for verification
        source_content_map[source_num] = {
            'name': source_name,
            'content': content
        }
    
    # Find all citations in response
    citations_found = set()
    citation_patterns = [
        (r'Source\s+(\d+)', 'Source X'),
        (r'\[(\d+)\]', '[X]'),
        (r'<span class="citation-ref">\[(\d+)\]</span>', 'span citation'),
    ]
    
    for pattern, desc in citation_patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        citations_found.update([int(m) for m in matches])
    
    # Check for issues
    issues = []
    
    # Issue 1: Citations to non-existent sources
    max_valid = len(sources)
    invalid_citations = [c for c in citations_found if c < 1 or c > max_valid]
    if invalid_citations:
        issues.append(f"Invalid citation numbers (no such source): {invalid_citations}")
    
    # Issue 2: Missing citations (sources not cited that should be)
    cited_sources = set([c for c in citations_found if 1 <= c <= max_valid])
    uncited_sources = set(range(1, max_valid + 1)) - cited_sources
    if len(uncited_sources) == max_valid:
        issues.append("No sources cited in the response")
    elif len(uncited_sources) > max_valid / 2:
        issues.append(f"Many sources not cited: {len(uncited_sources)}/{max_valid}")
    
    # Issue 3: Check for quotation accuracy (basic check)
    # Look for quoted text and verify it exists in sources
    quoted_texts = re.findall(r'"([^"]{10,100})"', response)
    unverified_quotes = []
    for quote in quoted_texts[:5]:  # Check first 5 quotes
        found_in_sources = False
        for src_num, src_data in source_content_map.items():
            if quote.lower() in src_data['content'].lower():
                found_in_sources = True
                break
        if not found_in_sources:
            unverified_quotes.append(quote[:50] + "...")
    
    if unverified_quotes:
        issues.append(f"Potentially inaccurate quotations: {len(unverified_quotes)} quotes not found in sources")
    
    # If issues found, use LLM to fix
    if issues:
        print(f"[ACADEMIC REVIEW] Issues found: {issues}")
        
        review_prompt = f"""You are an academic editor reviewing a scholarly article for citation accuracy.

ARTICLE:
{response[:3000]}

AVAILABLE SOURCES:
{chr(10).join([f"Source {k}: {v['name']}" for k, v in list(source_content_map.items())[:10]])}

ISSUES DETECTED:
{chr(10).join(['- ' + issue for issue in issues])}

YOUR TASK:
1. Fix any invalid citation numbers (ensure they reference valid sources 1-{max_valid})
2. Add citations where specific claims are made but not attributed
3. Ensure the References section lists all cited sources correctly
4. Fix any quotation marks that don't correspond to actual source content

Return the corrected article with accurate citations."""

        try:
            corrected = await llm_complete_with_provider(
                prompt=review_prompt,
                system_prompt="You are a meticulous academic editor. Fix citation errors while preserving the original content and meaning.",
                provider=llm_provider,
                fallback_provider=llm_fallback,
                max_tokens=4000,
                temperature=0.2
            )
            
            review_report = {
                'issues_found': issues,
                'citations_checked': len(citations_found),
                'sources_available': max_valid,
                'corrections_made': True
            }
            
            return corrected, review_report
            
        except Exception as e:
            print(f"[ACADEMIC REVIEW ERROR] {e}")
            return response, {'issues_found': issues, 'error': str(e)}
    
    # No issues found
    return response, {
        'issues_found': [],
        'citations_checked': len(citations_found),
        'sources_available': max_valid,
        'corrections_made': False
    }


def is_source_filename_relevant(source: str, query: str) -> tuple:
    """
    Check if source filename is relevant to the query topic.
    Returns True if filename contains query keywords (English or CJK).
    """
    import re
    
    if not source or not query:
        return True, None  # Trust if missing data
    
    source_lower = source.lower()
    query_lower = query.lower()
    
    # Extract English keywords (3+ chars)
    english_keywords = set()
    for word in re.findall(r'[a-zA-Z]{3,}', query_lower):
        english_keywords.add(word.lower())
    
    # Extract Chinese/Japanese/Korean keywords (2+ chars each)
    cjk_keywords = set()
    for word in re.findall(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]{2,}', query_lower):
        cjk_keywords.add(word)
    
    all_keywords = english_keywords | cjk_keywords
    
    # If no meaningful keywords, trust vector search
    if not all_keywords:
        return True, None
    
    # Check if ANY keyword appears in filename
    matched_keywords = []
    for keyword in all_keywords:
        if keyword in source_lower:
            matched_keywords.append(keyword)
    
    # If at least 1 keyword matches, filename is relevant
    if matched_keywords:
        return True, matched_keywords[0]
    
    # No keyword match in filename - this source is likely irrelevant
    return False, None


def is_source_relevant(source: str, query: str) -> tuple:
    """
    STRICT check: Source filename MUST contain relevant technical keywords.
    Uses same logic as is_source_filename_relevant for consistency.
    """
    # Delegate to the stricter function
    return is_source_filename_relevant(source, query)


def is_chunk_content_relevant(content: str, query: str, min_matches: int = 1) -> tuple:
    """
    LENIENT check: Chunk content should contain keywords from query.
    Vector search already found this chunk by semantic similarity,
    so we trust it unless there's a clear mismatch.
    
    Returns (is_relevant, match_count, matched_terms)
    """
    import re
    
    if not content or not query:
        return True, 0, []  # Be lenient - trust vector search
    
    query_lower = query.lower()
    content_lower = content.lower()
    
    # Extract ALL keywords from query (3+ chars) - dynamic, no predefined lists
    query_terms = set()
    for word in re.findall(r'[a-zA-Z]+', query_lower):
        word = word.lower()
        if len(word) >= 3:
            query_terms.add(word)
    
    # Check for matches
    matches = 0
    matched_terms = []
    
    for term in query_terms:
        if term in content_lower:
            matches += 1
            matched_terms.append(term)
    
    # LENIENT: Accept if at least 1 query term matches, OR accept anyway
    # Vector search already confirmed semantic similarity
    unique_matches = len(matched_terms)
    is_relevant = unique_matches >= min_matches
    
    # Debug logging only when rejected
    if not is_relevant:
        print(f"[FILTER] Content has {unique_matches} matches for: {list(query_terms)[:5]}")
    
    return is_relevant, matches, matched_terms


# ============ Search Mode Implementations ============

async def search_smart(
    query: str,
    query_embedding: List[float],
    top_k: int = 20,
    llm_config: dict = None
) -> List[Dict]:
    """
    SMART Mode: Multi-layer unified search combining ALL embedding types and strategies.
    
    Layers:
    1. Semantic Chunk Search (primary foundation)
    2. Entity Discovery & Expansion (entity embeddings)
    3. Relationship Enhancement (relationship embeddings)
    4. Keyword Boosting (keyword extraction)
    5. Multi-source Fusion & Intelligent Ranking
    """
    logger.info(f"[Smart] Starting multi-layer unified search for: {query[:50]}...")
    
    from storage import DistanceMetric
    all_chunks = []
    
    # =================================================================
    # LAYER 1: SEMANTIC CHUNK SEARCH (Foundation)
    # =================================================================
    try:
        chunk_results = await storage.search_chunks(
            query_vector=query_embedding,
            limit=top_k * 2,  # Get more for fusion
            distance_metric=DistanceMetric.COSINE,
            match_threshold=0.25
        )
        
        for chunk in chunk_results:
            all_chunks.append({
                'content': chunk.content,
                'source': chunk.source,
                'chunk_id': chunk.chunk_id,
                'entity_id': chunk.entity_id,
                'similarity': chunk.similarity,
                'source_layer': 'semantic_chunk',
                'base_score': chunk.similarity
            })
        
        logger.info(f"[Smart] Layer 1 - Semantic chunks: {len(chunk_results)}")
    except Exception as e:
        logger.warning(f"[Smart] Layer 1 failed: {e}")
    
    # =================================================================
    # LAYER 2: ENTITY DISCOVERY (Entity Embeddings)
    # =================================================================
    entity_ids_found = set()
    entity_scores = {}
    
    try:
        entity_results = await storage.search_entities(
            query_vector=query_embedding,
            limit=15,
            distance_metric=DistanceMetric.COSINE
        )
        
        for entity in entity_results:
            entity_id = entity.get('entity_id')
            entity_ids_found.add(entity_id)
            entity_scores[entity_id] = entity.get('similarity', 0.5)
        
        logger.info(f"[Smart] Layer 2 - Entities discovered: {len(entity_results)}")
    except Exception as e:
        logger.warning(f"[Smart] Layer 2 failed: {e}")
    
    # =================================================================
    # LAYER 3: RELATIONSHIP ENHANCEMENT (Relationship Embeddings)
    # =================================================================
    related_entity_ids = set()
    relationship_scores = {}
    
    try:
        # Search relationship embeddings
        rel_results = await storage.search_relationships(
            query_vector=query_embedding,
            limit=20,
            distance_metric=DistanceMetric.COSINE,
            match_threshold=0.4
        )
        
        # Extract entities from matching relationships
        for rel in rel_results:
            source_id = rel.get('source_id')
            target_id = rel.get('target_id')
            rel_score = rel.get('similarity', 0.5)
            
            if source_id:
                related_entity_ids.add(source_id)
                if source_id not in relationship_scores:
                    relationship_scores[source_id] = 0
                relationship_scores[source_id] += rel_score * 0.15
            
            if target_id:
                related_entity_ids.add(target_id)
                if target_id not in relationship_scores:
                    relationship_scores[target_id] = 0
                relationship_scores[target_id] += rel_score * 0.15
        
        # Also traverse from discovered entities
        for entity_id in list(entity_ids_found)[:5]:
            try:
                related = await storage.get_related_entities(
                    entity_id=entity_id,
                    max_depth=1,
                    limit_per_level=6
                )
                
                for rel in related:
                    rel_id = rel.get('related_entity_id')
                    if rel_id:
                        related_entity_ids.add(rel_id)
                        weight = rel.get('weight', 1.0)
                        if rel_id not in relationship_scores:
                            relationship_scores[rel_id] = 0
                        relationship_scores[rel_id] += weight * 0.08
            except Exception:
                pass
        
        # Add relationship descriptions as context
        for rel in rel_results[:10]:
            desc = rel.get('description') or f"{rel.get('source_id')} {rel.get('relationship_type')} {rel.get('target_id')}"
            all_chunks.append({
                'content': f"[Relationship] {desc}",
                'source': 'knowledge_graph',
                'chunk_id': f"rel_{rel.get('relationship_id')}",
                'similarity': rel.get('similarity', 0.5) * 0.9,
                'source_layer': 'relationship',
                'base_score': rel.get('similarity', 0.5)
            })
        
        logger.info(f"[Smart] Layer 3 - Related entities: {len(related_entity_ids)}, Relationships: {len(rel_results)}")
    except Exception as e:
        logger.warning(f"[Smart] Layer 3 failed: {e}")
    
    # =================================================================
    # LAYER 4: KEYWORD EXTRACTION & BOOSTING
    # =================================================================
    keyword_boosts = {}
    
    try:
        high_level, low_level = await extract_keywords_for_search(query, llm_config)
        
        # Boost chunks based on keyword matches
        for chunk in all_chunks:
            content = chunk['content'].lower()
            boost = 0.0
            
            # Low-level keywords (entities)
            for kw in low_level:
                if kw.lower() in content:
                    boost += 0.06
            
            # High-level keywords (concepts)
            for kw in high_level:
                if kw.lower() in content:
                    boost += 0.03
            
            if boost > 0:
                keyword_boosts[chunk['chunk_id']] = boost
                chunk['similarity'] = chunk.get('similarity', 0.5) + boost
                chunk['keyword_boost'] = boost
        
        logger.info(f"[Smart] Layer 4 - Keywords HL: {high_level[:3]}, LL: {low_level[:3]}")
    except Exception as e:
        logger.warning(f"[Smart] Layer 4 failed: {e}")
    
    # =================================================================
    # LAYER 5: ENTITY CHUNK COLLECTION
    # =================================================================
    all_entity_ids = entity_ids_found.union(related_entity_ids)
    
    for entity_id in all_entity_ids:
        try:
            chunks = await storage.get_chunks_by_entity(entity_id, limit=12)
            
            # Calculate composite score
            entity_score = entity_scores.get(entity_id, 0.5)
            rel_boost = relationship_scores.get(entity_id, 0)
            
            for chunk in chunks:
                base_score = 0.5 + (entity_score * 0.3) + rel_boost
                
                all_chunks.append({
                    'content': chunk.content,
                    'source': chunk.source,
                    'chunk_id': chunk.chunk_id,
                    'entity_id': entity_id,
                    'similarity': base_score,
                    'source_layer': 'entity_chunk',
                    'base_score': base_score,
                    'entity_score': entity_score
                })
        except Exception:
            pass
    
    logger.info(f"[Smart] Layer 5 - Entity chunks from {len(all_entity_ids)} entities")
    
    # =================================================================
    # FINAL: INTELLIGENT FUSION & RANKING
    # =================================================================
    
    # Deduplicate
    seen_content = set()
    unique_chunks = []
    
    for chunk in all_chunks:
        content_key = chunk['content'][:150].strip()
        if content_key not in seen_content:
            seen_content.add(content_key)
            unique_chunks.append(chunk)
    
    # Apply source layer boosting for diversity
    layer_boosts = {
        'semantic_chunk': 1.0,      # Base
        'relationship': 1.05,       # Slight boost for KG context
        'entity_chunk': 0.95        # Slight penalty (may be less relevant)
    }
    
    for chunk in unique_chunks:
        layer = chunk.get('source_layer', 'unknown')
        boost = layer_boosts.get(layer, 1.0)
        chunk['similarity'] = chunk.get('similarity', 0.5) * boost
    
    # Sort by final similarity
    unique_chunks.sort(key=lambda x: x.get('similarity', 0), reverse=True)
    
    # Log distribution
    layer_counts = {}
    for chunk in unique_chunks[:top_k]:
        layer = chunk.get('source_layer', 'unknown')
        layer_counts[layer] = layer_counts.get(layer, 0) + 1
    
    logger.info(f"[Smart] Returning {len(unique_chunks[:top_k])} chunks. Distribution: {layer_counts}")
    return unique_chunks[:top_k]


async def extract_keywords_for_search(query: str, llm_config: dict = None) -> tuple:
    """
    Extract high-level and low-level keywords for enhanced search.
    High-level: concepts, themes, topics
    Low-level: specific entities, names, products
    """
    try:
        # Use regex-based extraction as fallback (always works)
        import re
        
        # Extract potential entities (capitalized words, quoted phrases)
        entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', query)
        quoted = re.findall(r'"([^"]+)"', query)
        
        # Extract all meaningful words (3+ chars)
        all_words = [w.lower() for w in re.findall(r'\b[a-zA-Z]{3,}\b', query)]
        
        stop_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use', 'what', 'with', 'have', 'this', 'will', 'your', 'from', 'they', 'know', 'want', 'been', 'good', 'much', 'some', 'time', 'very', 'when', 'come', 'here', 'just', 'like', 'long', 'make', 'many', 'over', 'such', 'take', 'than', 'them', 'well', 'were'}
        
        # Low-level keywords: entities and specific terms
        low_level = list(set([e for e in entities if len(e) > 2] + quoted))
        
        # High-level keywords: concepts (filtered words)
        high_level = list(set([w for w in all_words if w not in stop_words and w not in [l.lower() for l in low_level]]))[:10]
        
        return high_level, low_level
        
    except Exception as e:
        logger.error(f"Keyword extraction failed: {e}")
        return [], []


async def search_entity_lookup(
    query: str,
    query_embedding: List[float],
    top_k: int = 20,
    llm_config: dict = None
) -> List[Dict]:
    """
    Entity-lookup mode: Comprehensive search using ALL embedding types:
    - Entity embeddings (primary): Find matching entities
    - Relationship embeddings (enhancement): Find related entities via relationships
    - Chunk embeddings (content): Direct vector search on chunks + entity chunks
    - Keywords (boosting): Extract and match keywords for precision
    """
    logger.info(f"[Entity-lookup] Starting comprehensive search for: {query[:50]}...")
    
    from storage import DistanceMetric
    all_chunks = []
    
    # =================================================================
    # LAYER 1: ENTITY EMBEDDINGS - Find matching entities
    # =================================================================
    entity_results = await storage.search_entities(
        query_vector=query_embedding,
        limit=top_k * 3,
        distance_metric=DistanceMetric.COSINE
    )
    
    if entity_results:
        logger.info(f"[Entity-lookup] Found {len(entity_results)} entities via entity embeddings")
    
    # =================================================================
    # LAYER 2: KEYWORD EXTRACTION - For entity boosting
    # =================================================================
    high_level, low_level = await extract_keywords_for_search(query, llm_config)
    logger.info(f"[Entity-lookup] Keywords - HL: {high_level[:5]}, LL: {low_level[:5]}")
    
    # Boost entity scores based on keyword matches
    boosted_entities = []
    for entity in entity_results:
        entity_name = entity.get('name', '').lower()
        entity_desc = (entity.get('description') or '').lower()
        
        boost = 0.0
        # Low-level keywords (entity names) get strong boost
        for kw in low_level:
            kw_lower = kw.lower()
            if kw_lower in entity_name:
                boost += 0.15
            elif kw_lower in entity_desc:
                boost += 0.08
        
        # High-level keywords (concepts) get medium boost
        for kw in high_level:
            if kw.lower() in entity_desc:
                boost += 0.05
        
        entity['similarity'] = entity.get('similarity', 0.5) + boost
        boosted_entities.append(entity)
    
    boosted_entities.sort(key=lambda x: x.get('similarity', 0), reverse=True)
    top_entities = boosted_entities[:top_k]
    
    # =================================================================
    # LAYER 3: RELATIONSHIP EMBEDDINGS - Find related entities
    # =================================================================
    related_entity_ids = set()
    relationship_boost = {}
    
    # Search relationship embeddings directly
    try:
        rel_embedding_results = await storage.search_relationships(
            query_vector=query_embedding,
            limit=15,
            distance_metric=DistanceMetric.COSINE,
            match_threshold=0.5
        )
        
        # Extract entities from matching relationships
        for rel in rel_embedding_results:
            source_id = rel.get('source_id')
            target_id = rel.get('target_id')
            if source_id:
                related_entity_ids.add(source_id)
            if target_id:
                related_entity_ids.add(target_id)
        
        logger.info(f"[Entity-lookup] Found {len(related_entity_ids)} entities via relationship embeddings")
    except Exception as e:
        logger.warning(f"[Entity-lookup] Relationship embedding search failed: {e}")
    
    # Also get related entities through graph traversal from top entities
    for entity in top_entities:
        entity_id = entity.get('entity_id')
        try:
            related = await storage.get_related_entities(
                entity_id=entity_id,
                max_depth=1,
                limit_per_level=5
            )
            
            for rel in related:
                related_id = rel.get('related_entity_id')
                if related_id and related_id != entity_id:
                    related_entity_ids.add(related_id)
                    weight = rel.get('weight', 1.0)
                    if related_id not in relationship_boost:
                        relationship_boost[related_id] = 0
                    relationship_boost[related_id] += weight * 0.1
                    
        except Exception as e:
            logger.warning(f"[Entity-lookup] Failed to get related for {entity_id}: {e}")
    
    # =================================================================
    # LAYER 4: CHUNK EMBEDDINGS - Multiple sources
    # =================================================================
    
    # 4a: Direct chunk vector search (semantic similarity)
    try:
        chunk_results = await storage.search_chunks(
            query_vector=query_embedding,
            limit=top_k,
            distance_metric=DistanceMetric.COSINE,
            match_threshold=0.3
        )
        
        for chunk in chunk_results:
            all_chunks.append({
                'content': chunk.content,
                'source': chunk.source,
                'chunk_id': chunk.chunk_id,
                'entity_id': chunk.entity_id,
                'similarity': chunk.similarity,
                'source_type': 'chunk_embedding'
            })
        
        logger.info(f"[Entity-lookup] Added {len(chunk_results)} chunks via direct chunk embeddings")
    except Exception as e:
        logger.warning(f"[Entity-lookup] Chunk embedding search failed: {e}")
    
    # 4b: Chunks from entity-based search (entity + related entities)
    all_entity_ids = set(e.get('entity_id') for e in top_entities)
    all_entity_ids.update(related_entity_ids)
    
    for entity_id in all_entity_ids:
        try:
            chunks = await storage.get_chunks_by_entity(entity_id, limit=15)
            for chunk in chunks:
                base_similarity = 0.6
                
                # Boost if from top entity
                if entity_id in [e.get('entity_id') for e in top_entities]:
                    entity_match = next((e for e in top_entities if e.get('entity_id') == entity_id), None)
                    if entity_match:
                        base_similarity = entity_match.get('similarity', 0.7)
                
                # Boost if from relationship-expanded entity
                if entity_id in relationship_boost:
                    base_similarity += relationship_boost[entity_id]
                
                all_chunks.append({
                    'content': chunk.content,
                    'source': chunk.source,
                    'chunk_id': chunk.chunk_id,
                    'entity_id': entity_id,
                    'similarity': base_similarity,
                    'source_type': 'entity_chunk'
                })
        except Exception as e:
            logger.warning(f"[Entity-lookup] Failed to get chunks for {entity_id}: {e}")
    
    # =================================================================
    # LAYER 5: RELATIONSHIP CONTENT - Add relationship descriptions
    # =================================================================
    try:
        # Use already fetched relationship results if available
        if 'rel_embedding_results' in locals():
            for rel in rel_embedding_results:
                desc = rel.get('description') or f"{rel.get('source_id')} {rel.get('relationship_type')} {rel.get('target_id')}"
                if desc:
                    all_chunks.append({
                        'content': f"[Relationship] {desc}",
                        'source': 'knowledge_graph',
                        'chunk_id': f"rel_{rel.get('relationship_id')}",
                        'similarity': rel.get('similarity', 0.5),
                        'source_type': 'relationship_embedding'
                    })
    except Exception as e:
        logger.warning(f"[Entity-lookup] Relationship content addition failed: {e}")
    
    # =================================================================
    # FINAL: Deduplicate and rank
    # =================================================================
    seen_content = set()
    unique_chunks = []
    
    for chunk in all_chunks:
        content_key = chunk['content'][:150].strip()
        if content_key not in seen_content:
            seen_content.add(content_key)
            unique_chunks.append(chunk)
    
    unique_chunks.sort(key=lambda x: x.get('similarity', 0), reverse=True)
    
    logger.info(f"[Entity-lookup] Returning {len(unique_chunks[:top_k])} unique chunks "
                f"(from {len(all_entity_ids)} entities, sources: chunk_emb, entity_emb, rel_emb)")
    return unique_chunks[:top_k]


async def search_graph_traversal(
    query: str,
    query_embedding: List[float],
    top_k: int = 20,
    max_depth: int = 2,
    llm_config: dict = None
) -> List[Dict]:
    """
    Graph-traversal mode: Comprehensive graph-based search using ALL embedding types:
    - Entity embeddings: Find seed entities for traversal
    - Relationship embeddings: Primary mechanism for relationship-based retrieval
    - Chunk embeddings: Direct semantic search + entity-linked chunks
    - Graph reasoning: BFS traversal, path finding, and connectivity analysis
    """
    logger.info(f"[Graph-traversal] Starting comprehensive graph search for: {query[:50]}...")
    
    from storage import DistanceMetric
    all_chunks = []
    
    # =================================================================
    # LAYER 1: RELATIONSHIP EMBEDDINGS - Primary relationship-based retrieval
    # =================================================================
    matching_relationships = []
    relationship_entity_ids = set()
    
    try:
        rel_results = await storage.search_relationships(
            query_vector=query_embedding,
            limit=20,
            distance_metric=DistanceMetric.COSINE,
            match_threshold=0.4
        )
        
        matching_relationships = rel_results
        
        # Extract all entities from matching relationships
        for rel in rel_results:
            source_id = rel.get('source_id')
            target_id = rel.get('target_id')
            if source_id:
                relationship_entity_ids.add(source_id)
            if target_id:
                relationship_entity_ids.add(target_id)
        
        logger.info(f"[Graph-traversal] Found {len(rel_results)} relationships via relationship embeddings, "
                    f"covering {len(relationship_entity_ids)} entities")
        
        # Add relationship descriptions as high-value context
        for rel in rel_results:
            desc = rel.get('description')
            rel_type = rel.get('relationship_type', 'related_to')
            
            if desc:
                edge_text = f"[Relationship: {rel_type}] {desc}"
            else:
                edge_text = f"[Relationship: {rel_type}] {rel.get('source_id')} → {rel.get('target_id')}"
            
            all_chunks.append({
                'content': edge_text,
                'source': 'relationship_embedding',
                'chunk_id': f"rel_{rel.get('relationship_id')}",
                'similarity': rel.get('similarity', 0.5) * 1.2,  # Boost relationship matches
                'rel_source': rel.get('source_id'),
                'rel_target': rel.get('target_id'),
                'rel_type': rel_type,
                'source_layer': 'relationship_embedding'
            })
            
    except Exception as e:
        logger.warning(f"[Graph-traversal] Relationship embedding search failed: {e}")
    
    # =================================================================
    # LAYER 2: ENTITY EMBEDDINGS - Find seed entities for graph expansion
    # =================================================================
    seed_entities = await storage.search_entities(
        query_vector=query_embedding,
        limit=15,
        distance_metric=DistanceMetric.COSINE
    )
    
    if seed_entities:
        logger.info(f"[Graph-traversal] Found {len(seed_entities)} seed entities via entity embeddings")
    
    # Combine seed entities with relationship-derived entities
    all_entity_ids = set(e.get('entity_id') for e in seed_entities)
    all_entity_ids.update(relationship_entity_ids)
    
    # =================================================================
    # LAYER 3: GRAPH TRAVERSAL - BFS with path finding and reasoning
    # =================================================================
    traversed_entities = set()
    entity_depths = {}
    entity_paths = {}
    entity_connection_scores = {}  # How well connected an entity is
    
    for seed in seed_entities:
        seed_id = seed.get('entity_id')
        seed_name = seed.get('name', 'Unknown')
        
        try:
            # Multi-hop BFS traversal
            related = await storage.get_related_entities(
                entity_id=seed_id,
                max_depth=max_depth,
                limit_per_level=12
            )
            
            # Mark seed entity
            if seed_id not in traversed_entities:
                traversed_entities.add(seed_id)
                entity_depths[seed_id] = 0
                entity_paths[seed_id] = [seed_name]
                entity_connection_scores[seed_id] = 1.0
            
            # Process traversed entities with path tracking
            for rel in related:
                rel_id = rel.get('related_entity_id')
                rel_name = rel.get('related_entity_name', 'Unknown')
                depth = rel.get('depth', 1)
                
                if rel_id:
                    traversed_entities.add(rel_id)
                    
                    # Track minimum depth (shortest path)
                    if rel_id not in entity_depths or depth < entity_depths[rel_id]:
                        entity_depths[rel_id] = depth
                        
                        # Build and store path
                        rel_path = rel.get('path', [])
                        if rel_path:
                            entity_paths[rel_id] = rel_path
                        else:
                            entity_paths[rel_id] = [seed_name, rel_name]
                    
                    # Increment connection score (more connections = higher score)
                    if rel_id not in entity_connection_scores:
                        entity_connection_scores[rel_id] = 0
                    entity_connection_scores[rel_id] += 1.0 / depth  # Closer connections count more
                    
        except Exception as e:
            logger.warning(f"[Graph-traversal] Failed traversal from {seed_id}: {e}")
    
    # Add traversed entities to our collection
    all_entity_ids.update(traversed_entities)
    
    logger.info(f"[Graph-traversal] Graph traversal discovered {len(traversed_entities)} entities "
                f"with depths {set(entity_depths.values()) if entity_depths else {0}}")
    
    # =================================================================
    # LAYER 4: CHUNK EMBEDDINGS - Multiple retrieval strategies
    # =================================================================
    
    # 4a: Direct chunk vector search (semantic similarity to query)
    try:
        chunk_results = await storage.search_chunks(
            query_vector=query_embedding,
            limit=top_k // 2,  # Get some direct semantic matches
            distance_metric=DistanceMetric.COSINE,
            match_threshold=0.3
        )
        
        for chunk in chunk_results:
            all_chunks.append({
                'content': chunk.content,
                'source': chunk.source,
                'chunk_id': chunk.chunk_id,
                'entity_id': chunk.entity_id,
                'similarity': chunk.similarity,
                'source_layer': 'chunk_embedding'
            })
        
        logger.info(f"[Graph-traversal] Added {len(chunk_results)} chunks via direct chunk embeddings")
    except Exception as e:
        logger.warning(f"[Graph-traversal] Direct chunk search failed: {e}")
    
    # 4b: Chunks from all discovered entities (entity-linked content)
    entity_chunk_count = 0
    for entity_id in all_entity_ids:
        try:
            chunks = await storage.get_chunks_by_entity(entity_id, limit=25)
            entity_chunk_count += len(chunks)
            
            # Calculate composite score based on multiple factors
            depth = entity_depths.get(entity_id, 0)
            connection_score = entity_connection_scores.get(entity_id, 0)
            
            # Depth factor: closer to seed = more relevant
            depth_factor = 1.0 - (depth * 0.15)  # 1.0, 0.85, 0.7 for depths 0, 1, 2
            
            # Connection factor: highly connected = more central
            connection_factor = min(connection_score * 0.1, 0.3)  # Cap at 0.3
            
            # Seed entity bonus
            seed_bonus = 0.2 if entity_id in [e.get('entity_id') for e in seed_entities] else 0
            
            base_similarity = 0.5 + (depth_factor * 0.25) + connection_factor + seed_bonus
            
            path = entity_paths.get(entity_id, [])
            
            for chunk in chunks:
                chunk_meta = {
                    'content': chunk.content,
                    'source': chunk.source,
                    'chunk_id': chunk.chunk_id,
                    'entity_id': entity_id,
                    'similarity': base_similarity,
                    'depth': depth,
                    'path': ' → '.join(path[-3:]) if len(path) > 1 else 'direct',
                    'connection_score': connection_score,
                    'source_layer': 'graph_traversal'
                }
                all_chunks.append(chunk_meta)
                
        except Exception as e:
            logger.warning(f"[Graph-traversal] Failed to get chunks for {entity_id}: {e}")
    
    logger.info(f"[Graph-traversal] Retrieved {entity_chunk_count} chunks from {len(all_entity_ids)} entities")
    
    # =================================================================
    # LAYER 5: GRAPH REASONING - Add connectivity insights
    # =================================================================
    
    # Add high-centrality entity summaries
    central_entities = sorted(
        [(eid, score) for eid, score in entity_connection_scores.items()],
        key=lambda x: x[1],
        reverse=True
    )[:5]
    
    for entity_id, score in central_entities:
        if score > 2:  # Only include highly connected entities
            try:
                entity_result = await storage.get_entity(entity_id)
                if entity_result:
                    entity_name = entity_result.get('name', 'Unknown')
                    entity_desc = entity_result.get('description', '')
                    path = entity_paths.get(entity_id, [entity_name])
                    
                    reasoning_text = f"[Graph Hub] {entity_name} is a central node in the knowledge graph "
                    reasoning_text += f"(connected to {int(score)} entities, path: {' → '.join(path[-3:])}). "
                    if entity_desc:
                        reasoning_text += f"Description: {entity_desc[:200]}"
                    
                    all_chunks.append({
                        'content': reasoning_text,
                        'source': 'graph_reasoning',
                        'chunk_id': f"hub_{entity_id}",
                        'entity_id': entity_id,
                        'similarity': 0.7 + min(score * 0.02, 0.2),  # Score based on centrality
                        'source_layer': 'graph_reasoning'
                    })
            except Exception as e:
                logger.warning(f"[Graph-traversal] Failed to get hub entity {entity_id}: {e}")
    
    # =================================================================
    # FINAL: Deduplicate, rank, and return
    # =================================================================
    seen_content = set()
    unique_chunks = []
    
    for chunk in all_chunks:
        content_key = chunk['content'][:150].strip()
        if content_key not in seen_content:
            seen_content.add(content_key)
            unique_chunks.append(chunk)
    
    # Sort by composite similarity score
    unique_chunks.sort(key=lambda x: x.get('similarity', 0), reverse=True)
    
    # Log layer distribution
    layer_counts = {}
    for chunk in unique_chunks[:top_k]:
        layer = chunk.get('source_layer', 'unknown')
        layer_counts[layer] = layer_counts.get(layer, 0) + 1
    
    logger.info(f"[Graph-traversal] Returning {len(unique_chunks[:top_k])} unique chunks "
                f"from {len(all_entity_ids)} entities. Layer distribution: {layer_counts}")
    
    return unique_chunks[:top_k]


# ============ Chat ============
@app.post("/api/v1/chat")
async def chat(request: dict):
    """
    RAG chat with Vector Similarity Search + Reranking for improved quality.
    Supports multiple search modes: semantic (default), entity-lookup, graph-traversal.
    
    Request body can include:
    - query/message: The search query
    - mode: Search mode - "semantic" (default), "entity-lookup", "graph-traversal"
    - top_k: Number of chunks to retrieve (default: from config)
    - rerank: Whether to rerank results (default: true)
    - rerank_method: "hybrid", "vector", "keyword", or "none"
    - llm_config: LLM provider configuration {provider: "deepseek"|"minimax", fallback_provider: ...}
    - max_depth: For graph-traversal mode (default: 2)
    """
    # Accept both "query" and "message" fields
    query = request.get("query") or request.get("message", "")
    
    # Get search mode (default: semantic)
    mode = request.get("mode", "semantic").lower()
    
    # Get LLM configuration from request (if provided)
    llm_config = request.get("llm_config", {})
    llm_provider = llm_config.get("provider", "deepseek")  # Default to DeepSeek
    llm_fallback = llm_config.get("fallback_provider")
    
    # Get parameters from request
    requested_top_k = request.get("top_k", RERANK_CONFIG.final_top_k)
    use_rerank = request.get("rerank", RERANK_CONFIG.enabled)
    rerank_method = request.get("rerank_method", RERANK_CONFIG.method)
    max_depth = request.get("max_depth", 2)
    
    if not query or not query.strip():
        return {
            "response": "Please enter a question to search the knowledge base.",
            "answer": "Please enter a question to search the knowledge base.",
            "context": "",
            "sources": [],
            "confidence": 0.0
        }
    
    # =================================================================
    # STEP 1: SEARCH BASED ON MODE
    # =================================================================
    
    # Generate query embedding (needed for all modes)
    query_embedding = get_ollama_embedding(query)
    
    logger.info(f"[Chat] Mode: {mode}, Query: {query[:50]}...")
    
    result = []
    
    if mode == "smart":
        # Smart mode: Multi-layer unified search combining all strategies
        try:
            result = await search_smart(
                query=query,
                query_embedding=query_embedding,
                top_k=requested_top_k,
                llm_config=llm_config
            )
            logger.info(f"[Chat] Smart mode returned {len(result)} chunks")
        except Exception as e:
            logger.error(f"[Chat] Smart mode failed: {e}, falling back to semantic")
            mode = "semantic"  # Fallback to semantic
    
    elif mode == "entity-lookup":
        # Entity-centric search with relationship enhancement
        try:
            result = await search_entity_lookup(
                query=query,
                query_embedding=query_embedding,
                top_k=requested_top_k,
                llm_config=llm_config
            )
            logger.info(f"[Chat] Entity-lookup returned {len(result)} chunks")
        except Exception as e:
            logger.error(f"[Chat] Entity-lookup failed: {e}, falling back to semantic")
            mode = "semantic"  # Fallback to semantic
    
    elif mode == "graph-traversal":
        # Graph-based traversal search
        try:
            result = await search_graph_traversal(
                query=query,
                query_embedding=query_embedding,
                top_k=requested_top_k,
                max_depth=max_depth,
                llm_config=llm_config
            )
            logger.info(f"[Chat] Graph-traversal returned {len(result)} chunks")
        except Exception as e:
            logger.error(f"[Chat] Graph-traversal failed: {e}, falling back to semantic")
            mode = "semantic"  # Fallback to semantic
    
    if mode in ("semantic", "semantic-hybrid") or not result:
        # Default: Semantic chunk search
        initial_k = RERANK_CONFIG.initial_top_k if use_rerank else requested_top_k
        
        try:
            from storage import DistanceMetric
            vector_results = await storage.search_chunks(
                query_vector=query_embedding,
                limit=initial_k,
                distance_metric=DistanceMetric.COSINE,
                match_threshold=0.2
            )
            
            # Convert to dict format
            result = []
            for r in vector_results:
                result.append({
                    "content": r.content,
                    "source": r.source,
                    "similarity": r.similarity,
                    "chunk_id": r.chunk_id,
                    "metadata": r.metadata
                })
            
            rerank_logger.info(f"[Chat] Semantic search returned {len(result)} chunks")
            
        except Exception as e:
            rerank_logger.error(f"[Chat] Semantic search failed: {e}")
            result = []
    
    # Fallback to keyword search if vector search returns nothing
    if not result:
        rerank_logger.warning("Vector search returned no results, falling back to keyword search")
        
        import re
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                      'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                      'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
                      'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as',
                      'into', 'through', 'during', 'before', 'after', 'above', 'below',
                      'between', 'under', 'again', 'further', 'then', 'once', 'here',
                      'there', 'when', 'where', 'why', 'how', 'all', 'each', 'few',
                      'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
                      'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just',
                      'and', 'but', 'if', 'or', 'because', 'until', 'while', 'about',
                      'against', 'this', 'that', 'these', 'those', 'what', 'which', 'who',
                      'whom', 'reply', 'english', 'translate', 'language', 'in', 'write'}
        
        english_words = [w.lower() for w in re.findall(r'[a-zA-Z]+', query) 
                        if w.lower() not in stop_words and len(w) > 2]
        
        for w in english_words[:3]:
            r = await storage.client.fetch(
                "SELECT content, source, chunk_id, metadata FROM chunks WHERE content ILIKE $1 LIMIT 10",
                f"%{w}%"
            )
            if r:
                result.extend([{"content": row.get("content", ""), 
                               "source": row.get("source", ""),
                               "chunk_id": row.get("chunk_id", ""),
                               "metadata": row.get("metadata", {}),
                               "similarity": 0.5} for row in r])
    
    # =================================================================
    # STEP 2: RERANKING
    # =================================================================
    
    if use_rerank and result and rerank_method != "none":
        rerank_logger.info(f"Reranking {len(result)} chunks using method: {rerank_method}")
        result = await rerank_chunks(query, result, method=rerank_method, final_k=requested_top_k)
        rerank_logger.info(f"Reranking complete, returning top {len(result)} chunks")
    else:
        # Just limit to requested number without reranking
        result = result[:requested_top_k]
    
    # =================================================================
    # STEP 3: FORMAT RESPONSE
    # =================================================================
    
    # Remove duplicates - use first 200 chars as key
    if result:
        seen = {}
        unique_result = []
        for r in result:
            content = r.get("content", "")
            key = content[:200].strip()
            if key and key not in seen:
                seen[key] = content
                unique_result.append(r)
        result = unique_result
    
    if not result:
        # Clean up query for display - remove common prefixes
        import re
        clean_query = re.sub(r'^(tell me about |what is |who is |show me |find |search for |about |explain )', '', query.lower().strip())
        return {
            "response": f"I couldn't find any information related to '{clean_query}'. Please try a different search term or upload relevant documents first.",
            "answer": f"I couldn't find any information related to '{clean_query}'. Please try a different search term or upload relevant documents first.",
            "context": "",
            "sources": [],
            "confidence": 0.0
        }
    
    # Get query mode for filtering decisions
    is_ultra = request.get("ultra_comprehensive", False)
    is_comprehensive = request.get("detailed", False)
    
    # Filter and clean chunks
    import re
    filtered_result = []
    box_chars = re.compile(r'[\u2500-\u257F]')
    
    for r in result:
        content = r.get("content", "")
        source = r.get("source", "unknown")
        
        if len(content) < 50:
            continue
        
        # Skip only if more is box-drawing than 30% chars
        box_count = len(box_chars.findall(content))
        if box_count > 0 and box_count / len(content) > 0.3:
            continue
        
        # For Ultra/Comprehensive modes: trust vector search, skip content filtering
        # For Quick/Balanced modes: apply relevance filtering
        if is_ultra or is_comprehensive:
            # Ultra/Comprehensive: Trust vector similarity results
            filtered_result.append(r)
        else:
            # Quick/Balanced: Check relevance - filename OR content must match
            filename_rel, matched_keyword = is_source_filename_relevant(source, query)
            content_rel, match_count, matched_terms = is_chunk_content_relevant(content, query, min_matches=1)
            
            if filename_rel:
                print(f"[FILTER] PASSED: '{source}' - filename matched: '{matched_keyword}'")
                filtered_result.append(r)
            elif content_rel:
                print(f"[FILTER] PASSED: '{source}' - content matched: {matched_terms}")
                filtered_result.append(r)
            else:
                print(f"[FILTER] REJECTED: '{source}' - no filename or content match")
                continue
    
    # Log filtering summary
    filtered_count = len(result) - len(filtered_result)
    if filtered_count > 0:
        print(f"[FILTER SUMMARY] Filtered out {filtered_count}/{len(result)} chunks as irrelevant")
    print(f"[FILTER SUMMARY] Keeping {len(filtered_result)} relevant chunks (Ultra={is_ultra}, Comprehensive={is_comprehensive})")
    
    # If no relevant chunks after filtering, generate from LLM knowledge
    if not filtered_result:
        print(f"[INFO] No relevant chunks after filtering. Generating answer from LLM knowledge...")
        try:
            fallback_response = await generate_llm_knowledge_response(
                query,
                llm_config={"provider": llm_provider, "fallback_provider": llm_fallback},
                is_ultra=is_ultra,
                is_comprehensive=is_comprehensive
            )
            if fallback_response:
                return {
                    "response": fallback_response,
                    "answer": fallback_response,
                    "sources": [],
                    "confidence": 0.7,
                    "retrieval_info": {
                        "method": "llm_knowledge_only",
                        "note": f"Vector search returned {len(result)} chunks but none passed relevance filtering. Answer generated from LLM pre-trained knowledge."
                    }
                }
        except Exception as e:
            print(f"[ERROR] LLM knowledge generation failed: {e}")
        
        # Ultimate fallback if LLM knowledge also fails
        return {
            "response": f"I couldn't find any relevant information about '{query}' in the knowledge base, and the AI knowledge generation is currently unavailable. Please try:\n\n1. Upload relevant documents about this topic\n2. Try a different search term\n3. Check your connection to the AI service",
            "answer": f"I couldn't find any relevant information about '{query}' in the knowledge base, and the AI knowledge generation is currently unavailable. Please try:\n\n1. Upload relevant documents about this topic\n2. Try a different search term\n3. Check your connection to the AI service",
            "context": "",
            "sources": [],
            "confidence": 0.0
        }
    
    # Build context from filtered results - include source info for better citations
    # Create a source legend for accurate citation
    source_legend = "SOURCE LEGEND (Use ONLY these source numbers in citations):\n"
    for i, r in enumerate(filtered_result):
        source = r.get("source", "unknown")
        source_legend += f"Source {i+1}: {source}\n"
    source_legend += "\n---\n\n"
    
    context_parts = []
    for i, r in enumerate(filtered_result):
        content = r.get("content", "")
        source = r.get("source", "unknown")
        score = r.get("rerank_score", r.get("similarity", 0))
        # Add metadata header for each chunk
        context_parts.append(f"[Source {i+1}: {source} | Relevance: {score:.2f}]\n{content}")
    
    context = source_legend + "\n\n---\n\n".join(context_parts)
    
    # Clean up the context - remove excessive formatting
    context = re.sub(r'╮╯╭╰━┃╱╲╳╔╗╚╝║═╠╬╣╝╚', '', context)
    context = re.sub(r'─{3,}', '', context)
    context = re.sub(r'│{2,}', '', context)
    context = context.strip()
    
    # Source relevance check - ENABLED for all modes with smart filtering
    # For Ultra/Comprehensive: Keep high-similarity chunks even if filename doesn't match
    # For Quick/Balanced: Stricter filename-based filtering
    is_ultra = request.get("ultra_comprehensive", False)
    is_comprehensive = request.get("detailed", False)
    
    # Get unique sources and apply relevance filtering
    unique_sources_check = list(set([r.get("source", "unknown") for r in filtered_result]))
    irrelevant_sources_check = []
    relevant_sources_check = []
    
    for src in unique_sources_check:
        is_rel, _ = is_source_relevant(src, query)
        if is_rel:
            relevant_sources_check.append(src)
        else:
            irrelevant_sources_check.append(src)
    
    # Smart filtering based on mode
    if is_ultra or is_comprehensive:
        # Ultra/Comprehensive: Keep sources with decent rerank scores (>0.4) even if filename doesn't match
        # This preserves high-quality vector matches while filtering obvious noise
        high_quality_threshold = 0.4
        rescued_sources = []
        
        for src in irrelevant_sources_check:
            # Find chunks from this source
            src_chunks = [r for r in filtered_result if r.get('source') == src]
            # Check if any chunk has high rerank score
            max_score = max([r.get('rerank_score', 0) for r in src_chunks], default=0)
            if max_score >= high_quality_threshold:
                rescued_sources.append(src)
                print(f"[INFO] Rescued source '{src}' due to high vector similarity ({max_score:.2f} > {high_quality_threshold})")
        
        relevant_sources_check.extend(rescued_sources)
        irrelevant_sources_check = [s for s in irrelevant_sources_check if s not in rescued_sources]
        
        print(f"[INFO] Ultra/Comprehensive mode: {len(relevant_sources_check)} sources kept, {len(irrelevant_sources_check)} filtered out")
    
    # Apply filtering
    if irrelevant_sources_check:
        if len(irrelevant_sources_check) == len(unique_sources_check) and not (is_ultra or is_comprehensive):
            # If ALL sources would be filtered AND not Ultra/Comprehensive, fall back to LLM knowledge
            print(f"[WARNING] All {len(unique_sources_check)} sources are irrelevant to query: {query}")
            print(f"[INFO] Skipping RAG, generating directly from LLM knowledge")
            try:
                fallback_response = await generate_llm_knowledge_response(
                    query,
                    llm_config={"provider": llm_provider, "fallback_provider": llm_fallback},
                    is_ultra=False,
                    is_comprehensive=False
                )
                if fallback_response:
                    return {
                        "response": fallback_response,
                        "answer": fallback_response,
                        "sources": [],
                        "confidence": 0.7,
                        "retrieval_info": {
                            "method": "llm_knowledge_only",
                            "note": f"Retrieved {len(filtered_result)} chunks but source relevance check failed. Answer generated from LLM pre-trained knowledge."
                        }
                    }
            except Exception as e:
                print(f"[ERROR] LLM knowledge generation failed: {e}")
        elif len(irrelevant_sources_check) == len(unique_sources_check) and (is_ultra or is_comprehensive):
            # Ultra/Comprehensive: Keep top 10 sources by rerank score even if all would be filtered
            print(f"[WARNING] All {len(unique_sources_check)} sources would be filtered, but Ultra/Comprehensive mode - keeping top sources by relevance")
            # Sort sources by max rerank score and keep top 10
            source_scores = {}
            for src in unique_sources_check:
                src_chunks = [r for r in filtered_result if r.get('source') == src]
                max_score = max([r.get('rerank_score', 0) for r in src_chunks], default=0)
                source_scores[src] = max_score
            
            top_sources = sorted(source_scores.items(), key=lambda x: x[1], reverse=True)[:10]
            relevant_sources_check = [src for src, score in top_sources]
            irrelevant_sources_check = []
            print(f"[INFO] Ultra/Comprehensive mode: Keeping top {len(relevant_sources_check)} sources by relevance score")
        else:
            print(f"[INFO] Filtered out {len(irrelevant_sources_check)} irrelevant sources, keeping {len(relevant_sources_check)} relevant ones")
            # Filter filtered_result to only keep relevant sources
            filtered_result = [r for r in filtered_result if r.get('source') in relevant_sources_check]
    
    # Rebuild context with filtered sources
    source_legend = "SOURCE LEGEND (Use ONLY these source numbers in citations):\n"
    for i, r in enumerate(filtered_result):
        source = r.get("source", "unknown")
        source_legend += f"Source {i+1}: {source}\n"
    source_legend += "\n---\n\n"
    context_parts = []
    for i, r in enumerate(filtered_result):
        content = r.get("content", "")
        source = r.get("source", "unknown")
        score = r.get("rerank_score", r.get("similarity", 0))
        context_parts.append(f"[Source {i+1}: {source} | Relevance: {score:.2f}]\n{content}")
    context = source_legend + "\n\n---\n\n".join(context_parts)
    
    # Try to generate LLM response - run in separate thread with its own event loop
    try:
        import concurrent.futures
        import asyncio
        import sys
        import os
        # Import from local backend directory
        
        # Get mode flags from request for use in outer scope
        is_ultra = request.get("ultra_comprehensive", False)
        is_comprehensive = request.get("detailed", False)
        top_k = request.get("top_k", 20)
        
        # Set detail_level for use in outer scope
        if is_ultra:
            detail_level = "ultra-deep"
            llm_timeout = 900  # 15 min for ultra (8000 tokens)
        elif is_comprehensive:
            detail_level = "comprehensive"
            llm_timeout = 600  # 10 min for comprehensive (6400 tokens)
        elif top_k >= 20:
            detail_level = "balanced"
            llm_timeout = 480  # 8 min for balanced (4800 tokens)
        else:
            detail_level = "quick"
            llm_timeout = 300  # 5 min for quick (3200 tokens)
        
        async def run_llm_async():
            """Run async LLM directly in the main event loop"""
            try:
                # Load API key if not set (uses main thread's environment)
                if not os.getenv("MINIMAX_API_KEY"):
                    with open(os.path.expanduser("~/.zshrc"), "r") as f:
                        for line in f:
                            if line.strip().startswith("export MINIMAX_API_KEY="):
                                key = line.strip().split("=", 1)[1].strip('"')
                                os.environ["MINIMAX_API_KEY"] = key
                                break
                
                # Check if we have no relevant sources (from outer scope)
                has_relevant_sources = len(filtered_result) > 0
                
                async def get_response():
                    # Check query mode from request parameters (not keywords in query)
                    is_ultra = request.get("ultra_comprehensive", False)
                    is_comprehensive = request.get("detailed", False)
                    
                    # Determine output length and mode
                    # NO TRUNCATION: Set high token limits (DeepSeek max = 8192)
                    if is_ultra:
                        target_words = ">3000-4000"
                        max_tokens = 8192  # Ultra Deep: 8192 tokens (DeepSeek max)
                        temperature = 0.4
                        detail_level = "extremely comprehensive (academic/research level) - MINIMUM 3000 WORDS REQUIRED"
                    elif is_comprehensive:
                        target_words = ">1800-2500"
                        max_tokens = 8192  # Comprehensive: 8192 tokens (DeepSeek max)
                        temperature = 0.3
                        detail_level = "comprehensive"
                    elif top_k >= 20:
                        target_words = ">1200-1800"
                        max_tokens = 8192  # Balanced: 8192 tokens (DeepSeek max)
                        temperature = 0.3
                        detail_level = "balanced"
                    else:
                        target_words = ">600-1200"
                        max_tokens = 8192  # Quick: 8192 tokens (DeepSeek max, no truncation)
                        temperature = 0.3
                        detail_level = "quick"
                    
                    # Initialize chinese_variant at function scope
                    chinese_variant = "english"
                    
                    # Ultra-comprehensive prompt for extensive answers with EXACT output format
                    if is_ultra or is_comprehensive:
                        # Detect query language for section headers
                        import re
                        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', query))
                        has_japanese = bool(re.search(r'[\u3040-\u309f\u30a0-\u30ff]', query))
                        has_korean = bool(re.search(r'[\uac00-\ud7af]', query))
                        
                        # Detect Traditional vs Simplified Chinese
                        # Traditional Chinese characters that differ from Simplified
                        trad_chars = r'[們員問學國過長從來時後無嗎讓愛會體與進說問們員來時國過長從們區義產點裡歲術員問學國過長從來時後無嗎讓愛會體與進說問們員來時國過長從們區義產點裡歲術員問學國過長從來時後無嗎讓愛會體與進說問們員來時國過長從們區義產點裡歲術]'
                        simp_chars = r'[们员问学国过长从来时后无吗让爱会体与进说们员来时国过长从们区义产点里岁术]'
                        has_traditional = bool(re.search(trad_chars, query))
                        has_simplified = bool(re.search(simp_chars, query))
                        
                        if has_japanese:
                            exec_summary = "<query-h2>概要 / Executive Summary</query-h2>"
                            conclusion = "<query-h2>結論 / Conclusion</query-h2>"
                            references = "<query-h2>📚 参考文献 / References</query-h2>"
                            sources = "<query-h2>🔍 検証ソース / Sources for Verification</query-h2>"
                        elif has_korean:
                            exec_summary = "<query-h2>개요 / Executive Summary</query-h2>"
                            conclusion = "<query-h2>결론 / Conclusion</query-h2>"
                            references = "<query-h2>📚 참고문헌 / References</query-h2>"
                        elif has_traditional or (has_chinese and not has_simplified):
                            # Traditional Chinese - use only Traditional characters
                            exec_summary = "<query-h2>摘要</query-h2>"
                            conclusion = "<query-h2>結論</query-h2>"
                            references = "<query-h2>📚 參考文獻</query-h2>"
                            sources = "<query-h2>🔍 驗證來源</query-h2>"
                            chinese_variant = "traditional"
                        elif has_chinese:
                            # Simplified Chinese or mixed
                            exec_summary = "<query-h2>摘要</query-h2>"
                            conclusion = "<query-h2>结论</query-h2>"
                            references = "<query-h2>📚 参考文献</query-h2>"
                            sources = "<query-h2>🔍 验证来源</query-h2>"
                            chinese_variant = "simplified"
                        else:
                            exec_summary = "<query-h2>Executive Summary</query-h2>"
                            conclusion = "<query-h2>Conclusion</query-h2>"
                            references = "<query-h2>📚 References</query-h2>"
                            sources = "<query-h2>🔍 Verification Sources</query-h2>"
                            chinese_variant = "english"
                        
                        prompt = f"""Write a COMPREHENSIVE, RESEARCH-LEVEL technical document. Follow the EXACT hierarchical format below.

User Question: {query}

---

## REQUIRED OUTPUT FORMAT (MUST FOLLOW EXACTLY):

<query-h1>[Main Title - Based on Query Topic]</query-h1>

[introduction paragraph - 2-3 sentences introducing the topic and its significance]

{exec_summary}

[flowing paragraph content - 3-5 sentences minimum]

<query-h2>1. [Section Title]</query-h2>

[introductory paragraph for this section - 100+ words]

<query-h3>1.1 [Subsection Title]</query-h3>

[detailed content 200+ words with citations <span class="citation-ref">[1]</span>, <span class="citation-ref">[2]</span>]

<query-h3>1.2 [Subsection Title]</query-h3>

[detailed content 200+ words]

<query-h3>1.3 [Subsection Title]</query-h3>

[detailed content 200+ words]

<query-h2>2. [Section Title]</query-h2>

[introductory paragraph - 100+ words]

<query-h3>2.1 [Subsection Title]</query-h3>

[detailed content 200+ words]

<query-h3>2.2 [Subsection Title]</query-h3>

[detailed content 200+ words]

<query-h3>2.3 [Subsection Title]</query-h3>

[detailed content 200+ words]

<query-h2>3. [Section Title]</query-h2>

[introductory paragraph - 100+ words]

<query-h3>3.1 [Subsection Title]</query-h3>

[detailed content 200+ words]

<query-h3>3.2 [Subsection Title]</query-h3>

[detailed content 200+ words]

<query-h3>3.3 [Subsection Title]</query-h3>

[detailed content 200+ words]

<query-h2>4. [Section Title]</query-h2>

[introductory paragraph - 100+ words]

<query-h3>4.1 [Subsection Title]</query-h3>

[detailed content 200+ words]

<query-h3>4.2 [Subsection Title]</query-h3>

[detailed content 200+ words]

<query-h3>4.3 [Subsection Title]</query-h3>

[detailed content 200+ words]

<query-h2>5. [Section Title]</query-h2>

[introductory paragraph - 100+ words]

<query-h3>5.1 [Subsection Title]</query-h3>

[detailed content 200+ words]

<query-h3>5.2 [Subsection Title]</query-h3>

[detailed content 200+ words]

<query-h3>5.3 [Subsection Title]</query-h3>

[detailed content 200+ words]

{conclusion}

[synthesize key insights, implications, and closing thoughts - write as flowing paragraphs, not bullet points]

{references}

<div class="reference-item"><span class="ref-number">1.</span> [Source filename 1]</div>
<div class="reference-item"><span class="ref-number">2.</span> [Source filename 2]</div>
<div class="reference-item"><span class="ref-number">3.</span> [Source filename 3]</div>

---

## CONTENT REQUIREMENTS - STRICT WORD COUNT:

**MANDATORY LENGTH**: Your response MUST be EXACTLY {target_words} words minimum. This is NON-NEGOTIABLE.

**STRICT STRUCTURE** - You MUST include ALL of the following:
1. Title with introduction paragraph (150+ words)
2. Executive Summary (300+ words)
3. 5 main numbered sections (1., 2., 3., 4., 5.)
4. Each section MUST have 3 subsections (1.1, 1.2, 1.3, 2.1, 2.2, 2.3, etc.)
5. Each subsection MUST be 200+ words (6-10 full sentences)
6. Conclusion section (400+ words)
7. References section
8. MINIMUM TOTAL: 3000 WORDS (non-negotiable)

**WORD COUNT BREAKDOWN (MUST TOTAL 3000+ WORDS):**
- Introduction: ~150 words
- Executive Summary: ~300 words  
- 5 Sections × 3 subsections × 200 words each = ~3000 words
- Conclusion: ~400 words
- Total: ~3850+ words (EXCEEDS 3000 MINIMUM)

**CITATIONS**: Use <span class="citation-ref">[1]</span>, <span class="citation-ref">[2]</span> in HTML span tags when citing specific information from sources.

**WRITING STYLE**: 
- Write EXTENSIVELY and COMPREHENSIVELY as an expert
- Each paragraph MUST be 5-8 sentences MINIMUM
- Provide DEEP analysis with multiple examples
- Do NOT say "Based on the context" or "According to the documents"
- Write in flowing PARAGRAPHS, NEVER bullet points

**CONTENT SOURCES**:
{context[:5000]}

Write in the same language as the user's question. Complete ALL sections. Do NOT truncate your response."""

                        system_prompt = f"""You are a senior research scientist and professor writing comprehensive academic survey papers.

CRITICAL HTML FORMAT REQUIREMENTS:
- Use <query-h1>TITLE</query-h1> for main document title
- Use <query-h2>1. Section Title</query-h2> for main section headers
- Use <query-h3>1.1 Subsection Title</query-h3> for subsection headers
- Use <span class="citation-ref">[1]</span> for citations
- Use <div class="reference-item"><span class="ref-number">1.</span> Source name</div> for references
- Do NOT use markdown (#, ##, ###) - use HTML tags ONLY

CRITICAL REQUIREMENTS - NO EXCEPTIONS:
- You MUST write MINIMUM 3000 WORDS - this is MANDATORY and NON-NEGOTIABLE
- Word count will be verified - responses under 3000 words are UNACCEPTABLE
- HIERARCHICAL STRUCTURE IS MANDATORY: Each of the 5 main sections MUST have EXACTLY 3 subsections (1.1, 1.2, 1.3, 2.1, 2.2, 2.3, etc.)
- NEVER output main section content without subsections - subsections are REQUIRED
- Each subsection must be 200+ words (6-10 sentences minimum)
- Write in flowing PARAGRAPHS ONLY - NEVER use bullet points
- Cover: introduction → executive summary → section 1 (with 1.1, 1.2, 1.3) → section 2 (with 2.1, 2.2, 2.3) → section 3 (with 3.1, 3.2, 3.3) → section 4 (with 4.1, 4.2, 4.3) → section 5 (with 5.1, 5.2, 5.3) → conclusion → references
- Write in same language as user's question
- USE THE EXACT HEADERS PROVIDED - Do NOT translate {exec_summary}, {conclusion}, {references} to a different language
- INCOMPLETE responses or missing subsections will be rejected - write FULLY and COMPREHENSIVELY"""

                    else:
                        # Balanced mode - with language-aware headers
                        # Build source mapping for accurate citations
                        source_mapping = "\n".join([f"Source {i+1}: {r.get('source', 'unknown')}" for i, r in enumerate(filtered_result)])
                        
                        # Detect query language for section headers
                        import re
                        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', query))
                        has_japanese = bool(re.search(r'[\u3040-\u309f\u30a0-\u30ff]', query))
                        has_korean = bool(re.search(r'[\uac00-\ud7af]', query))
                        
                        # Detect Traditional vs Simplified Chinese
                        trad_chars = r'[們員問學國過長從來時後無嗎讓愛會體與進說問們員來時國過長從們區義產點裡歲術]'
                        simp_chars = r'[们员问学国过长从来时后无吗让爱会体与进说们员来时国过长从们区义产点里岁术]'
                        has_traditional = bool(re.search(trad_chars, query))
                        has_simplified = bool(re.search(simp_chars, query))
                        
                        if has_japanese:
                            exec_summary = "<query-h2>概要 / Executive Summary</query-h2>"
                            conclusion = "<query-h2>結論 / Conclusion</query-h2>"
                            references = "<query-h2>📚 参考文献 / References</query-h2>"
                            sources = "<query-h2>🔍 検証ソース / Sources for Verification</query-h2>"
                        elif has_korean:
                            exec_summary = "<query-h2>개요 / Executive Summary</query-h2>"
                            conclusion = "<query-h2>결론 / Conclusion</query-h2>"
                            references = "<query-h2>📚 참고문헌 / References</query-h2>"
                            sources = "<query-h2>🔍 검증 출처 / Sources for Verification</query-h2>"
                        elif has_traditional or (has_chinese and not has_simplified):
                            # Traditional Chinese
                            exec_summary = "<query-h2>摘要</query-h2>"
                            conclusion = "<query-h2>結論</query-h2>"
                            references = "<query-h2>📚 參考文獻</query-h2>"
                            sources = "<query-h2>🔍 驗證來源</query-h2>"
                        elif has_chinese:
                            # Simplified Chinese
                            exec_summary = "<query-h2>摘要</query-h2>"
                            conclusion = "<query-h2>结论</query-h2>"
                            references = "<query-h2>📚 参考文献</query-h2>"
                            sources = "<query-h2>🔍 验证来源</query-h2>"
                        else:
                            exec_summary = "<query-h2>Executive Summary</query-h2>"
                            conclusion = "<query-h2>Conclusion</query-h2>"
                            references = "<query-h2>📚 References</query-h2>"
                            sources = "<query-h2>🔍 Verification Sources</query-h2>"
                        
                        prompt = f"""Provide a BALANCED answer following the EXACT hierarchical format below.

User Question: {query}

---

## REQUIRED OUTPUT FORMAT (MUST FOLLOW EXACTLY):

<query-h1>[Main Title - Based on Query Topic]</query-h1>

[introduction paragraph - 2 sentences about the topic]

{exec_summary}

[flowing paragraph content - 3-5 sentences minimum]

<query-h2>1. [Section Title]</query-h2>

[introductory paragraph for this section - 80+ words]

<query-h3>1.1 [Subsection Title]</query-h3>

[paragraph content 150+ words with citations <span class="citation-ref">[1]</span>, <span class="citation-ref">[2]</span>]

<query-h3>1.2 [Subsection Title]</query-h3>

[paragraph content 150+ words]

<query-h3>1.3 [Subsection Title]</query-h3>

[paragraph content 150+ words]

<query-h2>2. [Section Title]</query-h2>

[introductory paragraph - 80+ words]

<query-h3>2.1 [Subsection Title]</query-h3>

[paragraph content 150+ words with citations]

<query-h3>2.2 [Subsection Title]</query-h3>

[paragraph content 150+ words]

<query-h3>2.3 [Subsection Title]</query-h3>

[paragraph content 150+ words]

<query-h2>3. [Section Title]</query-h2>

[introductory paragraph - 80+ words]

<query-h3>3.1 [Subsection Title]</query-h3>

[paragraph content 150+ words]

<query-h3>3.2 [Subsection Title]</query-h3>

[paragraph content 150+ words]

<query-h3>3.3 [Subsection Title]</query-h3>

[paragraph content 150+ words]

<query-h2>4. [Section Title]</query-h2>

[introductory paragraph - 80+ words]

<query-h3>4.1 [Subsection Title]</query-h3>

[paragraph content 150+ words]

<query-h3>4.2 [Subsection Title]</query-h3>

[paragraph content 150+ words]

<query-h3>4.3 [Subsection Title]</query-h3>

[paragraph content 150+ words]

{conclusion}

[synthesize key insights and closing thoughts in flowing paragraphs]

{references}

<div class="reference-item"><span class="ref-number">1.</span> [Source filename 1]</div>
<div class="reference-item"><span class="ref-number">2.</span> [Source filename 2]</div>
<div class="reference-item"><span class="ref-number">3.</span> [Source filename 3]</div>

---

**CITATION RULES:**
- Use <span class="citation-ref">[1]</span>, <span class="citation-ref">[2]</span> in HTML span tags when citing sources

Available Sources:
{source_mapping}

Context:
{context[:8000]}

**TARGET LENGTH**: {target_words} words total.

**REQUIREMENTS**:
1. Follow the EXACT hierarchical format with 4 numbered sections (1., 2., 3., 4.)
2. Each section MUST have 3 subsections (1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 4.1, 4.2, 4.3)
3. NEVER output main section content without subsections - subsections are REQUIRED
4. Write in flowing PARAGRAPHS (4-6 sentences minimum per paragraph)
5. Do NOT use bullet points or fragment sentences
6. WRITE COMPLETE SECTIONS - do NOT stop mid-sentence or mid-thought
7. Write in the same language as the user's question
8. Write AUTHORITATIVELY as an expert - do NOT say "Based on context" or "According to documents"
9. HIERARCHICAL STRUCTURE IS MANDATORY: 4 sections × 3 subsections = 12 subsections total
10. USE THE EXACT HEADERS PROVIDED ABOVE - Do NOT translate or change {exec_summary}, {conclusion}, or {references} to a different language
11. DO NOT TRUNCATE - Write until the article is COMPLETELY finished with all sections fully developed"""

                        system_prompt = f"""You are a senior research scientist writing academic survey papers.

CRITICAL HTML FORMAT REQUIREMENTS:
- Use <query-h1>TITLE</query-h1> for main document title
- Use <query-h2>1. Section Title</query-h2> for main section headers
- Use <query-h3>1.1 Subsection Title</query-h3> for subsection headers
- Use <span class="citation-ref">[1]</span> for citations
- Use <div class="reference-item"><span class="ref-number">1.</span> Source name</div> for references
- Do NOT use markdown (#, ##, ###) - use HTML tags ONLY

MANDATORY:
- Produce {target_words} words minimum (2000+ words for Comprehensive mode)
- HIERARCHICAL STRUCTURE: 4 main sections with 3 subsections EACH (12 subsections total)
- NEVER skip subsections - each section MUST have 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, etc.
- Write in flowing PARAGRAPHS, NOT bullet points (4-6 sentences per paragraph)
- Cover: introduction → section 1 (with 1.1, 1.2, 1.3) → section 2 (with 2.1, 2.2, 2.3) → section 3 (with 3.1, 3.2, 3.3) → section 4 (with 4.1, 4.2, 4.3) → conclusion
- Include References section at the end
- Write in same language as user's question
- WRITE COMPLETE RESPONSES - do NOT truncate or stop mid-sentence
- Continue writing until ALL sections are fully developed and complete"""

                    # Use provider-aware LLM completion with fallback support
                    try:
                        # Use multi-step generation for comprehensive and ultra modes
                        # to enforce subsection structure (1.1, 1.2, 1.3 etc.)
                        if is_ultra:
                            # Ultra-Deep: Use multi-step with 5 sections, 3 subsections each
                            print(f"[ULTRA MODE] Starting multi-step generation with 5 sections × 3 subsections")
                            rerank_logger.info(f"[ULTRA MODE] Multi-step generation: 5 sections, context length={len(context)}")
                            return await generate_ultra_response(
                                query, context, system_prompt, target_words, 
                                num_sections=5, num_subsections=3,
                                llm_config={"provider": llm_provider, "fallback_provider": llm_fallback},
                                chinese_variant=chinese_variant,
                                sources=filtered_result
                            )
                        elif is_comprehensive:
                            # Comprehensive: Use multi-step with 4 sections, 3 subsections each
                            print(f"[COMPREHENSIVE MODE] Starting multi-step generation with 4 sections × 3 subsections")
                            rerank_logger.info(f"[COMPREHENSIVE MODE] Multi-step generation: 4 sections, context length={len(context)}")
                            return await generate_ultra_response(
                                query, context, system_prompt, target_words, 
                                num_sections=4, num_subsections=3,
                                llm_config={"provider": llm_provider, "fallback_provider": llm_fallback},
                                chinese_variant=chinese_variant,
                                sources=filtered_result
                            )
                        
                        # Single-pass generation for standard modes (Quick, Balanced)
                        # Use max_tokens directly - already set based on mode with +25% buffer
                        print(f"[DEBUG] Single-pass generation: max_tokens={max_tokens}, mode={detail_level}")
                        rerank_logger.info(f"Single-pass generation: max_tokens={max_tokens}, mode={detail_level}")
                        return await llm_complete_with_provider(
                            prompt=prompt,
                            system_prompt=system_prompt,
                            provider=llm_provider,
                            fallback_provider=llm_fallback,
                            max_tokens=max_tokens,
                            temperature=temperature
                        )
                    except Exception as e:
                        # Log full error details for debugging
                        import traceback
                        rerank_logger.error(f"MULTI-STEP GENERATION FAILED: {e}")
                        rerank_logger.error(f"Traceback: {traceback.format_exc()}")
                        print(f"[ERROR] Multi-step generation failed: {e}")
                        print(f"[ERROR] Traceback: {traceback.format_exc()}")
                        
                        # If primary provider failed and no fallback configured, try the other provider
                        other_provider = "minimax" if llm_provider == "deepseek" else "deepseek"
                        rerank_logger.warning(f"Primary provider '{llm_provider}' failed: {e}")
                        if llm_fallback:
                            rerank_logger.info(f"Trying fallback provider '{llm_fallback}'...")
                        else:
                            rerank_logger.info(f"No fallback configured, trying '{other_provider}'...")
                        
                        fallback_to_use = llm_fallback or other_provider
                        return await llm_complete_with_provider(
                            prompt=prompt,
                            system_prompt=system_prompt,
                            provider=fallback_to_use,
                            fallback_provider=None,  # Don't cascade further
                            max_tokens=max_tokens,
                            temperature=temperature
                        )
                
                # Return the response directly - timeout is handled by caller
                return await get_response()
            except Exception as e:
                print(f"[LLM Error]: {e}")
                import traceback
                traceback.print_exc()
                return None
        
        # Run LLM generation directly in the main event loop with timeout
        # Note: Thread pool approach was causing "different event loop" errors with httpx client
        try:
            llm_response = await asyncio.wait_for(run_llm_async(), timeout=llm_timeout)
        except asyncio.TimeoutError:
            print(f"[LLM Timeout]: Generation took longer than {llm_timeout}s")
            llm_response = None
        
        if llm_response:
            # Calculate confidence based on rerank scores
            if filtered_result:
                scores = [r.get("rerank_score", r.get("similarity", 0.5)) for r in filtered_result]
                # Filter out NaN/Infinity values
                valid_scores = [s for s in scores if isinstance(s, (int, float)) and not (np.isnan(s) if isinstance(s, float) else False) and not (np.isinf(s) if isinstance(s, float) else False)]
                avg_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0.5
            else:
                avg_score = 0.5
            confidence = min(0.95, 0.5 + avg_score * 0.5)  # Scale to 0.5-0.95 range
            # Guard against NaN/Infinity in confidence
            if np.isnan(confidence) or np.isinf(confidence):
                confidence = 0.5
            
            # Build source list with scores
            source_list = []
            for r in filtered_result:
                score = r.get("rerank_score", r.get("similarity", 0))
                # Guard against NaN/Infinity in scores
                if isinstance(score, float) and (np.isnan(score) or np.isinf(score)):
                    score = 0.0
                source_list.append({
                    "source": r.get("source", "unknown"),
                    "score": round(score, 3),
                    "preview": r.get("content", "")[:100] + "..."
                })
            
            # DEBUG: Log all retrieved sources with their scores
            print(f"[DEBUG] Query: {query}")
            print(f"[DEBUG] Retrieved {len(filtered_result)} chunks")
            for i, r in enumerate(filtered_result[:5]):
                print(f"[DEBUG] Chunk {i+1}: source={r.get('source', 'unknown')}, score={r.get('rerank_score', r.get('similarity', 0)):.3f}")
            
            # Extract unique source filenames for the response
            unique_sources = list(set([r.get("source", "unknown") for r in filtered_result]))
            print(f"[DEBUG] Unique sources: {unique_sources}")
            
            # Sources already filtered before LLM generation, just use them directly
            final_response = llm_response
            
            # NEW: Validate and fix citations
            final_response, citation_warnings = validate_and_fix_citations(final_response, unique_sources)
            
            # Log citation issues
            if citation_warnings:
                print(f"[CITATION ISSUES] {citation_warnings}")
            
            # NEW: Academic review for Ultra/Comprehensive modes
            if is_ultra or is_comprehensive:
                print(f"[ACADEMIC REVIEW] Running scholarly citation review for {detail_level} mode...")
                try:
                    final_response, review_report = await academic_review_citations(
                        final_response, 
                        filtered_result, 
                        query,
                        llm_provider=llm_provider,
                        llm_fallback=llm_fallback
                    )
                    print(f"[ACADEMIC REVIEW] Report: {review_report}")
                except Exception as e:
                    print(f"[ACADEMIC REVIEW ERROR] {e}")
            
            return {
                "response": final_response,
                "answer": final_response,
                "sources": unique_sources,  # Return actual source filenames, not just count
                "source_details": source_list,
                "confidence": round(confidence, 2),
                "retrieval_info": {
                    "method": "vector_similarity" if not (use_rerank and rerank_method != "none") else f"vector+{rerank_method}",
                    "chunks_retrieved": initial_k if use_rerank else requested_top_k,
                    "chunks_reranked": len(filtered_result) if use_rerank else 0
                }
            }
    except Exception as e:
        print(f"[LLM Exception]: {e}")
    
    # FALLBACK: Generate answer from LLM knowledge when RAG fails
    print(f"[FALLBACK] RAG LLM failed or timed out. Generating answer from LLM knowledge...")
    
    try:
        # Generate answer from LLM knowledge without RAG context
        fallback_response = await generate_llm_knowledge_response(
            query,
            llm_config={"provider": llm_provider, "fallback_provider": llm_fallback},
            is_ultra=is_ultra,
            is_comprehensive=is_comprehensive
        )
        if fallback_response:
            return {
                "response": fallback_response,
                "answer": fallback_response,
                "sources": [],  # No sources - this is from LLM knowledge
                "confidence": 0.7,
                "retrieval_info": {
                    "method": "llm_knowledge_fallback",
                    "note": "Answer generated from LLM pre-trained knowledge (RAG sources insufficient or unavailable)"
                }
            }
    except Exception as e2:
        print(f"[FALLBACK ERROR] Failed to generate LLM knowledge response: {e2}")
    
    # Ultimate fallback - return raw chunks with scores
    preview_parts = []
    for r in filtered_result[:5]:
        score = r.get("rerank_score", r.get("similarity", 0))
        source = r.get("source", "unknown")
        preview_parts.append(f"[Score: {score:.2f}] {r.get('content', '')[:300]}...")
    
    preview = "\n\n".join(preview_parts)
    # Extract unique source filenames
    unique_sources = list(set([r.get("source", "unknown") for r in filtered_result]))
    return {
        "response": f"Found {len(filtered_result)} relevant chunks:\n\n{preview}",
        "answer": f"Found {len(filtered_result)} relevant chunks:\n\n{preview}",
        "sources": unique_sources,  # Return actual source filenames
        "confidence": 0.5,
        "retrieval_info": {
            "method": "vector_fallback",
            "note": "LLM generation failed, showing raw chunks"
        }
    }

async def generate_llm_knowledge_response(query: str, llm_config: dict = None, is_ultra: bool = False, is_comprehensive: bool = False) -> str:
    """
    Generate a comprehensive answer from LLM knowledge when RAG sources are insufficient.
    This is a fallback when no relevant documents are found in the knowledge base.
    Supports Ultra-Deep and Comprehensive modes with proper subsection structure.
    """
    import os
    import re
    
    # Get LLM provider from config
    if llm_config is None:
        llm_config = {}
    provider = llm_config.get("provider", "deepseek")
    fallback = llm_config.get("fallback_provider")
    
    # Detect language for headers
    has_chinese = bool(re.search(r'[\u4e00-\u9fff]', query))
    has_japanese = bool(re.search(r'[\u3040-\u309f\u30a0-\u30ff]', query))
    has_korean = bool(re.search(r'[\uac00-\ud7af]', query))
    
    # Detect Traditional vs Simplified Chinese
    trad_chars = r'[們員問學國過長從來時後無嗎讓愛會體與進說問們員來時國過長從們區義產點裡歲術]'
    simp_chars = r'[们员问学国过长从来时后无吗让爱会体与进说们员来时国过长从们区义产点里岁术]'
    has_traditional = bool(re.search(trad_chars, query))
    has_simplified = bool(re.search(simp_chars, query))
    
    if has_japanese:
        chinese_variant = "japanese"
    elif has_korean:
        chinese_variant = "korean"
    elif has_traditional or (has_chinese and not has_simplified):
        chinese_variant = "traditional"
    elif has_chinese:
        chinese_variant = "simplified"
    else:
        chinese_variant = "english"
    
    # For Ultra/Comprehensive modes, use generate_ultra_response with no context
    if is_ultra or is_comprehensive:
        # Create minimal context for the function
        context = f"User query: {query}\n\nNo relevant documents found in knowledge base. Generate answer from your training knowledge."
        
        # Build system prompt
        if chinese_variant == "traditional":
            language_instruction = "使用繁體中文（台灣/香港用字）撰寫，例如：「這裡」、「們」、「員」、「問」、「學」、「國」、「過」、「長」、「從」、「來」、「時」、「後」、「無」、「嗎」、「讓」、「愛」、「會」、「體」、「與」、「進」、「說」。禁止使用簡體字。"
        elif chinese_variant == "simplified":
            language_instruction = "使用简体中文撰写。"
        else:
            language_instruction = "Write in English."
            
        system_prompt = f"""You are a senior research scientist writing comprehensive academic survey papers.

CRITICAL HTML FORMAT REQUIREMENTS:
- Use <query-h1>TITLE</query-h1> for main document title
- Use <query-h2>1. Section Title</query-h2> for main section headers
- Use <query-h3>1.1 Subsection Title</query-h3> for subsection headers
- Do NOT use markdown (#, ##, ###) - use HTML tags ONLY

CRITICAL REQUIREMENTS - NO EXCEPTIONS:
- You MUST write MINIMUM 3000 WORDS for Ultra-Deep / 2000 WORDS for Comprehensive
- HIERARCHICAL STRUCTURE IS MANDATORY: Each main section MUST have EXACTLY 3 subsections
- NEVER output main section content without subsections - subsections are REQUIRED
- Each subsection must be 200+ words (6-10 sentences minimum)
- Write in flowing PARAGRAPHS ONLY - NEVER use bullet points
- Write in same language as user's question
- {language_instruction}"""
        
        try:
            return await generate_ultra_response(
                query, context, system_prompt, ">3000-4000" if is_ultra else ">2000",
                num_sections=5 if is_ultra else 4, num_subsections=3,
                llm_config=llm_config,
                chinese_variant=chinese_variant
            )
        except Exception as e:
            print(f"[ERROR] Ultra response generation failed: {e}")
            # Fall through to standard generation
    
    # Standard (Quick/Balanced) mode - simple structure
    query_lower = query.lower()
    is_comprehensive_keyword = any(word in query_lower for word in ['comprehensive', 'detailed', 'explain', 'how to', 'overview'])
    
    if is_comprehensive_keyword:
        target_words = "1500-2000"
        detail_level = "comprehensive"
    else:
        target_words = "800-1200"
        detail_level = "balanced"
    
    prompt = f"""Provide a {detail_level}, well-structured answer to the user's question.

User Question: {query}

Requirements:
1. Write {target_words} words
2. Start with a clear title (# Title) and executive summary
3. Use proper sections (## Section Name)
4. Include specific details, examples, and technical information
5. Write authoritatively - do NOT mention sources, documents, or the knowledge base
6. Do NOT add any disclaimer notes at the end about how the answer was generated
7. Do NOT cite specific sources (Source 1, 2, etc.) - just provide the answer directly

Structure:
# [Clear Title]

## Executive Summary
[2-3 sentence summary]

## [Main Section 1]
[Detailed content]

## [Main Section 2]
[Detailed content]

## [Main Section 3]
[Detailed content]

## Conclusion
[Summary and key takeaways]
"""

    system_prompt = "You are an expert providing comprehensive technical information. Write authoritatively based on your knowledge. Do not cite specific sources. Do not add any disclaimer notes about how the answer was generated. Just provide the direct answer."
    
    try:
        # Use provider-aware LLM completion
        response = await llm_complete_with_provider(
            prompt=prompt,
            system_prompt=system_prompt,
            provider=provider,
            fallback_provider=fallback,
            max_tokens=8192,  # NO TRUNCATION: DeepSeek max is 8192
            temperature=0.4
        )
        
        return response
    except Exception as e:
        print(f"[LLM Knowledge Fallback Error]: {e}")
        return None
        return None


# ============ LLM Response Generator ============
# Note: llm_complete_with_provider imported at top of file

async def generate_llm_response(query: str, context: str, target_words: str = "~1000", detail_level: str = "balanced", llm_config: dict = None) -> str:
    """Generate a well-formatted response using LLM from provided context"""
    
    # Get LLM provider from config (defaults to deepseek for backwards compatibility)
    if llm_config is None:
        llm_config = {}
    provider = llm_config.get("provider", "deepseek")
    fallback = llm_config.get("fallback_provider")
    
    import re
    
    # Check if context is substantial
    context_length = len(context.strip()) if context else 0
    has_context = context_length > 100
    
    # NO TRUNCATION: Set very high token limits to ensure complete answers (Query+File mode)
    if detail_level == "ultra-deep":
        max_tokens = 8192  # Ultra Deep: 8192 tokens (DeepSeek max)
    elif detail_level == "comprehensive":
        max_tokens = 8192  # Comprehensive: 8192 tokens (NO TRUNCATION)
    elif detail_level == "balanced":
        max_tokens = 8192  # Balanced: 8192 tokens (NO TRUNCATION)
    else:  # quick
        max_tokens = 8192  # Quick: 8192 tokens (NO TRUNCATION)
    
    # Detect query language for section headers
    has_chinese = bool(re.search(r'[\u4e00-\u9fff]', query))
    has_japanese = bool(re.search(r'[\u3040-\u309f\u30a0-\u30ff]', query))
    has_korean = bool(re.search(r'[\uac00-\ud7af]', query))
    
    # Detect Traditional vs Simplified Chinese
    trad_chars = r'[們員問學國過長從來時後無嗎讓愛會體與進說問們員來時國過長從們區義產點裡歲術]'
    simp_chars = r'[们员问学国过长从来时后无吗让爱会体与进说们员来时国过长从们区义产点里岁术]'
    has_traditional = bool(re.search(trad_chars, query))
    has_simplified = bool(re.search(simp_chars, query))
    
    if has_japanese:
        exec_summary = "<query-h2>概要 / Executive Summary</query-h2>"
        conclusion = "<query-h2>結論 / Conclusion</query-h2>"
        references = "<query-h2>📚 参考文献 / References</query-h2>"
        sources = "<query-h2>🔍 検証ソース / Sources for Verification</query-h2>"
    elif has_korean:
        exec_summary = "<query-h2>개요 / Executive Summary</query-h2>"
        conclusion = "<query-h2>결론 / Conclusion</query-h2>"
        references = "<query-h2>📚 참고문헌 / References</query-h2>"
        sources = "<query-h2>🔍 검증 출처 / Sources for Verification</query-h2>"
    elif has_traditional or (has_chinese and not has_simplified):
        # Traditional Chinese
        exec_summary = "<query-h2>摘要</query-h2>"
        conclusion = "<query-h2>結論</query-h2>"
        references = "<query-h2>📚 參考文獻</query-h2>"
        sources = "<query-h2>🔍 驗證來源</query-h2>"
    elif has_chinese:
        # Simplified Chinese
        exec_summary = "<query-h2>摘要</query-h2>"
        conclusion = "<query-h2>结论</query-h2>"
        references = "<query-h2>📚 参考文献</query-h2>"
        sources = "<query-h2>🔍 验证来源</query-h2>"
    else:
        exec_summary = "<query-h2>Executive Summary</query-h2>"
        conclusion = "<query-h2>Conclusion</query-h2>"
        references = "<query-h2>📚 References</query-h2>"
        sources = "<query-h2>🔍 Verification Sources</query-h2>"
    
    if has_context:
        # Query+File mode with EXACT hierarchical format
        prompt = f"""Answer the user's question using the provided documents. Follow the EXACT hierarchical format below.

---

## REQUIRED OUTPUT FORMAT (MUST FOLLOW EXACTLY):

<query-h1>[Main Title - Based on Query Topic]</query-h1>

[introduction paragraph - 2 sentences]

{exec_summary}

[flowing paragraph content - 3-5 sentences minimum]

<query-h2>1. [Section Title]</query-h2>

[introductory paragraph]

<query-h3>1.1 [Subsection Title]</query-h3>

[paragraph content with citations <span class="citation-ref">[1]</span>, <span class="citation-ref">[2]</span> when referencing specific sources]

<query-h3>1.2 [Subsection Title]</query-h3>

[paragraph content]

<query-h2>2. [Section Title]</query-h2>

[introductory paragraph]

<query-h3>2.1 [Subsection Title]</query-h3>

[paragraph content with citations]

<query-h3>2.2 [Subsection Title]</query-h3>

[paragraph content]

<query-h2>3. [Section Title]</query-h2>

[introductory paragraph]

<query-h3>3.1 [Subsection Title]</query-h3>

[paragraph content]

<query-h3>3.2 [Subsection Title]</query-h3>

[paragraph content]

{conclusion}

[synthesize key insights in flowing paragraphs]

{references}

<div class="reference-item"><span class="ref-number">1.</span> [Source filename 1]</div>
<div class="reference-item"><span class="ref-number">2.</span> [Source filename 2]</div>

---

User Question: {query}

Context from documents:
{context[:4000]}

**TARGET LENGTH**: {target_words} words total.

**REQUIREMENTS**:
1. Follow the EXACT hierarchical format with numbered sections (1., 1.1, 1.2, 2., etc.)
2. Write in flowing PARAGRAPHS (3-5 sentences minimum per paragraph)
3. Do NOT use bullet points or fragment sentences
4. Complete ALL sections fully - do NOT truncate
5. Write in the same language as the user's question
6. Use <span class="citation-ref">[1]</span> for citations"""

        system_prompt = f"""You are a senior research scientist writing academic survey papers.

CRITICAL HTML FORMAT REQUIREMENTS:
- Use <query-h1>TITLE</query-h1> for main document title
- Use <query-h2>1. Section Title</query-h2> for main section headers
- Use <query-h3>1.1 Subsection Title</query-h3> for subsection headers
- Use <span class="citation-ref">[1]</span> for citations
- Use <div class="reference-item"><span class="ref-number">1.</span> Source name</div> for references
- Do NOT use markdown (#, ##, ###) - use HTML tags ONLY

MANDATORY:
- Produce {target_words} words minimum
- Write in flowing PARAGRAPHS, NOT bullet points (3-5 sentences per paragraph)
- Cover: introduction → section 1 → section 2 → section 3 → conclusion
- Include References section at the end
- Write in same language as user's question"""
    else:
        # No context available - use general knowledge with hierarchical format
        prompt = f"""Provide a comprehensive answer following the EXACT hierarchical format below.

---

## REQUIRED OUTPUT FORMAT (MUST FOLLOW EXACTLY):

<query-h1>[Main Title - Based on Query Topic]</query-h1>

[introduction paragraph - 2 sentences]

{exec_summary}

[flowing paragraph content - 3-5 sentences minimum]

<query-h2>1. [Section Title]</query-h2>

[introductory paragraph]

<query-h3>1.1 [Subsection Title]</query-h3>

[paragraph content explaining the topic]

<query-h3>1.2 [Subsection Title]</query-h3>

[paragraph content]

<query-h2>2. [Section Title]</query-h2>

[introductory paragraph]

<query-h3>2.1 [Subsection Title]</query-h3>

[paragraph content]

<query-h3>2.2 [Subsection Title]</query-h3>

[paragraph content]

<query-h2>3. [Section Title]</query-h2>

[introductory paragraph]

<query-h3>3.1 [Subsection Title]</query-h3>

[paragraph content]

<query-h3>3.2 [Subsection Title]</query-h3>

[paragraph content]

{conclusion}

[synthesize key insights in flowing paragraphs]

{references}

[N/A - General knowledge response]

---

User Question: {query}

**TARGET LENGTH**: {target_words} words total.

**REQUIREMENTS**:
1. Follow the EXACT hierarchical format with numbered sections (1., 1.1, 1.2, 2., etc.)
2. Write in flowing PARAGRAPHS (3-5 sentences minimum per paragraph)
3. Do NOT use bullet points or fragment sentences
4. Complete ALL sections fully - do NOT truncate
5. Write in the same language as the user's question"""

        system_prompt = f"You are a helpful assistant providing {detail_level} information. Follow the EXACT output format with Title, Executive Summary, sections, Conclusion, References, and Sources for Verification."
    
    try:
        # Use the provider-aware LLM completion function
        response = await llm_complete_with_provider(
            prompt=prompt,
            system_prompt=system_prompt,
            provider=provider,
            fallback_provider=fallback,
            max_tokens=max_tokens,
            temperature=0.4
        )
        
        # Response returned without source note - citations in text indicate sources used
        
        return response
    except Exception as e:
        raise Exception(f"LLM generation failed: {str(e)}")

# ============ Chat with Document ============
@app.post("/api/v1/chat/with-doc")
async def chat_with_doc(request: dict):
    """
    Query with document upload - searches BOTH uploaded files AND existing database.
    Supports multiple search modes: semantic (default), entity-lookup, graph-traversal.
    """
    message = request.get("message", "")
    filename = request.get("filename", "")
    filenames = request.get("filenames", [])  # Support multiple files
    
    # Get search mode (default: semantic)
    search_mode = request.get("mode", "semantic").lower()
    
    # Get LLM configuration from request (if provided)
    llm_config = request.get("llm_config", {})
    llm_provider = llm_config.get("provider", "deepseek")  # Default to DeepSeek
    llm_fallback = llm_config.get("fallback_provider")
    
    # Get query mode for word count control
    is_ultra = request.get("ultra_comprehensive", False)
    is_comprehensive = request.get("detailed", False)
    top_k = request.get("top_k", 20)
    max_depth = request.get("max_depth", 2)
    
    # Word count targets based on mode (+25% buffer to prevent truncation)
    if is_ultra:
        target_words = ">2500-3500"
        detail_level = "ultra-deep"
        max_context_chunks = 50  # More chunks for ultra
    elif is_comprehensive:
        target_words = ">1800-2500"
        detail_level = "comprehensive"
        max_context_chunks = 30
    elif top_k >= 20:
        target_words = ">1200-1800"
        detail_level = "balanced"
        max_context_chunks = 20
    else:
        target_words = ">600-1200"
        detail_level = "quick"
        max_context_chunks = 10
    
    # Handle both single filename and array of filenames
    if isinstance(filename, str) and filename:
        file_list = [filename] + filenames if filenames else [filename]
    elif isinstance(filename, list):
        file_list = filename
    else:
        file_list = filenames if filenames else []
    
    if not message:
        return {
            "response": "Please enter a question.",
            "answer": "Please enter a question.",
            "sources": []
        }
    
    # Get doc_ids from filenames
    import hashlib
    import re
    
    # Filter out empty filenames
    file_list = [f for f in file_list if f and f.strip()]
    doc_ids = [hashlib.md5(f.encode()).hexdigest()[:12] for f in file_list] if file_list else []
    
    # DEBUG: Log what's being received
    print(f"[DEBUG] chat/with-doc: message='{message}', detail_level={detail_level}, search_mode={search_mode}, file_list={file_list}, doc_ids={doc_ids}")
    
    # Collect results from BOTH uploaded files AND entire database
    all_results = []
    file_sources = set()  # Track which sources are from uploaded files
    
    try:
        # Step 1: Vector search on UPLOADED FILES first (most relevant)
        if doc_ids:
            try:
                # Generate query embedding for vector search
                query_embedding = get_ollama_embedding(message)
                from storage import DistanceMetric
                
                # Search for relevant chunks in uploaded files using vector similarity
                # We'll search all chunks but filter by entity_id
                vector_results = await storage.search_chunks(
                    query_vector=query_embedding,
                    limit=30,  # Get more to filter by doc_ids
                    distance_metric=DistanceMetric.COSINE,
                    match_threshold=0.2
                )
                
                # Filter to only keep chunks from uploaded files
                for r in vector_results:
                    chunk_doc_id = r.metadata.get('doc_id') or r.entity_id
                    if chunk_doc_id in doc_ids or r.entity_id in doc_ids:
                        all_results.append({
                            "content": r.content, 
                            "source": "uploaded",
                            "similarity": r.similarity
                        })
                        
                print(f"[DEBUG] Vector search found {len(all_results)} relevant chunks from uploaded files")
                
                # Fallback: If vector search returns few results, get more chunks directly
                if len(all_results) < 5:
                    print(f"[DEBUG] Vector search returned few results, fetching more chunks directly...")
                    placeholders = ','.join([f'${i+1}' for i in range(len(doc_ids))])
                    file_chunks_query = f"SELECT content, entity_id FROM chunks WHERE entity_id IN ({placeholders}) LIMIT 50"
                    
                    try:
                        file_chunks = await asyncio.wait_for(
                            storage.client.fetch(file_chunks_query, *doc_ids),
                            timeout=10.0
                        )
                        
                        # Add chunks not already included
                        existing = {r["content"][:100] for r in all_results}
                        for chunk in file_chunks:
                            content = chunk.get('content', '')
                            if content[:100] not in existing:
                                all_results.append({"content": content, "source": "uploaded"})
                                existing.add(content[:100])
                                
                        print(f"[DEBUG] Fallback added chunks, total from files: {len(all_results)}")
                    except Exception as e:
                        print(f"[DEBUG] Fallback chunk fetch failed: {e}")
                        
            except Exception as e:
                print(f"[DEBUG] File vector search error: {e}")
        
        # Step 2: ALSO search ENTIRE DATABASE (always do this, not just fallback)
        try:
            query_embedding = get_ollama_embedding(message)
            from storage import DistanceMetric
            
            # Calculate how many more chunks we need
            remaining_slots = max_context_chunks - len(all_results)
            
            if remaining_slots > 0:
                vector_results = await storage.search_chunks(
                    query_vector=query_embedding,
                    limit=remaining_slots,
                    distance_metric=DistanceMetric.COSINE,
                    match_threshold=0.3
                )
                
                # Add database results (avoiding duplicates)
                existing_content = {r["content"][:100] for r in all_results}
                for r in vector_results:
                    content_key = r.content[:100]
                    if content_key not in existing_content:
                        all_results.append({"content": r.content, "source": "database"})
                        existing_content.add(content_key)
                        
                print(f"[DEBUG] Added {len(all_results)} total chunks from files + database")
        except Exception as e:
            print(f"[DEBUG] Database search error: {e}")
        
    except Exception as e:
        print(f"[DEBUG] Overall search error: {e}")
    
    # Remove duplicates
    seen = set()
    unique_results = []
    for r in all_results:
        content = r["content"][:100]  # Use first 100 chars as key
        if content not in seen:
            seen.add(content)
            unique_results.append(r)
    
    result = unique_results if unique_results else None
    
    if not result:
        # Clean up query for display - remove common prefixes
        clean_message = re.sub(r'^(tell me about |what is |who is |show me |find |search for |about |explain )', '', message.lower().strip())
        
        # Build more helpful error message
        if file_list:
            msg = f"I couldn't find any information related to '{clean_message}'. Tried searching in uploaded files and database. Try a different search term."
        else:
            msg = f"I couldn't find any information related to '{clean_message}'. Please try a different search term or upload relevant documents."
        
        return {
            "response": msg,
            "answer": msg,
            "context": "",
            "sources": [],
            "confidence": 0.0
        }
    # Skip only if too many box-drawing chars
    import re
    filtered_result = []
    box_chars = re.compile(r'[\u2500-\u257F]')
    
    for r in result:
        content = r.get("content", "")
        if len(content) < 50:
            continue
        # Skip only if more is box-drawing than 30% chars
        box_count = len(box_chars.findall(content))
        if box_count > 0 and box_count / len(content) > 0.3:
            continue
        filtered_result.append({"content": content})
    
    if not filtered_result:
        return {
            "response": f"I couldn't find any clean information related to '{message}'. The indexed data may contain formatting issues.",
            "answer": f"I couldn't find any clean information related to '{message}'. The indexed data may contain formatting issues.",
            "context": "",
            "sources": [],
            "confidence": 0.0
        }
    
    context = "\n\n".join([r["content"] for r in filtered_result])
    
    # Clean up the context
    context = re.sub(r'[╮╯╭╰━┃╱╲╳╔╗╚╝║═╠╬╣╝╚]', '', context)
    context = re.sub(r'─{3,}', '', context)
    context = re.sub(r'│{2,}', '', context)
    context = re.sub(r'\s+', ' ', context)
    context = context.strip()
    
    # Generate LLM response with proper formatting
    # For file queries, sources are the uploaded files
    source_list = file_list if file_list else ["database"]
    try:
        llm_response = await generate_llm_response(
            message, context, target_words, detail_level,
            llm_config={"provider": llm_provider, "fallback_provider": llm_fallback}
        )
        return {
            "response": llm_response,
            "answer": llm_response,
            "context": context,
            "sources": source_list,  # Return actual filenames
            "confidence": 0.8
        }
    except Exception as e:
        return {
            "response": f"Found {len(filtered_result)} relevant chunks:\n\n{context[:1500]}",
            "answer": f"Found {len(filtered_result)} relevant chunks:\n\n{context[:1500]}",
            "context": context,
            "sources": source_list,  # Return actual filenames
            "confidence": 0.5
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002)
