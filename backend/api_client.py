"""
API Client for T036 FastAPI Backend (T058) - Synchronous Version
With ChatBot LLM Integration
"""
import html
import logging
import os
import re
import sys
import asyncio
from typing import Optional

# CRITICAL: Add current directory FIRST to avoid wrong config import
web_ui_dir = os.path.dirname(os.path.abspath(__file__))
if web_ui_dir not in sys.path:
    sys.path.insert(0, web_ui_dir)

# Add path for MiniMax AFTER local imports
sys.path.insert(0, '/Users/ken/clawd-jenny')

# MiniMax API configuration
MINIMAX_API_KEY = "sk-api-xI5kPLYH5Q1TbOjbVJrn3xYUZO5xWaWVEQP3LSVs8lR3JQ5roX_I4qG7ewZyYU16Sp_Ndg3aCTt6nRQzdf2mIvjmRxhv9z0ZjrNOwLVSSkbXEgmsvzpBjgk"
MINIMAX_MODEL = "MiniMax-M2.1"

import httpx

# Import Config - use local path to avoid clawd-jenny config conflict
import importlib.util
spec = importlib.util.spec_from_file_location("config", os.path.join(os.path.dirname(__file__), "config.py"))
config_module = importlib.util.module_from_spec(spec)
sys.modules['config'] = config_module
spec.loader.exec_module(config_module)
Config = config_module.Config

logger = logging.getLogger(__name__)

try:
    import httpx
    MINIMAX_AVAILABLE = True
    logger.info("MiniMax integration loaded")
except ImportError:
    MINIMAX_AVAILABLE = False
    logger.warning("MiniMax not available, chatbot mode disabled")


"""
API Client for T036 FastAPI Backend (T058) - Synchronous Version
With ChatBot LLM Integration
"""
import html
import logging
import os
import re
import sys
import asyncio
from typing import Optional

# Add path for MiniMax
sys.path.insert(0, '/Users/ken/clawd-jenny')

# MiniMax API configuration
MINIMAX_API_KEY = "sk-api-xI5kPLYH5Q1TbOjbVJrn3xYUZO5xWaWVEQP3LSVs8lR3JQ5roX_I4qG7ewZyYU16Sp_Ndg3aCTt6nRQzdf2mIvjmRxhv9z0ZjrNOwLVSSkbXEgmsvzpBjgk"
MINIMAX_MODEL = "MiniMax-M2.1"

import httpx
logger = logging.getLogger(__name__)

# Inline config - avoid import conflicts with clawd-jenny/config
class Config:
    API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8001")
    API_PREFIX = "/api"  # API has /api/v1/ routes
    API_TIMEOUT = 60
    MAX_QUERY_LENGTH = 500
    MOCK_DELAY = 0.5
async def call_minimax(prompt: str, system_prompt: str = None, max_tokens: int = 8192, temperature: float = 0.7) -> str:
    """Call MiniMax API directly."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            'https://api.minimaxi.com/v1/text/chatcompletion_v2',
            headers={
                'Authorization': f"Bearer {MINIMAX_API_KEY}",
                'Content-Type': 'application/json'
            },
            json={
                'model': MINIMAX_MODEL,
                'messages': messages,
                'max_tokens': max_tokens,
                'temperature': temperature
            },
            timeout=60.0
        )
        if resp.status_code == 200:
            result = resp.json()
            return result['choices'][0]['message']['content']
        else:
            raise Exception(f"MiniMax API error: {resp.status_code} - {resp.text}")


class APIError(Exception):
    """Custom exception for API errors."""
    
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


def safe_query(user_input: str) -> str:
    """Sanitize and validate user input."""
    cleaned = user_input.strip()
    if len(cleaned) < 1:
        raise ValueError("Query cannot be empty")
    if len(cleaned) > Config.MAX_QUERY_LENGTH:
        raise ValueError(f"Query exceeds maximum length of {Config.MAX_QUERY_LENGTH} characters")
    cleaned = html.escape(cleaned)
    return cleaned


def safe_filename(filename: str) -> str:
    """Sanitize uploaded filename."""
    filename = os.path.basename(filename)
    filename = re.sub(r'[^\w\s\-\.]', '_', filename)
    return filename[:255]


class APIClient:
    """Synchronous client for T036 FastAPI backend."""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or Config.API_BASE_URL
        self.timeout = Config.API_TIMEOUT
        logger.info(f"APIClient initialized with base_url: {self.base_url}")
    
    def query(self, query: str, mode: str = "hybrid", top_k: int = 10) -> dict:
        """Send a query to the RAG system using POST /api/v1/query."""
        import httpx
        
        sanitized_query = safe_query(query)
        
        # KG RAG API uses /api/v1/query with this payload structure
        payload = {
            "query": sanitized_query,
            "max_depth": 2,
            "limit": top_k,
            "include_metadata": True
        }
        
        endpoint = f"{Config.API_PREFIX}/v1/query"
        logger.info(f"Sending query to {self.base_url}{endpoint}")
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}{endpoint}",
                    json=payload
                )
                resp.raise_for_status()
                result = resp.json()
                
                # Transform KG RAG response to match expected format
                rag_result = {
                    "response": result.get("query", "No response"),
                    "sources": [{"content": str(s)} for s in result.get("results", [])],
                    "confidence": 0.8  # Default confidence
                }
                
                logger.info("Query successful")
                return rag_result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise APIError(
                f"API request failed: {e.response.status_code}",
                status_code=e.response.status_code
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise APIError(f"Unexpected error: {str(e)}")
    
    def query_chatbot(self, query: str, top_k: int = 10) -> dict:
        """
        Query the RAG system and generate a conversational response using MiniMax LLM.
        
        This follows the LightRAG pattern:
        1. Retrieve entities from KG RAG API
        2. Format entities and relationships as context
        3. Generate conversational answer with MiniMax
        """
        import httpx
        import sys
        
        if not MINIMAX_AVAILABLE:
            # Fallback to regular query if MiniMax not available
            logger.warning("MiniMax not available, falling back to regular query")
            return self.query(query, top_k=top_k)
        
        sanitized_query = safe_query(query)
        
        # Clean query - remove common question prefixes that don't match entities
        query_clean = sanitized_query.lower().strip()
        # Remove trailing punctuation
        query_clean = query_clean.rstrip('?.,!')
        for prefix in ['what is ', 'what are ', 'what is the ', 'how does ', 'define ']:
            if query_clean.startswith(prefix):
                query_clean = query_clean[len(prefix):]
                break
        # Use cleaned query for API but keep original for prompt
        api_query = query_clean.strip() if query_clean.strip() else sanitized_query
        
        # Step 1: Get entities from KG RAG API
        payload = {
            "query": api_query,
            "max_depth": 2,
            "limit": top_k,
            "include_metadata": True
        }
        
        endpoint = f"{Config.API_PREFIX}/v1/query"
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}{endpoint}",
                    json=payload
                )
                resp.raise_for_status()
                kg_result = resp.json()
            
            # Step 2: Extract entities and relationships for context
            entities = kg_result.get("results", [])
            
            if not entities:
                return {
                    "response": "I couldn't find any relevant information in the knowledge base to answer your question.",
                    "sources": [],
                    "confidence": 0.0
                }
            
            # Format entities for prompt
            entities_text = self._format_entities_for_prompt(entities)
            
            # Format relationships for prompt
            relationships_text = self._format_relationships_for_prompt(entities)
            
            # Step 3: Generate conversational response with MiniMax
            system_prompt = """You are a helpful knowledge assistant. Your task is to explain topics based on information from a knowledge graph.

Guidelines:
- Be concise but informative
- Use the provided entities and relationships to build your answer
- If information is incomplete, acknowledge what you know
- Format key terms in **bold** when first mentioned
- Keep a conversational, friendly tone
- Start your response naturally, not with "Based on..." """
            
            user_prompt = f"""Based on the user's question: "{sanitized_query}"

Here is the relevant information from the knowledge graph:

**Entities:**
{entities_text}

**Relationships:**
{relationships_text}

Please provide a clear, conversational answer to the user's question. Use the knowledge graph information above to ground your response. Make it sound natural, like you're explaining to a friend."""

            # Call MiniMax directly
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                llm_response = loop.run_until_complete(
                    call_minimax(
                        prompt=user_prompt,
                        system_prompt=system_prompt,
                        max_tokens=8192,  # NO TRUNCATION: DeepSeek max is 8192
                        temperature=0.7
                    )
                )
            finally:
                loop.close()
            
            # Format sources for display
            sources = [{"content": e.get("entity_name", "Unknown")} for e in entities[:5]]
            
            return {
                "response": llm_response,
                "sources": sources,
                "confidence": 0.85
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise APIError(f"API request failed: {e.response.status_code}", status_code=e.response.status_code)
        except Exception as e:
            logger.error(f"Chatbot error: {e}")
            raise APIError(f"Chatbot error: {str(e)}")
    
    def _format_entities_for_prompt(self, entities: list) -> str:
        """Format entity list into readable text for prompt."""
        if not entities:
            return "No entities found."
        
        lines = []
        for e in entities:
            name = e.get("entity_name", "Unknown")
            entity_type = e.get("entity_type", "Concept")
            # Use name as description since we don't have full content
            lines.append(f"- **{name}** ({entity_type})")
        
        return "\n".join(lines)
    
    def _format_relationships_for_prompt(self, entities: list) -> str:
        """Format relationships into readable text."""
        all_rels = []
        for e in entities:
            rels = e.get("relationships", [])
            for r in rels:
                source = e.get("entity_name", "Unknown")
                target = r.get("entity", "Unknown")
                rel_type = r.get("type", "related_to")
                all_rels.append(f"- **{source}** → {rel_type} → **{target}**")
        
        if not all_rels:
            return "No relationships found."
        
        return "\n".join(all_rels[:20])  # Limit to 20 relationships
    
    def health_check(self) -> bool:
        """Check if API is healthy."""
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(f"{self.base_url}/health")
                return resp.status_code == 200
        except Exception:
            return False
    
    def get_stats(self) -> dict:
        """Get knowledge graph statistics."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                endpoint = f"{Config.API_PREFIX}/v1/stats"
                resp = client.get(f"{self.base_url}{endpoint}")
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}
    
    def get_entities(self, limit: int = 10) -> list:
        """Get list of entities."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                endpoint = f"{Config.API_PREFIX}/v1/entities"
                resp = client.get(f"{self.base_url}{endpoint}", params={"limit": limit})
                resp.raise_for_status()
                return resp.json().get("entities", [])
        except Exception as e:
            logger.error(f"Error getting entities: {e}")
            return []
    
    def search_entities(self, query: str, limit: int = 10) -> list:
        """Search for entities."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                endpoint = f"{Config.API_PREFIX}/v1/entities/search"
                resp = client.get(
                    f"{self.base_url}{endpoint}",
                    params={"query": query, "limit": limit}
                )
                resp.raise_for_status()
                return resp.json().get("results", [])
        except Exception as e:
            logger.error(f"Error searching entities: {e}")
            return []
    
    def get_relationships(self, entity_id: str) -> list:
        """Get relationships for an entity."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                endpoint = f"{Config.API_PREFIX}/v1/entities/{entity_id}/relationships"
                resp = client.get(f"{self.base_url}{endpoint}")
                resp.raise_for_status()
                return resp.json().get("relationships", [])
        except Exception as e:
            logger.error(f"Error getting relationships: {e}")
            return []
    
    async def upload_document(self, file, ext: str) -> dict:
        """Upload and index a document."""
        try:
            # Read file content
            file_content = file.read()
            file_size = len(file_content)
            
            # Encode to base64
            import base64
            content_b64 = base64.b64encode(file_content).decode('utf-8')
            
            # Prepare payload
            payload = {
                "filename": file.name,
                "content": content_b64,
                "content_type": ext
            }
            
            endpoint = f"{Config.API_PREFIX}/v1/documents/upload"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}{endpoint}",
                    json=payload
                )
                resp.raise_for_status()
                result = resp.json()
                
                logger.info(f"Uploaded {file.name} ({file_size} bytes)")
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error uploading {file.name}: {e.response.status_code} - {e.response.text}")
            raise APIError(f"Upload failed: {e.response.status_code}", status_code=e.response.status_code)
        except Exception as e:
            logger.error(f"Error uploading {file.name}: {str(e)}")
            raise APIError(f"Upload error: {str(e)}")


class MockAPIClient:
    """Mock API client for demo mode."""
    
    def __init__(self):
        self.delay = Config.MOCK_DELAY
        logger.info("MockAPIClient initialized")
    
    def query(self, query: str, mode: str = "hybrid", top_k: int = 10) -> dict:
        """Return mock response."""
        import time
        time.sleep(self.delay)
        
        responses = {
            "rag": {
                "response": "RAG (Retrieval-Augmented Generation) is a technique that enhances LLM responses by fetching relevant information from a knowledge base. It combines the generative power of AI with accurate retrieval of context.",
                "sources": [
                    {"content": "Wikipedia: Retrieval-Augmented Generation"},
                    {"content": "Hugging Face: RAG Tutorial"},
                    {"content": "LangChain: RAG Documentation"}
                ],
                "confidence": 0.85
            },
            "default": {
                "response": f"This is a demo response for: '{query}'. In a real system, this would query the knowledge graph for relevant information.",
                "sources": [
                    {"content": "Demo Source 1"},
                    {"content": "Demo Source 2"}
                ],
                "confidence": 0.75
            }
        }
        
        if "rag" in query.lower():
            return responses["rag"]
        return responses["default"]
    
    def query_chatbot(self, query: str, top_k: int = 10) -> dict:
        """Return mock chatbot response for demo mode."""
        import time
        time.sleep(self.delay)
        
        # Generate conversational response based on query
        responses = {
            "machine learning": "**Machine learning** is a fascinating subset of artificial intelligence that enables computers to learn from data without being explicitly programmed. It powers many modern applications like recommendation systems, image recognition, and natural language processing. The technology has relationships with deep learning, neural networks, and data science.",
            "artificial intelligence": "**Artificial Intelligence** (AI) is the broad field of creating intelligent machines. It encompasses various techniques including machine learning, natural language processing, and computer vision. AI systems can perform tasks that typically require human intelligence, such as reasoning, learning, and problem-solving.",
            "default": f"Great question about **{query}**! Based on my knowledge of the topic, I can tell you that this is an important concept in our knowledge graph. The entities and relationships in our database help provide accurate and contextually relevant information."
        }
        
        query_lower = query.lower()
        for key, response in responses.items():
            if key in query_lower:
                return {
                    "response": response,
                    "sources": [{"content": f"Knowledge Graph: {key}"}],
                    "confidence": 0.9
                }
        
        return responses["default"]
    
    async def upload_document(self, file, ext: str) -> dict:
        """Mock document upload."""
        import time
        time.sleep(0.1)  # Simulate upload time
        return {"status": "success", "doc_id": f"mock_{file.name}", "chunks": 5}
    
    def health_check(self) -> bool:
        """Mock health check."""
        return True
    
    def get_stats(self) -> dict:
        """Mock stats."""
        return {"entities": 100, "relationships": 500}
    
    def get_entities(self, limit: int = 10) -> list:
        """Mock entities."""
        return [{"id": f"entity_{i}", "name": f"Entity {i}", "type": "Concept"} for i in range(limit)]
    
    def search_entities(self, query: str, limit: int = 10) -> list:
        """Mock search."""
        return [{"id": f"result_{i}", "name": f"Result {i} for {query}", "score": 0.9 - (i * 0.1)} for i in range(min(limit, 5))]
    
    def get_relationships(self, entity_id: str) -> list:
        """Mock relationships."""
        return [{"type": "related_to", "target": "Another Entity"}]


def create_api_client(use_real: bool = False) -> "APIClient | MockAPIClient":
    """Factory function to create an API client."""
    if use_real:
        return APIClient()
    return MockAPIClient()
