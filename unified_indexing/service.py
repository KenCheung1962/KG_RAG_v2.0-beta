#!/usr/bin/env python3
#!/usr/bin/env python3
"""
LightRAG Service - Production-ready Knowledge Graph RAG Service.

This module provides a service class for querying the LightRAG knowledge graph
with DeepSeek fallback for enhanced search capabilities.
"""
# Apply ultra-early patch for JsonKVStorage serialization
try:
    from . import ultra_early_patch
except ImportError:
    import ultra_early_patch

import asyncio
import argparse
import os
import re
from typing import Optional, Dict, Any
from functools import lru_cache
import logging

try:
    # Try external lightrag-hku package first
    from lightrag_hku import LightRAG, QueryParam
except ImportError:
    # Fallback to installed lightrag package
    from lightrag import LightRAG, QueryParam
from lightrag.utils import setup_logger, EmbeddingFunc

# Handle relative imports for when running as module vs standalone
try:
    from lightrag_local.config import (
        WORKING_DIR, CHUNK_TOKEN_SIZE, CHUNK_OVERLAP_TOKEN_SIZE,
        ENTITY_TYPES, DEFAULT_QUERY_MODE, TOP_K, CHUNK_TOP_K, EMBEDDING_DIM
    )
    from lightrag_local.minimax import deepseek_complete, minimax_embed
    from lightrag_local.comprehensive_patch import apply_comprehensive_patch
    from lightrag_local.httpx_patch import apply_patch as apply_httpx_patch
except ImportError:
    from .config import (
        WORKING_DIR, CHUNK_TOKEN_SIZE, CHUNK_OVERLAP_TOKEN_SIZE,
        ENTITY_TYPES, DEFAULT_QUERY_MODE, TOP_K, CHUNK_TOP_K, EMBEDDING_DIM
    )
    from .minimax import deepseek_complete, minimax_embed
    from .comprehensive_patch import apply_comprehensive_patch
    from .httpx_patch import apply_patch as apply_httpx_patch

# Configure logging
setup_logger("lightrag", level="INFO")
logger = logging.getLogger("lightrag")


# =============================================================================
# Query Cache for Repeated Queries (Fix 2: Optimize search speed)
# =============================================================================

# Simple in-memory cache for query results (thread-safe)
_query_cache: Dict[str, tuple[str, float]] = {}
_CACHE_MAX_SIZE = 100
_CACHE_TTL_SECONDS = 300  # 5 minutes cache TTL


def _get_cached_result(query: str) -> Optional[str]:
    """Get cached result for a query if available and not expired."""
    import time
    if query in _query_cache:
        result, timestamp = _query_cache[query]
        if time.time() - timestamp < _CACHE_TTL_SECONDS:
            logger.info(f"Cache hit for query: {query[:50]}...")
            return result
        else:
            # Cache expired, remove entry
            del _query_cache[query]
    return None


def _cache_result(query: str, result: str) -> None:
    """Cache a query result."""
    global _query_cache
    if len(_query_cache) >= _CACHE_MAX_SIZE:
        # Remove oldest entry (first item)
        _query_cache.pop(next(iter(_query_cache)))
    _query_cache[query] = (result, time.time())
    logger.debug(f"Cached result for query: {query[:50]}...")


import time  # Import time for cache TTL checks


# Wrap embedding function with EmbeddingFunc wrapper
embedding_function = EmbeddingFunc(
    embedding_dim=EMBEDDING_DIM,
    max_token_size=8192,
    func=minimax_embed
)


# =============================================================================
# DeepSeek API Integration
# =============================================================================

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"


async def deepseek_fallback(query: str) -> Dict[str, Any]:
    """
    Query DeepSeek API when local knowledge base has no relevant information.
    
    Args:
        query: The search query
        
    Returns:
        Dictionary with 'answer' and 'sources' keys
    """
    if not DEEPSEEK_API_KEY:
        logger.warning("DEEPSEEK_API_KEY not configured")
        return {
            "answer": "🔑 DeepSeek API key not configured. Please set DEEPSEEK_API_KEY in your environment variables.",
            "sources": [],
            "error": "API key missing"
        }
    
    try:
        import httpx
        
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful research assistant. Provide accurate, well-cited information about the query."
                },
                {
                    "role": "user", 
                    "content": f"Please research and provide information about: {query}"
                }
            ],
            "max_tokens": 8192,  # NO TRUNCATION: DeepSeek max is 8192
            "temperature": 0.2
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                DEEPSEEK_API_URL,
                json=payload,
                headers=headers,
                timeout=60.0
            )
            response.raise_for_status()
            result = response.json()
            
            # Extract answer
            answer = result["choices"][0]["message"]["content"]
            
            # No structured sources in DeepSeek response, use query as citation
            sources = [{"query": query}]
            
            return {
                "answer": answer,
                "sources": sources,
                "raw_response": result
            }
            
    except Exception as e:
        logger.error(f"DeepSeek fallback failed: {e}")
        return {
            "answer": f"DeepSeek fallback failed: {str(e)}",
            "sources": [],
            "error": str(e)
        }


def detect_no_context_response(text: str) -> bool:
    """
    Detect if the response indicates no relevant information was found in local knowledge base.
    
    Args:
        text: The response text from RAG query
        
    Returns:
        True if no context was found
    """
    # This function now just checks for "no context" patterns
    # Word count check moved to should_trigger_fallback()
    if not text or not isinstance(text, str):
        return True
    
    # Common "no context" patterns
    no_context_patterns = [
        r"no (relevant|available|sufficient|related|information|data)",
        r"based on the provided context.*no information",
        r"context.*does not contain",
        r"don't have enough information",
        r"cannot find.*information",
        r"couldn't find.*information",
        r"don't have any.*about",
        r"no (local|knowledge base|document).*found",
        r"unable to find.*in the (knowledge|context)",
        r"insufficient.*context",
        r"the knowledge base.*does not have",
        r"does not contain.*any",
        r"not.*in the (knowledge|local).*base",
        r"i don't have information about",
        r"i cannot answer.*based on",
        r"there is no.*in the provided",
        r"context.*does not.*provide",
        r"cannot locate.*in the",
        r"does not appear.*in the",
    ]
    
    text_lower = text.lower()
    for pattern in no_context_patterns:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    
    # Check if the response is very short and generic
    short_no_info = [
        "i don't know",
        "no information",
        "cannot answer",
        "unable to help",
    ]
    
    if len(text.strip()) < 100:
        for phrase in short_no_info:
            if phrase in text_lower:
                return True
    
    return False


def should_trigger_fallback(response: str) -> tuple[bool, str]:
    """
    Check if DeepSeek fallback should trigger.
    
    Only triggers if LLM explicitly says it has no relevant information.
    We trust retrieved context even if response is short but informative.
    
    Args:
        response: The response text from RAG query
        
    Returns:
        Tuple of (should_trigger: bool, reason: str)
    """
    # Only trigger fallback if LLM explicitly says no context
    # We trust retrieved context even if response is brief but informative
    if detect_no_context_response(response):
        word_count = len(response.split()) if response else 0
        return True, f"LLM indicates no relevant context ({word_count} words)"
    
    return False, ""


def format_deepseek_response(query: str, deepseek_result: Dict[str, Any]) -> str:
    """
    Format DeepSeek response with proper citation for the References section.

    Args:
        query: Original user query
        deepseek_result: Result from deepseek_fallback

    Returns:
        Formatted response with DeepSeek citation (clean format)
    """
    answer = deepseek_result.get("answer", "")
    sources = deepseek_result.get("sources", [])

    # Check if there are real sources (not just the fallback query)
    has_real_sources = False
    if sources:
        for source in sources:
            if isinstance(source, str):
                if source.strip() and source.lower() != "unknown":
                    has_real_sources = True
                    break
            elif isinstance(source, dict):
                url = source.get("url", "").strip()
                title = source.get("title", "").strip()
                if (url and url.lower() != "unknown") or (title and title.lower() != "unknown"):
                    has_real_sources = True
                    break

    # Build response - skip References section if only fallback query
    formatted = f"{answer}\n"

    # Add References section only if there are real sources
    if has_real_sources:
        formatted += "\nReferences\n"
        # Add source URLs (filter out "Unknown" sources)
        for i, source in enumerate(sources[:3], start=1):  # Limit to 3 sources
            if isinstance(source, str):
                # Filter out "Unknown" references
                if source.strip() and source.lower() != "unknown":
                    formatted += f"* [{i}] {source}\n"
            elif isinstance(source, dict):
                url = source.get("url", "").strip()
                title = source.get("title", "").strip()
                # Filter out references with "Unknown" or empty source/title
                if url or title:
                    if url.lower() != "unknown" and title.lower() != "unknown":
                        formatted += f"* [{i}] {title}: {url}\n" if title else f"* [{i}] {url}\n"

    return formatted


# =============================================================================
# LightRAG Service Class
# =============================================================================


class LightRAGService:
    """
    Production LightRAG service with DeepSeek integration.
    """
    
    _instance = None
    _rag = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def _fix_references(self, text: str) -> str:
        """
        Post-process query result to fix reference numbering and format.
        - Renumbers ALL references starting from [1]
        - Removes duplicate references to the same document
        - Consolidates reference list
        """
        if not text or not isinstance(text, str):
            return text or ""
        
        import re
        
        try:
            # Step 1: Find all inline references like [1], [2, 3], [4-6]
            inline_refs = re.findall(r'\[([\d,\s\-\–]+)\]', text)
            
            # Step 2: Collect unique document references from the References section
            ref_list_match = re.search(r'\n\s*References\s*\n(.*)$', text, re.DOTALL | re.IGNORECASE)
            ref_items = []
            
            if ref_list_match:
                ref_section = ref_list_match.group(1)
                # Parse each line: "* [X] Document Name" or "- [X] Document Name"
                for line in ref_section.split('\n'):
                    line = line.strip()
                    if line.startswith('*') or line.startswith('•') or line.startswith('-'):
                        match = re.match(r'[\*\•\-]\s*\[(\d+)\]\s*(.+)', line)
                        if match:
                            orig_num = int(match.group(1))
                            doc_name = match.group(2).strip()
                            
                            # Fix 1: Filter out "Unknown: Unknown" references
                            # Skip references with empty source or "Unknown" source
                            if doc_name and doc_name.lower() not in ['unknown', 'unknown: unknown', '']:
                                ref_items.append({'orig': orig_num, 'doc': doc_name})
            
            # Step 3: Create mapping from original number to new number (deduplicated)
            # Sort by original number to maintain order
            ref_items.sort(key=lambda x: x['orig'])
            
            orig_to_new = {}
            seen_docs = {}
            next_num = 1
            
            for item in ref_items:
                doc = item['doc']
                if doc not in seen_docs:
                    seen_docs[doc] = next_num
                    next_num += 1
                orig_to_new[item['orig']] = seen_docs[doc]
            
            # Step 4: If no References section found, create mapping from inline refs only
            if not orig_to_new:
                # Find all unique original numbers
                all_orig_nums = set()
                for ref_group in inline_refs:
                    # Parse numbers from group like "2, 3" or "2"
                    nums = re.findall(r'\d+', ref_group)
                    for n in nums:
                        all_orig_nums.add(int(n))
                
                # Create sequential mapping
                sorted_nums = sorted(all_orig_nums)
                for i, orig in enumerate(sorted_nums):
                    orig_to_new[orig] = i + 1
            
            # Step 5: Replace inline references with new numbers
            def replace_inline(match):
                ref_group = match.group(1)
                # Parse the reference group (could be single num or list)
                nums = re.findall(r'\d+', ref_group)
                new_nums = [str(orig_to_new.get(int(n), n)) for n in nums]
                return '[' + ', '.join(new_nums) + ']'
            
            text = re.sub(r'\[([\d,\s\-\–]+)\]', replace_inline, text)
            
            # Step 6: Rebuild the References section with new numbers (deduplicated)
            if ref_items:
                new_refs = []
                for doc, new_num in sorted(seen_docs.items(), key=lambda x: x[1]):
                    new_refs.append(f"* [{new_num}] {doc}")
                
                # Replace the old References section
                text = re.sub(
                    r'\n\s*References\s*\n.*$',
                    '\n\nReferences\n' + '\n'.join(new_refs),
                    text,
                    flags=re.DOTALL | re.IGNORECASE
                )
            
            # Step 7: Fix other numeric references (pages, sections, figures)
            text = re.sub(r'p\.(\d+)', lambda m: 'p.' + str(int(m.group(1)) + 1), text)
            text = re.sub(r'Sec\.(\d+)', lambda m: 'Sec.' + str(int(m.group(1)) + 1), text)
            text = re.sub(r'Fig\.(\d+)', lambda m: 'Fig.' + str(int(m.group(1)) + 1), text)
            text = re.sub(r'Table\.(\d+)', lambda m: 'Table.' + str(int(m.group(1)) + 1), text)
            
        except Exception as e:
            logger.warning(f"Reference fixing failed: {e}")
            import traceback
            logger.warning(traceback.format_exc())
            return text
        
        except Exception as e:
            logger.warning(f"Reference fixing failed: {e}")
            import traceback
            logger.warning(traceback.format_exc())
            return text
        
        return text
    
    def _format_query_response(self, text: str, query: str) -> str:
        """
        Format query response according to Boss's requirements:
        1. Remove irrelevant context disclaimers
        2. Add proper heading hierarchy with bold formatting
        3. Format tables with boundaries
        4. Use proper heading sizes
        """
        if not text or not isinstance(text, str):
            return text or ""
        
        import re
        
        try:
            # Step 1: Remove irrelevant context disclaimers
            disclaimer_patterns = [
                r"(?i)^.*the (provided )?context (does not|doesn't|doesn.t) (contain|have|include).*$",
                r"(?i)^.*based on the (provided )?context.*$",
                r"(?i)^.*no (relevant )?information (was|has been|is) (found|provided).*$",
                r"(?i)^.*i (cannot|couldn.t|could not) find.*$",
                r"(?i)^.*i don.t have .* in my (knowledge|context).*$",
                r"(?i)^.*this (response|information) is based on.*$",
                r"(?i)^\s*\*note:.*context\s*\*\s*$",
                r"(?i)^\s*\*note:.*irrelevant\s*\*\s*$",
            ]
            
            lines = text.split('\n')
            filtered_lines = []
            skip_next = 0
            
            for i, line in enumerate(lines):
                if skip_next > 0:
                    skip_next -= 1
                    continue
                
                # Check if line matches any disclaimer pattern
                is_disclaimer = False
                for pattern in disclaimer_patterns:
                    if re.match(pattern, line.strip()):
                        is_disclaimer = True
                        break
                
                # Also check if this line + next few lines form a disclaimer paragraph
                if not is_disclaimer:
                    # Check multi-line disclaimers (current line + next 2 lines)
                    check_text = '\n'.join(lines[i:i+3]).lower()
                    if re.search(r"context.*(does not|doesn't|have|contain|provide)", check_text):
                        if re.search(r"(no|not|irrelevant|cannot)", check_text):
                            is_disclaimer = True
                            skip_next = 2  # Skip next 2 lines too
                
                if not is_disclaimer:
                    filtered_lines.append(line)
            
            text = '\n'.join(filtered_lines)
            
            # Step 2: Extract title from query and create proper heading
            # Convert query to title case
            title = query.strip().rstrip('?').rstrip('.').title()
            
            # Add # title at the beginning if not present
            if not text.strip().startswith('#'):
                text = f"# {title}\n\n{text}"
            else:
                # Ensure first heading is # (not ##)
                text = re.sub(r'^#+\s+', '# ', text, count=1, flags=re.MULTILINE)
            
            # Step 3: Add bold formatting to section headers
            # Make ## headers bold and ensure proper hierarchy
            def make_bold_header(match):
                level = match.group(1)  # ## or ###
                content = match.group(2).strip()
                return f"{level} **{content}**"
            
            # Process ### headers (make bold)
            text = re.sub(r'^###\s+(.+)$', make_bold_header, text, flags=re.MULTILINE)
            
            # Process ## headers (make bold and bigger)
            text = re.sub(r'^##\s+(.+)$', make_bold_header, text, flags=re.MULTILINE)
            
            # Step 4: Format tables with boundaries
            # Find markdown tables and add proper borders
            def ensure_table_borders(table_match):
                table_text = table_match.group(0)
                lines = table_text.split('\n')
                
                # Rebuild with proper borders
                new_lines = []
                for line in lines:
                    line = line.strip()
                    if line:
                        if not line.startswith('|'):
                            line = '|' + line
                        if not line.endswith('|'):
                            line = line + '|'
                        new_lines.append(line)
                
                return '\n'.join(new_lines)
            
            # Apply table border fixes
            text = re.sub(r'(?:\|[^\n]+\|[\n])+(?:\|[^\n]+\|)', ensure_table_borders, text)
            
            # Step 5: Clean up excessive newlines
            text = re.sub(r'\n{4,}', '\n\n\n', text)
            text = text.strip()
            
            return text
            
        except Exception as e:
            logger.warning(f"Response formatting failed: {e}")
            import traceback
            logger.warning(traceback.format_exc())
            return text
    
    async def initialize(self) -> None:
        """Initialize LightRAG."""
        if self._initialized:
            return

        # Apply patches
        apply_comprehensive_patch()
        apply_httpx_patch()

        logger.info("Initializing LightRAG service...")
        
        self._rag = LightRAG(
            working_dir=WORKING_DIR,
            embedding_func=embedding_function,
            llm_model_func=deepseek_complete,
            chunk_token_size=CHUNK_TOKEN_SIZE,
            chunk_overlap_token_size=CHUNK_OVERLAP_TOKEN_SIZE,
            addon_params={"language": "English", "entity_types": ENTITY_TYPES},
            enable_llm_cache=True
        )
        
        await self._rag.initialize_storages()
        self._initialized = True
        logger.info("LightRAG service initialized successfully")
    
    async def query(
        self,
        question: str,
        mode: str = DEFAULT_QUERY_MODE,
        response_type: str = "Multiple Paragraphs",
        use_deepseek_fallback: bool = True,
        timeout_seconds: float = 60.0  # Increased from 30s to 60s for complex queries
    ) -> str:
        """
        Query the knowledge graph with DeepSeek fallback.

        Args:
            question: The question to ask
            mode: Query mode (local, global, hybrid, naive)
            response_type: Format of response
            use_deepseek_fallback: If True, query DeepSeek when local context is empty
            timeout_seconds: Timeout for the query in seconds

        Returns:
            Generated answer from local RAG or DeepSeek fallback
        """
        if not self._initialized:
            await self.initialize()

        if not self._rag:
            raise RuntimeError("LightRAG not properly initialized")

        # Fix 2: Check cache for repeated queries
        cache_key = f"{mode}:{response_type}:{question}"
        cached_result = _get_cached_result(cache_key)
        if cached_result:
            return cached_result

        # Query local RAG first with timeout and faster settings
        logger.info(f"Querying local RAG: {question[:100]}...")
        try:
            # Enable rerank with smaller TOP_K for quality + speed balance
            result = await asyncio.wait_for(
                self._rag.aquery(
                    question,
                    param=QueryParam(
                        mode=mode,
                        response_type=response_type,
                        top_k=TOP_K,
                        chunk_top_k=CHUNK_TOP_K,
                        enable_rerank=True  # Enable rerank for better quality
                    )
                ),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.warning(f"Query timed out after {timeout_seconds}s")
            # Return timeout message
            return f"Query timed out after {timeout_seconds} seconds. Please try again with a simpler query or reduce TOP_K settings."

        # Issue 1: Early exit if high confidence result found
        # Check if result is good enough to skip fallback
        word_count = len(result.split()) if result else 0
        if word_count >= 150 and not detect_no_context_response(result):
            # High confidence result - skip DeepSeek fallback
            logger.info(f"High confidence result ({word_count} words), skipping DeepSeek fallback")
            # Post-process result to fix references (handle None)
            if result:
                result = self._fix_references(result)
            # Cache the result for repeated queries
            _cache_result(cache_key, result)
            return result

        # Check if we need DeepSeek fallback
        should_fallback, fallback_reason = should_trigger_fallback(result)
        if use_deepseek_fallback and should_fallback:
            logger.info(f"No local context found for: {question[:100]}...")
            logger.info(f"Falling back to DeepSeek AI (reason: {fallback_reason})...")

            # Query DeepSeek with timeout
            try:
                deepseek_result = await asyncio.wait_for(
                    deepseek_fallback(question),
                    timeout=30.0  # 30 second timeout for DeepSeek
                )

                if deepseek_result.get("answer") and not deepseek_result.get("error"):
                    # Format response with DeepSeek citation
                    result = format_deepseek_response(question, deepseek_result)
                    logger.info("DeepSeek fallback successful")
                else:
                    logger.warning(f"DeepSeek fallback failed: {deepseek_result.get('error')}")
                    # Keep the original "no context" response
                    if result:
                        result = result + "\n\n*Note: DeepSeek AI is unavailable.*"
            except asyncio.TimeoutError:
                logger.warning("DeepSeek fallback timed out")
                if result:
                    result = result + "\n\n*Note: DeepSeek AI timed out.*"

        # Post-process result to fix references (handle None)
        if result:
            result = self._fix_references(result)

        # Fix 2: Cache the result for repeated queries
        _cache_result(cache_key, result)

        return result
    
    async def add_documents(self, documents: list[str], metadata: list[dict] = None) -> None:
        """Add new documents to the knowledge graph."""
        if not self._initialized:
            await self.initialize()
        
        if not self._rag:
            raise RuntimeError("LightRAG not properly initialized")
        
        await self._rag.ainsert(documents)
    
    async def close(self) -> None:
        """Cleanup resources."""
        if self._rag:
            await self._rag.finalize_storages()
        self._initialized = False
        logger.info("LightRAG service closed")
    
    @property
    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        return self._initialized


async def get_service() -> LightRAGService:
    """Get or create the LightRAG service instance."""
    service = LightRAGService()
    if not service._initialized:
        await service.initialize()
    return service


async def cli():
    """CLI interface for LightRAG."""
    parser = argparse.ArgumentParser(description="LightRAG CLI - Knowledge Graph RAG System")
    parser.add_argument("--query", "-q", help="Query to run")
    parser.add_argument("--mode", "-m", default=DEFAULT_QUERY_MODE,
                       choices=["local", "global", "hybrid", "naive"],
                       help="Query mode (default: hybrid)")
    parser.add_argument("--init", action="store_true", help="Initialize service only")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    
    args = parser.parse_args()
    
    if args.init:
        service = await get_service()
        print("LightRAG service initialized. Ready to query.")
        print("Use --query to run a query, or --interactive for interactive mode.")
    elif args.interactive:
        service = await get_service()
        print("=" * 60)
        print("LightRAG Interactive Mode")
        print("Type 'quit' or 'exit' to exit.")
        print("=" * 60)
        
        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() in ['quit', 'exit']:
                    break
                if not query:
                    continue
                
                result = await service.query(query, mode=args.mode)
                print(f"\n{'=' * 60}")
                print(f"Answer:")
                print(result)
                print(f"{'=' * 60}")
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
        
        await service.close()
        print("Goodbye!")
    elif args.query:
        service = await get_service()
        result = await service.query(args.query, mode=args.mode)
        print(f"\n{'=' * 60}")
        print(f"Query: {args.query}")
        print(f"Mode: {args.mode}")
        print(f"{'=' * 60}")
        print(result)
        await service.close()
    else:
        parser.print_help()


def run_query(service: LightRAGService, query: str, mode: str = DEFAULT_QUERY_MODE, response_type: str = "Multiple Paragraphs") -> str:
    """
    Synchronous wrapper for async query.
    Use this for synchronous contexts like Streamlit.
    """
    return asyncio.run(service.query(query, mode=mode, response_type=response_type))


if __name__ == "__main__":
    asyncio.run(cli())
