"""
RAG Web UI - 4-Tab Layout (T058) - Fixed Version
Tabs: Ingest, Query, Query + File, Config
With Knowledge Graph Stats Panel
Fixed: Auto-refresh stats, separate refresh from processing, folder detection
"""
import logging
import sys
import os
import subprocess

import streamlit as st
import httpx
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
DEFAULT_API_URL = "http://127.0.0.1:8001"
OLLAMA_URL = "http://127.0.0.1:11434"

st.set_page_config(
    page_title="KG RAG System",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session state for stats
if 'stats_last_updated' not in st.session_state:
    st.session_state.stats_last_updated = None
if 'ingest_success' not in st.session_state:
    st.session_state.ingest_success = False


def check_api_connection(api_url: str) -> tuple[bool, dict, dict]:
    """Check API connection and get stats."""
    try:
        resp = httpx.get(f'{api_url}/health', timeout=5.0)
        if resp.status_code == 200:
            stats_resp = httpx.get(f'{api_url}/api/v1/stats', timeout=5.0)
            stats = stats_resp.json() if stats_resp.status_code == 200 else {}
            return True, resp.json(), stats
        return False, {}, {}
    except Exception as e:
        return False, {}, {}


def refresh_stats(api_url: str):
    """Force refresh stats."""
    connected, health, stats = check_api_connection(api_url)
    st.session_state.stats_last_updated = datetime.now()
    return connected, health, stats


def render_kg_stats_panel(api_url: str):
    """Render Knowledge Graph Stats panel with auto-refresh and manual refresh."""
    connected, health, stats = check_api_connection(api_url)
    
    st.markdown("### 📊 Knowledge Graph Stats")
    
    # Auto-refresh check after ingest
    if st.session_state.ingest_success:
        connected, health, stats = refresh_stats(api_url)
        st.session_state.ingest_success = False
    
    # Manual refresh button (doesn't trigger rerun, just refreshes data)
    refresh_col1, refresh_col2 = st.columns([1, 5])
    with refresh_col1:
        if st.button("🔄", key="refresh_stats_btn", help="Refresh stats"):
            connected, health, stats = refresh_stats(api_url)
    with refresh_col2:
        if connected:
            st.caption(f"Last updated: {st.session_state.stats_last_updated.strftime('%H:%M:%S') if st.session_state.stats_last_updated else 'Never'}")
    
    if connected:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Entities", stats.get('entities', 0))
        with col2:
            st.metric("Relationships", stats.get('relationships', 0))
        with col3:
            st.metric("Status", health.get('status', 'unknown').upper())
        
        st.caption(f"Validated: {stats.get('validated_at', 'N/A')}")
    else:
        st.warning("⚠️ Not connected to API")


def select_folder():
    """Use macOS folder selection dialog."""
    try:
        # Use AppleScript for folder selection on macOS
        script = '''
        tell application "System Events"
            activate
            set folderPath to choose folder with prompt "Select a folder to index"
            return POSIX path of folderPath
        end tell
        '''
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            folder = result.stdout.strip()
            if folder:
                return folder
    except Exception as e:
        logger.error(f"Folder selection error: {e}")
    return None


def render_ingest_tab(api_url: str):
    """Tab 1: Document Ingest."""
    st.markdown("### 📁 Document Ingest")
    
    # Mode selection
    ingest_mode = st.radio(
        "Ingest Mode",
        ["Single File", "Folder", "File List"],
        horizontal=True
    )
    
    if ingest_mode == "Single File":
        uploaded_file = st.file_uploader(
            "Upload document",
            type=['pdf', 'docx', 'txt', 'md', 'html', 'json'],
            key="single_file_uploader"
        )
        
        if uploaded_file:
            st.success(f"✅ File ready: {uploaded_file.name}")
            
            if st.button("🚀 Upload & Index", key="upload_single", type="primary"):
                with st.spinner("Processing..."):
                    try:
                        content = uploaded_file.getvalue()
                        import base64
                        content_b64 = base64.b64encode(content).decode('utf-8')
                        
                        resp = httpx.post(
                            f"{api_url}/api/v1/documents/upload",
                            json={
                                "filename": uploaded_file.name,
                                "content": content_b64,
                                "content_type": uploaded_file.type,
                                "extract_kg": True
                            },
                            timeout=120.0
                        )
                        
                        if resp.status_code == 200:
                            result = resp.json()
                            st.success(f"✅ Indexed {result.get('chunks_indexed', 0)} chunks")
                            # Set flag to refresh stats
                            st.session_state.ingest_success = True
                        else:
                            st.error(f"Error: {resp.status_code} - {resp.text}")
                    except Exception as e:
                        st.error(f"Error: {e}")
    
    elif ingest_mode == "Folder":
        st.markdown("**Select a folder to index:**")
        
        # Folder selection using button + text input
        folder_col1, folder_col2 = st.columns([1, 3])
        with folder_col1:
            if st.button("📂 Browse...", key="browse_folder"):
                folder_path = select_folder()
                if folder_path:
                    st.session_state.selected_folder = folder_path
                    st.rerun()
        with folder_col2:
            # Text input as fallback or manual entry
            folder_path = st.text_input(
                "Or enter folder path:",
                value=st.session_state.get('selected_folder', ''),
                placeholder="/path/to/documents",
                key="folder_path_input"
            )
        
        # Show selected folder info
        if folder_path and os.path.isdir(folder_path):
            st.success(f"📂 Selected: {folder_path}")
            
            # Count files
            try:
                file_count = sum(1 for _ in os.scandir(folder_path) if _.is_file())
                st.info(f"📄 {file_count} files in folder")
            except:
                pass
            
            recursive = st.checkbox("Scan subfolders recursively", value=False)
            
            if st.button("🚀 Index Folder", key="index_folder", type="primary"):
                with st.spinner("Processing... This may take a while."):
                    try:
                        resp = httpx.post(
                            f"{api_url}/api/v1/documents/upload/folder",
                            json={
                                "folder_path": folder_path,
                                "recursive": recursive,
                                "use_llm": True,
                                "sequential": True
                            },
                            timeout=600.0
                        )
                        
                        if resp.status_code == 200:
                            result = resp.json()
                            st.success(f"✅ Processed {result.get('new_files', 0)} new files (skipped {result.get('skipped_files', 0)})")
                            st.session_state.ingest_success = True
                        else:
                            st.error(f"Error: {resp.status_code}")
                    except Exception as e:
                        st.error(f"Error: {e}")
        elif folder_path:
            st.error(f"❌ Folder not found: {folder_path}")
    
    elif ingest_mode == "File List":
        file_paths = st.text_area(
            "File Paths (one per line)",
            value=st.session_state.get('file_list_input', ''),
            placeholder="/path/to/file1.txt\n/path/to/file2.txt",
            key="file_list_input"
        )
        
        if st.button("🚀 Index Files", key="index_files", type="primary"):
            if not file_paths.strip():
                st.error("Please enter file paths")
            else:
                with st.spinner("Processing..."):
                    try:
                        paths = [p.strip() for p in file_paths.split('\n') if p.strip()]
                        resp = httpx.post(
                            f"{api_url}/api/v1/documents/upload/list",
                            json={
                                "file_paths": paths,
                                "use_llm": True,
                                "sequential": True
                            },
                            timeout=600.0
                        )
                        
                        if resp.status_code == 200:
                            result = resp.json()
                            st.success(f"✅ Processed {result.get('new_files', 0)} new files")
                            st.session_state.ingest_success = True
                        else:
                            st.error(f"Error: {resp.status_code}")
                    except Exception as e:
                        st.error(f"Error: {e}")


def render_query_tab(api_url: str):
    """Tab 2: Simple Query."""
    st.markdown("### 🔍 Query Knowledge Base")
    
    # Query settings
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("Ask a question:", placeholder="What is...?")
    with col2:
        mode = st.selectbox("Mode", ["local", "global", "hybrid"], index=2)
    
    if st.button("🔍 Search", key="query_search", type="primary") and query:
        with st.spinner("Searching..."):
            try:
                resp = httpx.post(
                    f"{api_url}/api/v1/chat",
                    json={
                        "message": query,
                        "mode": mode,
                        "use_llm": True
                    },
                    timeout=120.0
                )
                
                if resp.status_code == 200:
                    result = resp.json()
                    
                    st.markdown("#### 💬 Answer")
                    st.write(result.get('response', 'No response'))
                    
                    sources = result.get('sources', [])
                    if sources:
                        st.markdown("#### 📚 Sources")
                        for src in sources[:5]:
                            st.caption(f"• {src.get('entity', 'Unknown')} ({src.get('type', 'document')})")
                else:
                    st.error(f"Error: {resp.status_code}")
            except Exception as e:
                st.error(f"Error: {e}")


def render_query_with_file_tab(api_url: str):
    """Tab 3: Query + Attached File."""
    st.markdown("### 🔍 Query with Attached Document")
    
    uploaded_file = st.file_uploader(
        "Attach document (optional)",
        type=['pdf', 'docx', 'txt', 'md', 'html', 'json'],
        key="attached_file_uploader"
    )
    
    query = st.text_input("Ask a question:", placeholder="Based on the attached document...")
    
    if st.button("🔍 Search with Doc", key="query_with_doc", type="primary") and query:
        with st.spinner("Processing..."):
            try:
                attached_text = None
                filename = None
                
                if uploaded_file:
                    attached_text = uploaded_file.getvalue().decode('utf-8', errors='ignore')
                    filename = uploaded_file.name
                
                resp = httpx.post(
                    f"{api_url}/api/v1/chat/with-doc",
                    json={
                        "message": query,
                        "mode": "hybrid",
                        "use_llm": True,
                        "attached_text": attached_text,
                        "attached_filename": filename
                    },
                    timeout=120.0
                )
                
                if resp.status_code == 200:
                    result = resp.json()
                    
                    st.markdown("#### 💬 Answer")
                    st.write(result.get('response', 'No response'))
                    
                    sources = result.get('sources', [])
                    if sources:
                        st.markdown("#### 📚 Sources")
                        db_sources = [s for s in sources if s.get('type') == 'database']
                        doc_sources = [s for s in sources if s.get('type') == 'attached_document']
                        
                        if db_sources:
                            st.markdown("**From Knowledge Base:**")
                            for src in db_sources[:3]:
                                st.caption(f"• {src.get('entity', 'Unknown')}")
                        
                        if doc_sources:
                            st.markdown("**From Attached Document:**")
                            for src in doc_sources[:3]:
                                st.caption(f"• {src.get('entity', 'Unknown')}")
                else:
                    st.error(f"Error: {resp.status_code}")
            except Exception as e:
                st.error(f"Error: {e}")


def render_config_tab(api_url: str):
    """Tab 4: Configuration."""
    st.markdown("### ⚙️ Configuration")
    
    # API Settings
    st.markdown("#### API Connection")
    
    new_api_url = st.text_input("API URL", value=api_url, key="api_url_input")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Test Connection", key="test_conn"):
            connected, health, stats = check_api_connection(new_api_url)
            if connected:
                st.success(f"✅ Connected - {health.get('status', 'OK')}")
            else:
                st.error("❌ Connection failed")
    
    with col2:
        if st.button("🔌 Connect", key="connect_btn"):
            st.session_state.api_url = new_api_url
            st.rerun()
    
    # Embedding Settings
    st.markdown("#### Embedding Configuration")
    st.info(f"**Model:** nomic-embed-text (768d)")
    st.info(f"**Source:** Ollama")
    
    # Check Ollama
    try:
        resp = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=5.0)
        if resp.status_code == 200:
            models = resp.json().get('models', [])
            nomic = [m for m in models if 'nomic' in m.get('name', '').lower()]
            if nomic:
                st.success(f"✅ nomic-embed-text available")
            else:
                st.warning("⚠️ nomic-embed-text not found in Ollama")
        else:
            st.error(f"Ollama error: {resp.status_code}")
    except Exception as e:
        st.error(f"❌ Ollama not reachable: {e}")
    
    # Registry Stats
    st.markdown("#### File Registry")
    try:
        resp = httpx.get(f"{api_url}/api/v1/documents/registry", timeout=5.0)
        if resp.status_code == 200:
            reg_stats = resp.json()
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Files", reg_stats.get('total_files', 0))
            with col2:
                size_bytes = reg_stats.get('total_size_bytes', 0)
                size_mb = size_bytes / (1024 * 1024)
                st.metric("Total Size", f"{size_mb:.2f} MB")
    except Exception as e:
        st.caption(f"Registry: {e}")


def main():
    """Main app."""
    if 'api_url' not in st.session_state:
        st.session_state.api_url = DEFAULT_API_URL
    
    # Header
    st.title("🔍 KG RAG System")
    st.markdown("**Knowledge Graph RAG with Ollama Embeddings (768d)**")
    st.markdown("---")
    
    # Render KG Stats at top
    render_kg_stats_panel(st.session_state.api_url)
    st.markdown("---")
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📥 Ingest", "🔍 Query", "🔍 Query + File", "⚙️ Config"])
    
    with tab1:
        render_ingest_tab(st.session_state.api_url)
    
    with tab2:
        render_query_tab(st.session_state.api_url)
    
    with tab3:
        render_query_with_file_tab(st.session_state.api_url)
    
    with tab4:
        render_config_tab(st.session_state.api_url)


if __name__ == "__main__":
    main()
