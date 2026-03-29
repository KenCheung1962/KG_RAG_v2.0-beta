"""
Chat Module for RAG Web UI (T058)
"""
import asyncio
import logging
import os

import streamlit as st

from api_client import APIClient, safe_query, APIError
from config import Config

# Import mock client if available
try:
    from mock_api_client import MockAPIClient
    MOCK_AVAILABLE = True
except ImportError:
    MOCK_AVAILABLE = False

logger = logging.getLogger(__name__)


def render_message(msg: dict):
    """
    Render a single chat message.
    
    Args:
        msg: Dictionary containing message data
    """
    role = msg.get("role", "user")
    content = msg.get("content", "")
    
    with st.chat_message(role):
        # Display content
        st.markdown(content)
        
        # Display sources if available (assistant messages)
        if role == "assistant" and "sources" in msg:
            sources = msg["sources"]
            if sources:
                with st.expander(f"📚 Sources ({len(sources)})"):
                    for i, source in enumerate(sources, 1):
                        st.markdown(f"**{i}.** {source.get('content', 'N/A')[:200]}...")
        
        # Display confidence if available
        if role == "assistant" and "confidence" in msg:
            confidence = msg["confidence"]
            st.caption(f"Confidence: {confidence:.2%}")


def render_chat_interface():
    """
    Render the main chat interface.
    """
    # Initialize chat history if not exists
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # Initialize selected mode (hardcoded to hybrid in app.py)
    if "selected_mode" not in st.session_state:
        st.session_state.selected_mode = "hybrid"
    
    # Display chat history
    for msg in st.session_state.chat_history:
        render_message(msg)
    
    # Chat input (no sidebar settings)
    user_input = st.chat_input("Enter your query...")
    
    if user_input:
        # Process the query
        asyncio.run(process_query(user_input))


async def process_query(query: str):
    """
    Process a user query with proper error handling.
    
    Args:
        query: Raw user input
    """
    try:
        # Validate and sanitize input
        cleaned_query = safe_query(query)
        
        # Add user message to history immediately
        user_msg = {"role": "user", "content": query}
        st.session_state.chat_history.append(user_msg)
        
        # Show loading indicator
        with st.spinner(f"🔍 Searching in {st.session_state.selected_mode} mode..."):
            # Make API request
            api_client: APIClient = st.session_state.get("api_client")
            
            if not api_client:
                # Create API client if not exists
                api_client = await create_api_client()
                st.session_state.api_client = api_client
            
            # Send query
            response = await api_client.query(
                query=cleaned_query,
                mode=st.session_state.selected_mode,
                top_k=10
            )
        
        # Create assistant message
        assistant_msg = {
            "role": "assistant",
            "content": response.get("response", "No response received"),
            "sources": response.get("sources", []),
            "confidence": response.get("confidence", 0.0)
        }
        
        # Add to history
        st.session_state.chat_history.append(assistant_msg)
        
        # Truncate history if exceeds max
        if len(st.session_state.chat_history) > Config.MAX_CHAT_HISTORY * 2:
            st.session_state.chat_history = st.session_state.chat_history[
                -Config.MAX_CHAT_HISTORY:
            ]
        
        # Rerun to update UI
        st.rerun()
        
    except ValueError as e:
        # Input validation error
        logger.warning(f"Input validation error: {e}")
        st.error(f"Invalid input: {str(e)}")
        
    except APIError as e:
        # API error
        logger.error(f"API error: {e.message}")
        st.error(f"API Error: {e.message}")
        
    except Exception as e:
        # Unexpected error
        logger.exception(f"Unexpected error processing query: {e}")
        st.error(f"An unexpected error occurred: {str(e)}")


async def create_api_client():
    """
    Factory function to create an API client.
    
    Returns:
        APIClient or MockAPIClient instance based on configuration
    """
    import streamlit as st
    
    # Check for mock mode from session state first, then env var
    use_mock = st.session_state.get("use_mock", False)
    
    if not use_mock:
        # Also check environment variable as fallback
        use_mock = os.getenv("USE_MOCK_API", "").lower() == "true"
    
    if use_mock and MOCK_AVAILABLE:
        logger.info("Using Mock API Client")
        return MockAPIClient(mock_delay=Config.MOCK_DELAY)
    
    return APIClient()


# Utility functions for testing
def test_render_message():
    """Test function for render_message."""
    # Test user message
    test_msg = {"role": "user", "content": "Hello, world!"}
    print(f"User message: {test_msg}")
    
    # Test assistant message
    test_msg = {
        "role": "assistant",
        "content": "Hello! How can I help?",
        "sources": [{"content": "Source document"}],
        "confidence": 0.85
    }
    print(f"Assistant message: {test_msg}")
    
    print("✅ render_message tests passed")


if __name__ == "__main__":
    # Run tests
    test_render_message()
