#!/usr/bin/env python3
#!/usr/bin/env python3
"""
MiniMax LLM + DeepSeek Integration for LightRAG.

This module provides:
- MiniMax-M2.1 for LLM (text completion)
- DeepSeek for embeddings AND LLM (OpenAI-compatible API)

Timeout Configuration:
- EMBEDDING_TIMEOUT: 120 seconds (default)
- LLM_TIMEOUT: 180 seconds (default)
"""
import os
import asyncio
import hashlib
from typing import List, Optional, Awaitable
import numpy as np
import httpx

# Load timeout configuration
# NO TRUNCATION: Increased timeouts to support long-form content generation
EMBEDDING_TIMEOUT = float(os.getenv("EMBEDDING_TIMEOUT", "120"))
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "900"))  # 15 min for NO TRUNCATION - Ultra mode needs more time for multi-step generation

print(f"[minimax.py] Timeout Configuration: EMBEDDING_TIMEOUT={EMBEDDING_TIMEOUT}s, LLM_TIMEOUT={LLM_TIMEOUT}s")


def normalize_embedding(embedding: list, target_dim: int = 1024) -> list:
    """
    Normalize embedding dimension to target dimension.
    Truncates if larger, pads with zeros if smaller.
    
    Args:
        embedding: Input embedding vector
        target_dim: Target dimension (default: 1024)
    
    Returns:
        Normalized embedding with target dimension
    """
    if len(embedding) == target_dim:
        return embedding
    if len(embedding) > target_dim:
        return embedding[:target_dim]
    return embedding + [0.0] * (target_dim - len(embedding))


# MiniMax API configuration
# Note: API key loaded dynamically in functions to handle subprocess environments
MINIMAX_ENDPOINT = "https://api.minimax.chat/v1/text/chatcompletion_v2"
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY")
MINIMAX_EMBEDDING_ENDPOINT = "https://api.minimax.chat/v1/embeddings"
MINIMAX_EMBEDDING_MODEL = "nomic-embed-text"  # Now using Ollama

# DeepSeek API configuration (for OpenAI-compatible embeddings + LLM)
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_ENDPOINT = "https://api.deepseek.com/chat/completions"
DEEPSEEK_EMBEDDING_ENDPOINT = "https://api.deepseek.com/embeddings"
DEEPSEEK_EMBEDDING_MODEL = "deepseek-embed"
DEEPSEEK_MODEL = "deepseek-chat"

# Ollama configuration for embeddings (PRIMARY - using nomic-embed-text)
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_EMBED_DIM = 768  # nomic-embed-text produces 768-dim embeddings

# Singleton client to avoid event loop issues
_client = None
_client_lock = asyncio.Lock()


async def get_client():
    """Get or create async httpx client (singleton pattern)"""
    global _client
    async with _client_lock:
        if _client is None:
            _client = httpx.AsyncClient()
        return _client


async def minimax_complete(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: str = "MiniMax-M2.1",
    max_tokens: int = 8192,  # NO TRUNCATION: DeepSeek max is 8192
    temperature: float = 0.1,
    **kwargs
) -> str:
    """
    Call MiniMax API for text completion.
    
    Args:
        prompt: The user prompt
        system_prompt: Optional system prompt for context
        model: Model name (default: MiniMax-M2.1)
        max_tokens: Maximum tokens to generate
        temperature: Temperature for generation (0.1-1.0)
        **kwargs: Additional arguments
    
    Returns:
        Generated text response
    """
    # Load API key dynamically from .zshrc for subprocess compatibility
    minimax_api_key = os.getenv("MINIMAX_API_KEY")
    if not minimax_api_key:
        # Try loading from .zshrc
        try:
            with open(os.path.expanduser("~/.zshrc"), "r") as f:
                for line in f:
                    if line.startswith("export ") and "MINIMAX_API_KEY" in line:
                        parts = line.strip().split("=")
                        var_name = parts[0].replace("export ", "").strip()
                        value = "=".join(parts[1:]).strip('"').strip("'")
                        os.environ[var_name] = value
                        minimax_api_key = value
                        break
        except:
            pass
    
    if not minimax_api_key:
        raise ValueError("MINIMAX_API_KEY not set in environment")
    
    headers = {
        "Authorization": f"Bearer {minimax_api_key}",
        "Content-Type": "application/json"
    }
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        **kwargs
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            MINIMAX_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=LLM_TIMEOUT  # Configurable timeout
        )
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]


async def deepseek_complete(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: str = "deepseek-chat",
    max_tokens: int = 8192,  # NO TRUNCATION: DeepSeek max is 8192
    temperature: float = 0.1,
    hashing_kv: Optional[str] = None,
    **kwargs
) -> str:
    """
    Call DeepSeek API for text completion (OpenAI-compatible).

    This is the PRIMARY LLM for entity extraction to avoid JSON serialization issues.

    Args:
        prompt: The user prompt
        system_prompt: Optional system prompt for context
        model: Model name (default: deepseek-chat)
        max_tokens: Maximum tokens to generate
        temperature: Temperature for generation (0.1-1.0)
        hashing_kv: LightRAG caching key (ignored)
        **kwargs: Additional arguments (ignored by DeepSeek API)

    Returns:
        Generated text response
    """
    # Load API key dynamically from .zshrc for subprocess compatibility
    deepseek_api_key = DEEPSEEK_API_KEY or os.getenv("DEEPSEEK_API_KEY")
    if not deepseek_api_key:
        # Try loading from .zshrc
        try:
            with open(os.path.expanduser("~/.zshrc"), "r") as f:
                for line in f:
                    if line.startswith("export ") and "DEEPSEEK_API_KEY" in line:
                        parts = line.strip().split("=")
                        var_name = parts[0].replace("export ", "").strip()
                        value = "=".join(parts[1:]).strip('"').strip("'")
                        os.environ[var_name] = value
                        deepseek_api_key = value
                        break
        except:
            pass

    if not deepseek_api_key:
        raise ValueError("DEEPSEEK_API_KEY not set in environment")

    headers = {
        "Authorization": f"Bearer {deepseek_api_key}",
        "Content-Type": "application/json"
    }

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    print(f"[DEBUG] DeepSeek API call: max_tokens={max_tokens}, model={model}")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            DEEPSEEK_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=LLM_TIMEOUT  # Configurable timeout
        )
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]


async def minimax_embed_async(texts: List[str], model: str = "nomic-embed-text") -> np.ndarray:
    """
    Generate embeddings using DeepSeek OpenAI-compatible Embedding API.
    
    Falls back to hash-based embeddings if DeepSeek API is not available.
    
    Args:
        texts: List of texts to embed
        model: Embedding model name (not used, DeepSeek uses fixed model)
    
    Returns:
        Numpy array of embedding vectors
    """
    import hashlib
    
    # First try DeepSeek embeddings API (OpenAI-compatible)
    if DEEPSEEK_API_KEY:
        try:
            headers = {
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": DEEPSEEK_EMBEDDING_MODEL,
                "input": texts
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    DEEPSEEK_EMBEDDING_ENDPOINT,
                    json=payload,
                    headers=headers,
                    timeout=EMBEDDING_TIMEOUT
                )
                
                if response.status_code == 200:
                    result = response.json()
                    embeddings = [item["embedding"] for item in result["data"]]
                    return np.array(embeddings, dtype=np.float32)
        except Exception as e:
            print(f"DeepSeek embeddings failed: {e}")
    
    # Fallback: Generate deterministic embeddings using hash + encoding
    embeddings = []
    for text in texts:
        hash_obj = hashlib.sha256(text.encode('utf-8'))
        hash_bytes = hash_obj.digest()
        
        values = [float(b) / 255.0 for b in hash_bytes[:64]]
        expanded = []
        for i in range(1024):
            idx = i % len(values)
            expanded.append(values[idx])
        
        norm = sum(v * v for v in expanded) ** 0.5
        if norm > 0:
            expanded = [v / norm for v in expanded]
        
        embeddings.append(expanded)
    
    return np.array(embeddings, dtype=np.float32)


async def minimax_embed(texts: List[str], model: str = "nomic-embed-text") -> np.ndarray:
    """
    Generate embeddings asynchronously.

    This is the async version that LightRAG expects.

    Args:
        texts: List of texts to embed
        model: Embedding model name

    Returns:
        Numpy array of embedding vectors
    """
    # Import here to avoid circular imports
    import hashlib

    # Priority 1: Try Docker-based BGE-M3 service (1024-dim, compatible)
    try:
        print("Trying Ollama embedding service (nomic-embed-text)...")
        embeddings = await docker_embed_async(texts)
        print(f"✓ Generated {len(embeddings)} embeddings via Ollama (nomic-embed-text)")
        return embeddings
    except Exception as e:
        print(f"Ollama embedding service failed: {e}")
    
    # Priority 2: Try MiniMax embeddings API (1536-dim, incompatible but works)
    if MINIMAX_API_KEY:
        try:
            headers = {
                "Authorization": f"Bearer {MINIMAX_API_KEY}",
                "Content-Type": "application/json"
            }

            # Correct payload format for MiniMax API
            payload = {
                "model": "embo-01",  # Only working model
                "texts": texts,
                "type": "db"
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    MINIMAX_EMBEDDING_ENDPOINT,
                    json=payload,
                    headers=headers,
                    timeout=EMBEDDING_TIMEOUT  # Configurable timeout
                )

                if response.status_code == 200:
                    result = response.json()
                    if "vectors" in result and result["vectors"] is not None:
                        vectors = result["vectors"]
                        if len(vectors) > 0:
                            # Normalize embeddings to 1024-dim
                            normalized_vectors = [normalize_embedding(v, target_dim=1024) for v in vectors]
                            embeddings = np.array(normalized_vectors, dtype=np.float32)
                            dimension = embeddings.shape[1]
                            print(f"✓ Generated {len(embeddings)} embeddings via MiniMax API")
                            print(f"✓ Normalized to {dimension}-dim embeddings")
                            return embeddings
        except Exception as e:
            print(f"MiniMax embeddings failed: {e}")

    # Try DeepSeek embeddings API (OpenAI-compatible)
    if DEEPSEEK_API_KEY:
        try:
            headers = {
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": DEEPSEEK_EMBEDDING_MODEL,
                "input": texts
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    DEEPSEEK_EMBEDDING_ENDPOINT,
                    json=payload,
                    headers=headers,
                    timeout=EMBEDDING_TIMEOUT  # Configurable timeout
                )

                if response.status_code == 200:
                    result = response.json()
                    # DeepSeek returns OpenAI-compatible format
                    embeddings = [item["embedding"] for item in result["data"]]
                    print(f"✓ Generated {len(embeddings)} embeddings via DeepSeek API")
                    return np.array(embeddings, dtype=np.float32)
        except Exception as e:
            print(f"DeepSeek embeddings failed: {e}, using deterministic fallback")

    # Fallback: Generate deterministic embeddings using word hashing
    # This provides consistent, dense 1024-dim vectors for the same text
    print(f"Using deterministic embeddings for {len(texts)} texts")
    
    embeddings = []
    for text in texts:
        embedding = create_deterministic_embedding(text, dim=1024)
        embeddings.append(embedding)
    
    return np.array(embeddings, dtype=np.float32)


def create_deterministic_embedding(text: str, dim: int = 1024) -> np.ndarray:
    """
    Create a deterministic embedding using word hashing with hash expansion.
    Produces dense, consistent 1024-dim vectors.
    """
    import re
    from collections import Counter
    
    # Tokenize
    words = re.findall(r'\b\w+\b', text.lower())
    word_counts = Counter(words)
    
    # Initialize embedding vector
    embedding = np.zeros(dim, dtype=np.float32)
    
    # For each word, add its contribution using seeded random
    for word, count in word_counts.items():
        # Create a hash-based seed (modulo 2**32)
        word_hash = int(hashlib.sha256(word.encode()).hexdigest(), 16) % (2**32)
        
        # Use seed for random direction
        rng = np.random.RandomState(word_hash)
        direction = rng.randn(dim).astype(np.float32)
        direction = direction / max(np.linalg.norm(direction), 1e-10)
        
        # Weight by frequency (log-scaled)
        weight = np.log1p(count)
        
        # Add weighted contribution
        embedding += weight * direction
    
    # Normalize
    norm = np.linalg.norm(embedding)
    if norm > 0:
        embedding = embedding / norm
    
    return embedding


# Simple fallback embedding function using TF-IDF style approach
def fallback_embed(texts: List[str], dim: int = 1024) -> List[List[float]]:
    """
    Fallback embedding function using simple hash-based approach.
    Used when API is not available.
    
    Args:
        texts: List of texts to embed
        dim: Embedding dimension
    
    Returns:
        List of embedding vectors
    """
    import hashlib
    
    embeddings = []
    for text in texts:
        # Create a simple hash-based embedding
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()
        
        # Convert to float array and normalize
        values = [float(b) / 255.0 for b in hash_bytes]
        
        # Pad or truncate to target dimension
        if len(values) < dim:
            values.extend([0.0] * (dim - len(values)))
        else:
            values = values[:dim]
        
        # Normalize
        norm = sum(v * v for v in values) ** 0.5
        if norm > 0:
            values = [v / norm for v in values]
        
        embeddings.append(values)
    
    return embeddings


# Docker-based BGE-M3 Embeddings Service
# Use this when torch installation is not available
# Removed: was Docker BGE-M3 URL
USE_DOCKER_EMBEDDINGS = os.getenv("USE_DOCKER_EMBEDDINGS", "false").lower() == "true"

async def docker_embed_async(texts: List[str]) -> np.ndarray:
    """
    Generate embeddings using Ollama directly with nomic-embed-text.
    
    Uses local Ollama at http://127.0.0.1:11434
    
    Args:
        texts: List of texts to embed
    
    Returns:
        Numpy array of 768-dimensional embedding vectors (nomic-embed-text)
    """
    if not texts:
        return np.array([], dtype=np.float32).reshape(0, OLLAMA_EMBED_DIM)
    
    try:
        embeddings = []
        async with httpx.AsyncClient(timeout=EMBEDDING_TIMEOUT) as client:
            for text in texts:
                response = await client.post(
                    f"{OLLAMA_HOST}/api/embeddings",
                    json={
                        "model": OLLAMA_EMBED_MODEL,
                        "prompt": text
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    embedding = result.get("embedding", [])
                    embeddings.append(embedding)
                else:
                    raise Exception(f"Ollama returned {response.status_code}: {response.text}")
        
        print(f"✓ Generated {len(embeddings)} embeddings via Ollama ({OLLAMA_EMBED_MODEL})")
        return np.array(embeddings, dtype=np.float32)
                
    except Exception as e:
        print(f"Ollama embedding service failed: {e}")
        raise


# Register with LightRAG - using DeepSeek for LLM to avoid JSON serialization issues
llm_model_func = deepseek_complete  # Primary: DeepSeek for entity extraction

# Select embedding function based on configuration
if USE_DOCKER_EMBEDDINGS:
    embedding_func = docker_embed_async  # Use Ollama with nomic-embed-text (direct, not Docker)
    print("✓ Using Ollama embeddings (nomic-embed-text)")
else:
    embedding_func = minimax_embed  # Use API-based embeddings (with fallback)

# Alias for deepseek_embed (used by some scripts)
deepseek_embed = minimax_embed


async def llm_complete_with_provider(
    prompt: str,
    system_prompt: Optional[str] = None,
    provider: str = "deepseek",
    fallback_provider: Optional[str] = None,
    max_tokens: int = 8192,  # NO TRUNCATION: DeepSeek max is 8192
    temperature: float = 0.4,
    **kwargs
) -> str:
    """
    Generate LLM completion with provider selection and fallback support.
    
    Args:
        prompt: The user prompt
        system_prompt: Optional system prompt for context
        provider: Primary LLM provider ("deepseek" or "minimax")
        fallback_provider: Fallback provider if primary fails ("deepseek", "minimax", or None)
        max_tokens: Maximum tokens to generate
        temperature: Temperature for generation
        **kwargs: Additional arguments
    
    Returns:
        Generated text response
    """
    print(f"[DEBUG] llm_complete_with_provider called: provider={provider}, max_tokens={max_tokens}")
    providers_to_try = [provider]
    if fallback_provider and fallback_provider != provider:
        providers_to_try.append(fallback_provider)
    
    last_error = None
    
    for prov in providers_to_try:
        try:
            if prov == "minimax":
                print(f"[LLM] Using MiniMax for generation...")
                return await minimax_complete(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    model="MiniMax-M2.5",
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
            else:  # Default to DeepSeek
                print(f"[LLM] Using DeepSeek for generation...")
                return await deepseek_complete(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    model="deepseek-chat",
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
        except Exception as e:
            print(f"[LLM] Provider '{prov}' failed: {e}")
            last_error = e
            continue
    
    # All providers failed
    raise last_error or Exception("All LLM providers failed")
