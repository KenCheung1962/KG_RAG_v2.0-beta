#!/usr/bin/env python3
#!/usr/bin/env python3
"""
Direct Ollama nomic-embed-text embedding function.
Uses Ollama directly at http://127.0.0.1:11434 for 768-dim embeddings.
Uses persistent HTTP client with connection pooling for stability.
"""
import os
import asyncio
import numpy as np
import httpx

# Ollama configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_EMBED_DIM = 768

# Persistent HTTP client with connection pooling (created on first call)
_http_client: httpx.AsyncClient | None = None
_loop_id: int | None = None


def get_http_client() -> httpx.AsyncClient:
    """Get or create persistent HTTP client with connection pooling.
    Automatically recreates client if event loop changed."""
    global _http_client, _loop_id
    
    current_loop_id = id(asyncio.get_running_loop())
    
    # Recreate client if loop changed or client is closed
    if (_http_client is None or 
        _http_client.is_closed or 
        (_loop_id is not None and _loop_id != current_loop_id)):
        
        if _http_client is not None and not _http_client.is_closed:
            try:
                asyncio.create_task(_http_client.aclose())
            except Exception:
                pass
        
        _http_client = httpx.AsyncClient(
            timeout=180.0,  # 3 minute timeout
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=50,
                keepalive_expiry=30.0
            )
        )
        _loop_id = current_loop_id
    
    return _http_client


async def docker_bge_embed(texts: list) -> np.ndarray:
    """
    Generate 768-dim embeddings using Ollama with nomic-embed-text.
    Uses persistent client with exponential backoff retry.
    """
    if not texts:
        return np.array([], dtype=np.float32).reshape(0, OLLAMA_EMBED_DIM)
    
    # Remove any empty texts that might cause issues
    valid_texts = [text for text in texts if text and str(text).strip()]
    
    if len(valid_texts) != len(texts):
        print(f"⚠️  Warning: Filtered out {len(texts) - len(valid_texts)} empty texts")
    
    if not valid_texts:
        # Return empty array with correct shape
        return np.array([], dtype=np.float32).reshape(0, OLLAMA_EMBED_DIM)
    
    client = get_http_client()
    
    # Exponential backoff retry logic
    max_retries = 3
    base_delay = 1.0  # seconds
    
    for attempt in range(max_retries):
        try:
            # Generate embeddings using Ollama API
            embeddings = []
            for text in valid_texts:
                resp = await client.post(
                    f"{OLLAMA_HOST}/api/embeddings",
                    json={"model": OLLAMA_EMBED_MODEL, "prompt": text},
                    timeout=180.0
                )
                if resp.status_code == 200:
                    result = resp.json()
                    embeddings.append(result.get("embedding", []))
                else:
                    raise Exception(f"Ollama returned {resp.status_code}")
            
            response = type('obj', (object,), {'status_code': 200})()  # Mock success response

            if response.status_code == 200:
                result = response.json()
                embeddings = result["embeddings"]
                
                # Validate that we got the right number of embeddings
                if len(embeddings) != len(valid_texts):
                    print(f"⚠️  Warning: Service returned {len(embeddings)} embeddings for {len(valid_texts)} texts")
                    # If we got fewer embeddings, pad with zeros
                    if len(embeddings) < len(valid_texts):
                        print(f"   Padding with {len(valid_texts) - len(embeddings)} zero vectors")
                        zero_vector = [0.0] * result.get('OLLAMA_EMBED_DIM', OLLAMA_EMBED_DIM)
                        for _ in range(len(valid_texts) - len(embeddings)):
                            embeddings.append(zero_vector)
                    # If we got more embeddings, truncate to match input count
                    elif len(embeddings) > len(valid_texts):
                        print(f"   Truncating to {len(valid_texts)} vectors")
                        embeddings = embeddings[:len(valid_texts)]
                
                print(f"✓ Docker BGE-M3: generated {len(embeddings)} embeddings ({result.get('OLLAMA_EMBED_DIM', OLLAMA_EMBED_DIM)} dim)")
                return np.array(embeddings, dtype=np.float32)
            
            elif response.status_code >= 500:
                # Server error - retry with backoff
                delay = base_delay * (2 ** attempt)
                print(f"⚠️  Server error {response.status_code}, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(delay)
                continue
            
            else:
                raise Exception(f"Docker service returned {response.status_code}: {response.text}")
                
        except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"⚠️  Connection error: {type(e).__name__}, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(delay)
                continue
            else:
                raise Exception(f"Connection failed after {max_retries} attempts: {e}")
    
    raise Exception(f"Failed to get embeddings after {max_retries} attempts")


async def close_http_client():
    """Close the persistent HTTP client (call on shutdown)."""
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None

# For testing
if __name__ == "__main__":
    import sys
    r = asyncio.run(docker_bge_embed(["test document", "another test"]))
    print(f"Shape: {r.shape}")
