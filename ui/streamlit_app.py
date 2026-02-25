import streamlit as st
import requests
import json
from datetime import datetime
from typing import Optional
import time

# Page configuration
st.set_page_config(
    page_title="Enterprise RAG Chat",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for production look
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .stat-box {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .source-box {
        background-color: #e8f4f8;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 3px solid #17a2b8;
    }
    .error-box {
        background-color: #f8d7da;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 3px solid #dc3545;
        color: #721c24;
    }
    .success-box {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 3px solid #28a745;
        color: #155724;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar - Configuration
st.sidebar.title("⚙️ Configuration")
api_url = st.sidebar.text_input(
    "API Endpoint",
    value="http://localhost:8000",
    help="FastAPI server URL"
)
api_key = st.sidebar.text_input(
    "API Key",
    type="password",
    help="SERVICE_API_KEY from environment"
)

# Settings
st.sidebar.markdown("### Settings")
show_confidence = st.sidebar.checkbox("Show Confidence Score", value=True)
show_sources = st.sidebar.checkbox("Show Sources", value=True)
show_timings = st.sidebar.checkbox("Show Response Time", value=True)
max_sources = st.sidebar.slider("Max Sources to Display", 1, 5, 3)

# Health check
st.sidebar.markdown("### Health Status")
if st.sidebar.button("🔄 Check API Status"):
    try:
        resp = requests.get(f"{api_url}/health", timeout=5)
        if resp.status_code == 200:
            health = resp.json()
            st.sidebar.success(f"✅ API is healthy")
            st.sidebar.info(f"RAG Initialized: {health.get('rag_initialized', False)}")
        else:
            st.sidebar.error(f"❌ API returned {resp.status_code}")
    except Exception as e:
        st.sidebar.error(f"❌ Cannot reach API: {str(e)}")

# Session state for conversation history
if "messages" not in st.session_state:
    st.session_state.messages = []

if "history" not in st.session_state:
    st.session_state.history = []

# Main header
st.markdown('<div class="main-header">🤖 Enterprise RAG Chat</div>', unsafe_allow_html=True)
st.markdown("Production-grade AI-powered document Q&A system")

# Tabs for different views
tab1, tab2, tab3 = st.tabs(["💬 Chat", "📚 Conversation History", "📊 Metrics"])

# ============= TAB 1: CHAT =============
with tab1:
    st.markdown("### Ask Questions About Your Documents")
    
    # Display conversation history in chat format
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and "metadata" in msg:
                meta = msg["metadata"]
                if show_confidence and "confidence" in meta:
                    st.caption(f"🎯 Confidence: {meta['confidence']:.1%}")
                if show_timings and "latency_ms" in meta:
                    st.caption(f"⏱️ Response time: {meta['latency_ms']}ms")
    
    # Query input
    col1, col2 = st.columns([5, 1])
    with col1:
        user_query = st.text_input(
            "Enter your question (max 500 characters):",
            placeholder="e.g., What is the data governance policy?",
            key="query_input"
        )
    with col2:
        send_button = st.button("Send", use_container_width=True)
    
    # Process query
    if send_button and user_query.strip():
        # Validate input
        if len(user_query) > 500:
            st.error("❌ Query too long (max 500 characters)")
        elif not api_key:
            st.error("❌ Please enter API key in sidebar")
        elif not api_url:
            st.error("❌ Please enter API endpoint in sidebar")
        else:
            # Add user message to history
            st.session_state.messages.append({
                "role": "user",
                "content": user_query
            })
            
            # Show loading state
            with st.spinner("🔄 Processing your question..."):
                start_time = time.time()
                try:
                    # Call API
                    headers = {"x-api-key": api_key}
                    response = requests.post(
                        f"{api_url}/ask",
                        json={"query": user_query},
                        headers=headers,
                        timeout=30
                    )
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    
                    if response.status_code == 200:
                        data = response.json()
                        answer = data.get("answer", "No answer generated")
                        confidence = data.get("confidence", 0)
                        sources = data.get("sources", [])
                        latency = data.get("latency_ms", elapsed_ms)
                        
                        # Build assistant message
                        assistant_msg = {
                            "role": "assistant",
                            "content": answer,
                            "metadata": {
                                "confidence": confidence,
                                "sources": sources,
                                "latency_ms": latency
                            }
                        }
                        st.session_state.messages.append(assistant_msg)
                        st.session_state.history.append({
                            "query": user_query,
                            "answer": answer,
                            "confidence": confidence,
                            "sources": sources,
                            "timestamp": datetime.now().isoformat(),
                            "latency_ms": latency
                        })
                        
                        # Re-render chat
                        st.rerun()
                    
                    elif response.status_code == 400:
                        error_data = response.json()
                        st.error(f"❌ {error_data.get('details', 'Invalid request')}")
                    
                    elif response.status_code == 503:
                        st.error("❌ API is temporarily unavailable (rate limited). Try again in a moment.")
                    
                    elif response.status_code == 504:
                        st.error("❌ Request timeout. The API took too long to respond.")
                    
                    else:
                        st.error(f"❌ API Error: {response.status_code}")
                
                except requests.exceptions.Timeout:
                    st.error("❌ Request timeout. Check if API is running.")
                except requests.exceptions.ConnectionError:
                    st.error(f"❌ Cannot connect to API at {api_url}. Is it running?")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    # Clear history button
    if st.session_state.messages:
        if st.button("🗑️ Clear Conversation"):
            st.session_state.messages = []
            st.rerun()

# ============= TAB 2: HISTORY =============
with tab2:
    st.markdown("### Conversation History")
    
    if st.session_state.history:
        # Display as table
        for i, item in enumerate(st.session_state.history, 1):
            with st.expander(f"**Query {i}:** {item['query'][:60]}..."):
                st.markdown("**Question:**")
                st.write(item['query'])
                
                st.markdown("**Answer:**")
                st.write(item['answer'])
                
                # Metadata
                col1, col2, col3 = st.columns(3)
                with col1:
                    if show_confidence:
                        st.metric("Confidence", f"{item['confidence']:.1%}")
                with col2:
                    if show_timings:
                        st.metric("Response Time", f"{item['latency_ms']}ms")
                with col3:
                    st.metric("Sources", len(item['sources']))
                
                # Sources
                if show_sources and item['sources']:
                    st.markdown("**Sources:**")
                    for src in item['sources'][:max_sources]:
                        st.markdown(f"- {src}")
                
                st.caption(f"📅 {item['timestamp']}")
        
        # Export history
        if st.button("💾 Export History as JSON"):
            json_str = json.dumps(st.session_state.history, indent=2)
            st.download_button(
                label="Download JSON",
                data=json_str,
                file_name=f"rag_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    else:
        st.info("No conversation history yet. Start by asking a question!")

# ============= TAB 3: METRICS =============
with tab3:
    st.markdown("### Session Metrics")
    
    if st.session_state.history:
        # Calculate metrics
        total_queries = len(st.session_state.history)
        avg_confidence = sum(item['confidence'] for item in st.session_state.history) / total_queries
        avg_latency = sum(item['latency_ms'] for item in st.session_state.history) / total_queries
        total_sources = sum(len(item['sources']) for item in st.session_state.history)
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Queries", total_queries)
        with col2:
            st.metric("Avg Confidence", f"{avg_confidence:.1%}")
        with col3:
            st.metric("Avg Response Time", f"{avg_latency:.0f}ms")
        with col4:
            st.metric("Total Sources Used", total_sources)
        
        # Confidence distribution
        st.markdown("### Confidence Distribution")
        confidences = [item['confidence'] for item in st.session_state.history]
        st.bar_chart({"Confidence Score": confidences})
        
        # Response time trend
        st.markdown("### Response Time Trend")
        latencies = [item['latency_ms'] for item in st.session_state.history]
        st.line_chart({"Latency (ms)": latencies})
        
        # Source popularity
        st.markdown("### Source Utilization")
        from collections import Counter
        all_sources = []
        for item in st.session_state.history:
            all_sources.extend(item['sources'])
        source_counts = Counter(all_sources)
        
        if source_counts:
            st.bar_chart({"Uses": dict(source_counts)})
    
    else:
        st.info("No metrics to display yet. Ask some questions first!")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.85rem;'>
    🚀 Enterprise RAG System | Powered by FastAPI + Streamlit | v1.0
    </div>
    """,
    unsafe_allow_html=True
)
