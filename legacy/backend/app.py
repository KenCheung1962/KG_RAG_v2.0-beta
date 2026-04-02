"""
RAG Web UI - Main Application (T058) - Compact Layout with Large Fonts
With User-Friendly Mode Toggle (DEMO/REAL) and Reconnect Button
Updated for Ollama/nomic-embed-text direct integration
"""
import logging
import sys

import streamlit as st

# Add source directory to path
sys.path.insert(0, '/Users/ken/clawd/RG_RAG/KG_RAG_Tasks/t058_web_ui/source')

from config import Config
from upload_module import render_document_upload
from api_client import APIClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default API URL for REAL mode (KG RAG API service)
DEFAULT_API_URL = "http://127.0.0.1:8001"

# Default Ollama URL for direct embedding calls
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"


def check_api_connection(api_url: str) -> tuple[bool, str]:
    """Check if API is reachable and return status."""
    try:
        import httpx
        resp = httpx.get(f'{api_url}/health', timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            status = data.get('status', 'unknown')
            return True, status
        return False, f"HTTP {resp.status_code}"
    except httpx.ConnectError:
        return False, "Connection refused"
    except httpx.TimeoutException:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)


def configure_page():
    """Set basic Streamlit page config."""
    st.set_page_config(
        page_title=Config.PAGE_TITLE,
        page_icon=Config.PAGE_ICON,
        layout='wide',
        initial_sidebar_state='collapsed'
    )


def render_mode_selector():
    """Render the mode selection section with toggle and reconnect button."""
    
    st.markdown('---')
    st.markdown('<p style="font-size:18px;font-weight:bold;">🔌 Connection Mode</p>', unsafe_allow_html=True)
    
    # Initialize mode if not set
    if 'use_real_mode' not in st.session_state:
        st.session_state.use_real_mode = False
    if 'api_url' not in st.session_state:
        st.session_state.api_url = DEFAULT_API_URL
    if 'api_status' not in st.session_state:
        st.session_state.api_status = 'unknown'
    if 'api_status_message' not in st.session_state:
        st.session_state.api_status_message = 'Not tested'
    
    # API URL input (only in REAL mode)
    if st.session_state.use_real_mode:
        new_url = st.text_input(
            'API URL',
            value=st.session_state.api_url,
            help='URL of the T036 backend API',
            key='api_url_input'
        )
        if new_url != st.session_state.api_url:
            st.session_state.api_url = new_url
            # Clear cached client when URL changes
            if 'api_client' in st.session_state:
                del st.session_state.api_client
    
    # Mode toggle buttons
    col_demo, col_real, col_reconnect = st.columns([1, 1, 1])
    
    with col_demo:
        demo_clicked = st.button(
            '🔵 DEMO MODE',
            use_container_width=True,
            type='primary' if not st.session_state.use_real_mode else 'secondary',
            help='Use mock data - no backend required'
        )
        if demo_clicked:
            st.session_state.use_real_mode = False
            if 'api_client' in st.session_state:
                del st.session_state.api_client
            st.session_state.api_status = 'demo'
            st.session_state.api_status_message = 'Demo mode active'
            st.rerun()
    
    with col_real:
        real_clicked = st.button(
            '🟢 REAL MODE',
            use_container_width=True,
            type='primary' if st.session_state.use_real_mode else 'secondary',
            help='Connect to T036 backend at ' + st.session_state.api_url
        )
        if real_clicked:
            st.session_state.use_real_mode = True
            if 'api_client' in st.session_state:
                del st.session_state.api_client
            # Test connection
            connected, status_msg = check_api_connection(st.session_state.api_url)
            if connected:
                st.session_state.api_status = 'connected'
                st.session_state.api_status_message = f'Connected - {status_msg}'
            else:
                st.session_state.api_status = 'error'
                st.session_state.api_status_message = f'Error - {status_msg}'
            st.rerun()
    
    with col_reconnect:
        reconnect_clicked = st.button(
            '🔄 Reconnect / Test',
            use_container_width=True,
            help='Test API connection'
        )
        if reconnect_clicked:
            if st.session_state.use_real_mode:
                connected, status_msg = check_api_connection(st.session_state.api_url)
                if connected:
                    st.session_state.api_status = 'connected'
                    st.session_state.api_status_message = f'Connected - {status_msg}'
                else:
                    st.session_state.api_status = 'error'
                    st.session_state.api_status_message = f'Error - {status_msg}'
            else:
                st.session_state.api_status = 'demo'
                st.session_state.api_status_message = 'Demo mode active'
            st.rerun()
    
    # Status indicator
    status_col1, status_col2 = st.columns([1, 3])
    
    with status_col1:
        if st.session_state.use_real_mode:
            if st.session_state.api_status == 'connected':
                st.success('🟢 REAL MODE ACTIVE')
            elif st.session_state.api_status == 'error':
                st.error('🔴 CONNECTION ERROR')
            else:
                st.warning('🟡 UNKNOWN STATUS')
        else:
            st.info('🔵 DEMO MODE ACTIVE')
    
    with status_col2:
        if st.session_state.use_real_mode:
            st.caption(f'API: {st.session_state.api_url}')
            st.caption(f'Status: {st.session_state.api_status_message}')
        else:
            st.caption('Using mock data - no backend required')
    
    st.markdown('---')


def render_left_column():
    """Render LEFT column - Compact with larger fonts."""
    
    # Mode selector
    render_mode_selector()
    
    # Search Mode selection
    if 'selected_mode' not in st.session_state:
        st.session_state.selected_mode = 'hybrid'
    
    st.markdown('<p style="font-size:16px;font-weight:bold;">🔍 Search Mode</p>', unsafe_allow_html=True)
    
    mode = st.selectbox(
        'Mode',
        options=['local', 'global', 'hybrid'],
        index=['local', 'global', 'hybrid'].index(st.session_state.selected_mode),
        label_visibility='collapsed',
        help='local: current document, global: all documents, hybrid: both'
    )
    if mode != st.session_state.selected_mode:
        st.session_state.selected_mode = mode
    
    # Spacing
    st.markdown('<div style="margin-top:30px;"></div>', unsafe_allow_html=True)
    
    # Document upload section - use the fixed upload module
    render_document_upload()
    
    # Spacing
    st.markdown('<div style="margin-top:30px;"></div>', unsafe_allow_html=True)
    
    # Quick stats (if available)
    if st.session_state.get('use_real_mode') and st.session_state.get('api_status') == 'connected':
        if st.button('📊 Load Stats', use_container_width=True):
            try:
                import httpx
                resp = httpx.get(f'{st.session_state.api_url}/api/v1/stats', timeout=5.0)
                if resp.status_code == 200:
                    stats = resp.json()
                    st.json(stats)
                else:
                    st.error(f'Stats unavailable: HTTP {resp.status_code}')
            except Exception as e:
                st.error(f'Error loading stats: {e}')


def render_right_column():
    """Render RIGHT column - Compact with large fonts."""
    
    # Compact chat label
    st.markdown('<p style="font-size:18px;font-weight:bold;margin:0;padding:0;">💬 Chat</p>', unsafe_allow_html=True)
    
    # Initialize chat history
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    if 'searching' not in st.session_state:
        st.session_state.searching = False
    
    # User input area
    col1, col2 = st.columns([6, 1])
    
    with col1:
        user_input = st.text_area(
            'Your question',
            height=80,
            placeholder='Ask about machine learning, transformers, knowledge graphs...',
            label_visibility='collapsed',
            key='input_field'
        )
    
    with col2:
        st.markdown('<div style="height:80px;display:flex;align-items:end;">', unsafe_allow_html=True)
        search_clicked = st.button('🔍', use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    if user_input.strip() and search_clicked:
        process_query(user_input.strip())
    
    # Minimal gap
    st.markdown('')
    
    # Searching indicator
    if st.session_state.searching:
        st.markdown('<p style="font-size:14px;color:#1E90FF;">🔍 Searching knowledge base...</p>', unsafe_allow_html=True)
    
    st.markdown('')
    
    # Display messages
    if st.session_state.chat_history:
        pairs = []
        for i in range(0, len(st.session_state.chat_history), 2):
            if i+1 < len(st.session_state.chat_history):
                pairs.append((
                    st.session_state.chat_history[i],
                    st.session_state.chat_history[i+1]
                ))
        
        for user_msg, assistant_msg in reversed(pairs):
            # Question with yellow dot
            st.markdown(f'''
            <div style="background-color:#FFD700;border-radius:50%;width:35px;height:35px;display:flex;align-items:center;justify-content:center;float:left;margin-right:10px;">
                <span style="color:black;font-weight:bold;font-size:20px;">Q</span>
            </div>
            <p style="font-size:20px;margin-left:45px;margin-top:5px;">{user_msg["content"]}</p>
            <div style="clear:both;"></div>
            ''', unsafe_allow_html=True)
            
            # Reply with green dot
            st.markdown(f'''
            <div style="background-color:#32CD32;border-radius:50%;width:35px;height:35px;display:flex;align-items:center;justify-content:center;float:left;margin-right:10px;">
                <span style="color:black;font-weight:bold;font-size:20px;">A</span>
            </div>
            <p style="font-size:20px;margin-left:45px;margin-top:5px;">{assistant_msg["content"]}</p>
            <div style="clear:both;"></div>
            ''', unsafe_allow_html=True)
            
            # Sources
            if 'sources' in assistant_msg and assistant_msg['sources']:
                with st.expander(f'Sources ({len(assistant_msg["sources"])})'):
                    for i, src in enumerate(assistant_msg['sources'], 1):
                        content = src.get('content', '')[:300]
                        st.markdown(f'**{i}.** {content}...')
            
            # Confidence
            if 'confidence' in assistant_msg:
                st.caption(f'Confidence: {assistant_msg["confidence"]:.1%}')
            
            st.markdown('')
    else:
        st.caption('💡 Ask a question to search the knowledge base')
        st.caption('📚 Try: "What is a transformer?" or "Explain attention mechanism"')


def process_query(query: str):
    """Process user query (synchronous)."""
    from api_client import safe_query
    
    st.session_state.searching = True
    
    # Validate input
    try:
        cleaned_query = safe_query(query)
    except ValueError as e:
        st.session_state.searching = False
        st.error(f'Invalid input: {e}')
        return
    
    user_msg = {'role': 'user', 'content': query}
    st.session_state.chat_history.append(user_msg)
    
    try:
        use_real = st.session_state.get('use_real_mode', False)
        
        if use_real:
            # Use real API client for REAL MODE
            api_url = st.session_state.get('api_url', DEFAULT_API_URL)
            api_client = APIClient(base_url=api_url)
        else:
            # Use mock API client for DEMO MODE
            from mock_api_client import MockAPIClient
            api_client = MockAPIClient()
        
        # Call chatbot query method (uses MiniMax LLM for conversational responses)
        response = api_client.query_chatbot(
            query=cleaned_query,
            top_k=10
        )
        
        assistant_msg = {
            'role': 'assistant',
            'content': response.get('response', 'No response received'),
            'sources': response.get('sources', []),
            'confidence': response.get('confidence', 0.0)
        }
        st.session_state.chat_history.append(assistant_msg)
        
    except Exception as e:
        error_msg = {
            'role': 'assistant',
            'content': f'Error: {str(e)}',
            'sources': [],
            'confidence': 0.0
        }
        st.session_state.chat_history.append(error_msg)
    
    st.session_state.searching = False
    st.rerun()


def main():
    configure_page()
    
    # Compact header
    st.markdown('<h1 style="font-size:40px;margin:0;padding:0;line-height:1.0;">👋 Knowledge Graph RAG v1.0</h1>', unsafe_allow_html=True)
    st.caption('T058 - Web UI with Mode Toggle')
    
    # Spacing
    st.markdown('<div style="margin-top:20px;"></div>', unsafe_allow_html=True)
    
    # Two column layout
    left_col, right_col = st.columns([1, 3])
    
    with left_col:
        render_left_column()
    
    with right_col:
        render_right_column()


if __name__ == '__main__':
    main()
