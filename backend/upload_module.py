"""
Document Upload Module for RAG Web UI (T058) - Fixed for multiple files
"""
import asyncio
import logging
import os

import streamlit as st

from api_client import APIClient, safe_filename, APIError
from config import Config

# Import mock client if available
try:
    from mock_api_client import MockAPIClient
    MOCK_AVAILABLE = True
except ImportError:
    MOCK_AVAILABLE = False

logger = logging.getLogger(__name__)


def validate_file_type(file) -> tuple[bool, str]:
    """Validate file type and size."""
    file_size = file.size
    max_size_bytes = 200 * 1024 * 1024  # 200MB
    
    if file_size > max_size_bytes:
        return False, f"File {file.name} exceeds 200MB limit"
    
    ext = file.name.split(".")[-1].lower()
    allowed_ext = ("pdf", "docx", "txt", "html")
    if ext not in allowed_ext:
        return False, f"Invalid file type: .{ext}. Allowed: {', '.join(allowed_ext)}"
    
    for blocked_ext in Config.BLOCKED_EXTENSIONS:
        if file.name.lower().endswith(blocked_ext):
            return False, f"File type .{blocked_ext} is not allowed"
    
    return True, ""


def render_document_upload():
    """Render compact document upload interface."""
    # Tips expander
    with st.expander("📝 Upload Tips"):
        st.markdown('''
        - PDF, DOCX, TXT, HTML files
        - Max 200MB per file
        - Select multiple files at once (Ctrl/Cmd + Click)
        ''')
    
    st.markdown("**📄 Select Files (select multiple at once)**")
    
    # Use session state to store selected files
    if 'pending_files' not in st.session_state:
        st.session_state.pending_files = []
    
    # File uploader - multiple files at once
    uploaded_files = st.file_uploader(
        "Drag and drop files here",
        type=["pdf", "docx", "txt", "html"],
        accept_multiple_files=True,
        help="Hold Ctrl/Cmd to select multiple files",
        key="file_uploader",
        label_visibility="collapsed"
    )
    
    # If new files selected, add to session state
    if uploaded_files:
        for f in uploaded_files:
            # Check if already in list
            names = [x.name for x in st.session_state.pending_files]
            if f.name not in names:
                st.session_state.pending_files.append(f)
    
    # Show current pending files
    pending = st.session_state.pending_files
    
    if pending:
        st.markdown("### 📁 Files to Upload:")
        for i, f in enumerate(pending):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.text(f"  ✓ {f.name} ({f.size/1024:.1f} KB)")
            with col2:
                if st.button(f"✕", key=f"remove_{i}", help="Remove"):
                    st.session_state.pending_files.pop(i)
                    st.rerun()
        
        # Upload button
        st.markdown("---")
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🗑️ Clear All", type="secondary", use_container_width=True):
                st.session_state.pending_files = []
                st.rerun()
        with col2:
            if st.button("⬆️ Upload All", type="primary", use_container_width=True):
                # Validate all files
                valid_files = []
                errors = []
                
                for f in pending:
                    is_valid, error_msg = validate_file_type(f)
                    if is_valid:
                        valid_files.append(f)
                    else:
                        errors.append(f"{f.name}: {error_msg}")
                
                if errors:
                    for err in errors:
                        st.error(err)
                
                if valid_files:
                    # Show progress and upload
                    st.info(f"⬆️ Uploading {len(valid_files)} file(s)...")
                    
                    # Run async upload
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        success, failed = loop.run_until_complete(upload_files_async(valid_files))
                        
                        if success:
                            st.success(f"✅ Successfully uploaded {success} file(s)!")
                            st.session_state.pending_files = []
                        
                        if failed:
                            st.warning(f"⚠️ {failed} file(s) failed")
                    finally:
                        loop.close()
                    
                    st.rerun()
    
    elif not uploaded_files:
        st.info("👆 Select files above to begin")


async def upload_files_async(files: list) -> tuple[int, int]:
    """Upload and index files asynchronously."""
    import httpx
    
    api_url = Config.API_BASE_URL
    endpoint = f"{api_url}/api/v1/documents/upload"
    
    success_count = 0
    error_count = 0
    
    progress_bar = st.progress(0)
    
    for i, file in enumerate(files):
        try:
            progress_bar.progress((i + 1) / len(files))
            st.text(f"Uploading: {file.name}")
            
            # Read file
            file_content = file.read()
            
            # Encode to base64
            import base64
            content_b64 = base64.b64encode(file_content).decode('utf-8')
            
            # Prepare payload
            ext = file.name.split(".")[-1].lower()
            payload = {
                "filename": file.name,
                "content": content_b64,
                "content_type": ext
            }
            
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(endpoint, json=payload)
                resp.raise_for_status()
                success_count += 1
                
        except Exception as e:
            error_count += 1
            st.error(f"Failed: {file.name} - {str(e)}")
    
    progress_bar.empty()
    return success_count, error_count


async def create_api_client():
    """Create API client."""
    import streamlit as st
    
    use_mock = os.getenv("USE_MOCK_API", "").lower() == "true"
    
    if use_mock and MOCK_AVAILABLE:
        logger.info("Using Mock API Client")
        return MockAPIClient()
    
    return APIClient()


if __name__ == "__main__":
    print("Upload module loaded")
