#!/usr/bin/env python3
#!/usr/bin/env python3
"""
Retry Wrapper with Exponential Backoff for LightRAG.

This module provides retry logic for embedding and LLM calls to handle
transient failures with exponential backoff.

Usage:
    from retry_wrapper import retry_embed, retry_llm
"""
import asyncio
import time
import logging
from typing import Callable, Any, TypeVar, Optional
from functools import wraps
import httpx

logger = logging.getLogger("retry_wrapper")

# Retry configuration
MAX_RETRIES = 3
INITIAL_DELAY = 1.0  # 1 second
BACKOFF_MULTIPLIER = 2.0  # Exponential backoff: 1s, 2s, 4s
MAX_DELAY = 30.0  # Maximum delay between retries

# Timeout configuration
EMBEDDING_TIMEOUT = 120.0  # 2 minutes for embedding
LLM_TIMEOUT = 180.0  # 3 minutes for LLM

T = TypeVar('T')


def retry_with_exponential_backoff(
    max_retries: int = MAX_RETRIES,
    initial_delay: float = INITIAL_DELAY,
    backoff_multiplier: float = BACKOFF_MULTIPLIER,
    max_delay: float = MAX_DELAY,
    include_timeout_errors: bool = True,
    retry_on_exceptions: tuple = (httpx.RequestError, httpx.TimeoutException, httpx.NetworkError)
):
    """
    Decorator for adding exponential backoff retry logic to async functions.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries (seconds)
        backoff_multiplier: Multiplier for exponential backoff
        max_delay: Maximum delay between retries
        include_timeout_errors: Whether to retry on timeout errors
        retry_on_exceptions: Tuple of exception types to retry on
    
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries + 1):  # +1 for initial attempt
                try:
                    return await func(*args, **kwargs)
                    
                except retry_on_exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(
                            f"[{func.__name__}] Failed after {max_retries + 1} attempts. "
                            f"Last error: {type(e).__name__}: {str(e)[:200]}"
                        )
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(initial_delay * (backoff_multiplier ** attempt), max_delay)
                    
                    # Add jitter to prevent thundering herd
                    jitter = delay * 0.1 * (time.time() % 1)
                    actual_delay = delay + jitter
                    
                    logger.warning(
                        f"[{func.__name__}] Attempt {attempt + 1}/{max_retries + 1} failed: "
                        f"{type(e).__name__}: {str(e)[:100]}. "
                        f"Retrying in {actual_delay:.1f}s..."
                    )
                    
                    await asyncio.sleep(actual_delay)
                    
                except Exception as e:
                    # Don't retry on unexpected exceptions
                    logger.error(
                        f"[{func.__name__}] Unexpected error: {type(e).__name__}: {str(e)[:200]}"
                    )
                    raise
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected retry failure")
        
        return wrapper
    return decorator


class RetryWrapper:
    """
    Wrapper class for adding retry logic to existing functions.
    
    Usage:
        retry_embed = RetryWrapper.wrap_async(
            minimax_embed,
            timeout=120.0,
            max_retries=3
        )
    """
    
    @staticmethod
    def wrap_async(
        func: Callable[..., Any],
        timeout: float = LLM_TIMEOUT,
        max_retries: int = MAX_RETRIES,
        initial_delay: float = INITIAL_DELAY,
        backoff_multiplier: float = BACKOFF_MULTIPLIER,
        max_delay: float = MAX_DELAY
    ) -> Callable[..., Any]:
        """
        Wrap an async function with retry logic.
        
        Args:
            func: Async function to wrap
            timeout: Timeout for each attempt
            max_retries: Maximum retry attempts
            initial_delay: Initial delay between retries
            backoff_multiplier: Exponential backoff multiplier
            max_delay: Maximum delay between retries
        
        Returns:
            Wrapped function with retry logic
        """
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    # Add timeout to the function call
                    return await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=timeout
                    )
                    
                except (asyncio.TimeoutError, httpx.TimeoutException) as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(
                            f"[{func.__name__}] Timeout after {max_retries + 1} attempts"
                        )
                        raise
                    
                    delay = min(initial_delay * (backoff_multiplier ** attempt), max_delay)
                    jitter = delay * 0.1 * (time.time() % 1)
                    actual_delay = delay + jitter
                    
                    logger.warning(
                        f"[{func.__name__}] Timeout on attempt {attempt + 1}/{max_retries + 1}. "
                        f"Retrying in {actual_delay:.1f}s..."
                    )
                    
                    await asyncio.sleep(actual_delay)
                    
                except (httpx.RequestError, httpx.NetworkError) as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(
                            f"[{func.__name__}] Network error after {max_retries + 1} attempts: {e}"
                        )
                        raise
                    
                    delay = min(initial_delay * (backoff_multiplier ** attempt), max_delay)
                    jitter = delay * 0.1 * (time.time() % 1)
                    actual_delay = delay + jitter
                    
                    logger.warning(
                        f"[{func.__name__}] Network error on attempt {attempt + 1}/{max_retries + 1}: "
                        f"{str(e)[:100]}. Retrying in {actual_delay:.1f}s..."
                    )
                    
                    await asyncio.sleep(actual_delay)
                    
                except Exception as e:
                    logger.error(
                        f"[{func.__name__}] Unexpected error: {type(e).__name__}: {str(e)[:200]}"
                    )
                    raise
            
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected retry failure")
        
        return wrapper


async def retry_embed(
    texts: list,
    embed_func: Callable[..., Any] = None,
    timeout: float = EMBEDDING_TIMEOUT,
    max_retries: int = MAX_RETRIES
) -> Any:
    """
    Retry embedding with exponential backoff.
    
    Args:
        texts: List of texts to embed
        embed_func: Embedding function to use (defaults to minimax_embed)
        timeout: Timeout for each attempt
        max_retries: Maximum retry attempts
    
    Returns:
        Embedding vectors
    """
    if embed_func is None:
        from minimax import minimax_embed as embed_func
    
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return await asyncio.wait_for(
                embed_func(texts),
                timeout=timeout
            )
            
        except (asyncio.TimeoutError, httpx.TimeoutException) as e:
            last_exception = e
            
            if attempt == max_retries:
                logger.error(f"Embedding timeout after {max_retries + 1} attempts")
                raise
            
            delay = min(INITIAL_DELAY * (BACKOFF_MULTIPLIER ** attempt), MAX_DELAY)
            jitter = delay * 0.1 * (time.time() % 1)
            actual_delay = delay + jitter
            
            logger.warning(
                f"Embedding timeout (attempt {attempt + 1}/{max_retries + 1}). "
                f"Retrying in {actual_delay:.1f}s..."
            )
            
            await asyncio.sleep(actual_delay)
            
        except (httpx.RequestError, httpx.NetworkError) as e:
            last_exception = e
            
            if attempt == max_retries:
                logger.error(f"Embedding network error after {max_retries + 1} attempts: {e}")
                raise
            
            delay = min(INITIAL_DELAY * (BACKOFF_MULTIPLIER ** attempt), MAX_DELAY)
            jitter = delay * 0.1 * (time.time() % 1)
            actual_delay = delay + jitter
            
            logger.warning(
                f"Embedding network error (attempt {attempt + 1}/{max_retries + 1}): "
                f"{str(e)[:100]}. Retrying in {actual_delay:.1f}s..."
            )
            
            await asyncio.sleep(actual_delay)
        
        except Exception as e:
            logger.error(f"Embedding unexpected error: {type(e).__name__}: {str(e)[:200]}")
            raise
    
    raise last_exception


async def retry_llm(
    prompt: str,
    llm_func: Callable[..., Any] = None,
    timeout: float = LLM_TIMEOUT,
    max_retries: int = MAX_RETRIES,
    **kwargs
) -> str:
    """
    Retry LLM call with exponential backoff.
    
    Args:
        prompt: Prompt to send to LLM
        llm_func: LLM function to use (defaults to deepseek_complete)
        timeout: Timeout for each attempt
        max_retries: Maximum retry attempts
        **kwargs: Additional arguments for LLM function
    
    Returns:
        LLM response text
    """
    if llm_func is None:
        from minimax import deepseek_complete as llm_func
    
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return await asyncio.wait_for(
                llm_func(prompt, **kwargs),
                timeout=timeout
            )
            
        except (asyncio.TimeoutError, httpx.TimeoutException) as e:
            last_exception = e
            
            if attempt == max_retries:
                logger.error(f"LLM timeout after {max_retries + 1} attempts")
                raise
            
            delay = min(INITIAL_DELAY * (BACKOFF_MULTIPLIER ** attempt), MAX_DELAY)
            jitter = delay * 0.1 * (time.time() % 1)
            actual_delay = delay + jitter
            
            logger.warning(
                f"LLM timeout (attempt {attempt + 1}/{max_retries + 1}). "
                f"Retrying in {actual_delay:.1f}s..."
            )
            
            await asyncio.sleep(actual_delay)
            
        except (httpx.RequestError, httpx.NetworkError) as e:
            last_exception = e
            
            if attempt == max_retries:
                logger.error(f"LLM network error after {max_retries + 1} attempts: {e}")
                raise
            
            delay = min(INITIAL_DELAY * (BACKOFF_MULTIPLIER ** attempt), MAX_DELAY)
            jitter = delay * 0.1 * (time.time() % 1)
            actual_delay = delay + jitter
            
            logger.warning(
                f"LLM network error (attempt {attempt + 1}/{max_retries + 1}): "
                f"{str(e)[:100]}. Retrying in {actual_delay:.1f}s..."
            )
            
            await asyncio.sleep(actual_delay)
        
        except Exception as e:
            logger.error(f"LLM unexpected error: {type(e).__name__}: {str(e)[:200]}")
            raise
    
    raise last_exception


# Pre-configured wrappers for common use cases
retry_docker_embed = RetryWrapper.wrap_async(
    None,  # Will be set at runtime
    timeout=EMBEDDING_TIMEOUT,
    max_retries=MAX_RETRIES
)

retry_deepseek_complete = RetryWrapper.wrap_async(
    None,  # Will be set at runtime
    timeout=LLM_TIMEOUT,
    max_retries=MAX_RETRIES
)

retry_minimax_complete = RetryWrapper.wrap_async(
    None,  # Will be set at runtime
    timeout=LLM_TIMEOUT,
    max_retries=MAX_RETRIES
)
