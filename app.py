"""
VIRA - VIT Intelligent Regulation Assistant
Main Streamlit Application

Run with:
    streamlit run app.py
"""

import streamlit as st
import time
import sys
import io

# Force UTF-8 stdout so emoji in Gemini responses don't crash the Windows terminal
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# --- Page Configuration (must be FIRST streamlit call) ---
st.set_page_config(
    page_title="VIRA - VIT Regulation Assistant",
    page_icon="assets/vira_icon.png" if __import__('pathlib').Path("assets/vira_icon.png").exists() else "🎓",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://vit.ac.in",
        "About": "VIRA - VIT Intelligent Regulation Assistant v1.0",
    }
)

# --- Custom CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        max-width: 1100px;
    }

    /* Hero header */
    .vira-header {
        background: linear-gradient(135deg, #6C3EE8 0%, #A855F7 50%, #3B82F6 100%);
        border-radius: 20px;
        padding: 2.5rem 2rem;
        margin-bottom: 1.5rem;
        text-align: center;
        box-shadow: 0 20px 60px rgba(108, 62, 232, 0.3);
        position: relative;
        overflow: hidden;
    }

    .vira-header::before {
        content: "";
        position: absolute;
        top: -50%; left: -50%;
        width: 200%; height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.05) 0%, transparent 60%);
        animation: shimmer 4s infinite linear;
    }

    @keyframes shimmer {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    .vira-title {
        font-size: 2.8rem;
        font-weight: 700;
        color: white;
        margin: 0;
        letter-spacing: -0.5px;
        text-shadow: 0 2px 20px rgba(0,0,0,0.3);
    }

    .vira-subtitle {
        font-size: 1rem;
        color: rgba(255,255,255,0.85);
        margin-top: 0.5rem;
        font-weight: 400;
    }

    .vira-badge {
        display: inline-block;
        background: rgba(255,255,255,0.2);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.3);
        border-radius: 50px;
        padding: 0.3rem 1rem;
        font-size: 0.8rem;
        color: white;
        margin-top: 1rem;
        font-weight: 500;
    }

    /* Source citation box */
    .source-box {
        background: rgba(108, 62, 232, 0.1);
        border: 1px solid rgba(108, 62, 232, 0.3);
        border-radius: 10px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
        font-size: 0.82rem;
        color: rgba(232, 232, 240, 0.8);
    }

    .source-title {
        font-weight: 600;
        color: #A855F7;
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 0.4rem;
    }

    /* Chat message styling */
    .stChatMessage {
        animation: fadeUp 0.3s ease-out;
    }

    @keyframes fadeUp {
        from { opacity: 0; transform: translateY(8px); }
        to   { opacity: 1; transform: translateY(0); }
    }

    /* Stat card in sidebar */
    .stat-card {
        background: rgba(108, 62, 232, 0.12);
        border: 1px solid rgba(108, 62, 232, 0.25);
        border-radius: 12px;
        padding: 0.75rem;
        margin-bottom: 0.5rem;
        text-align: center;
    }

    .stat-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #A855F7;
    }

    .stat-label {
        font-size: 0.72rem;
        color: rgba(255,255,255,0.45);
        margin-top: 0.1rem;
    }

    /* Tip box */
    .tip-box {
        background: rgba(59, 130, 246, 0.08);
        border: 1px solid rgba(59, 130, 246, 0.2);
        border-radius: 10px;
        padding: 0.6rem 0.9rem;
        font-size: 0.82rem;
        color: rgba(232, 232, 240, 0.7);
        margin-top: 0.5rem;
    }

    hr { border-color: rgba(255,255,255,0.07) !important; }
</style>
""", unsafe_allow_html=True)


# --- Load VIRA Engine (cached - only runs once) ---
@st.cache_resource(show_spinner=False)
def load_vira_engine():
    """
    Load the RAG engine once and cache it for the entire session.
    @st.cache_resource means this won't re-run on each Streamlit rerun.
    """
    try:
        from src.rag_pipeline import VIRAEngine
        return VIRAEngine(), None
    except FileNotFoundError as e:
        return None, str(e)
    except ValueError as e:
        return None, str(e)
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"


# --- Sample Questions ---
SAMPLE_QUESTIONS = [
    "What is the minimum attendance required at VIT?",
    "How is CGPA calculated at VIT?",
    "What happens if I fail a subject?",
    "Can I re-register for a failed course?",
    "What are the scholarship criteria?",
    "How many exam attempts do I get?",
]


# === HERO HEADER ===
st.markdown("""
<div class="vira-header">
    <div class="vira-title">VIRA</div>
    <div class="vira-subtitle">VIT Intelligent Regulation Assistant</div>
    <div class="vira-badge">Powered by Google Gemini 2.5 &middot; VIT Academic Regulations</div>
</div>
""", unsafe_allow_html=True)


# === SIDEBAR ===
with st.sidebar:
    st.markdown("### About VIRA")
    st.markdown("""
    VIRA uses **AI + RAG** to answer your questions about VIT Academic Regulations
    with accuracy and source citations.

    **Key Features:**
    - Cites specific regulations
    - Searches full regulation document
    - Remembers conversation context
    - Flags missing information honestly
    """)

    st.divider()

    if "messages" in st.session_state:
        msg_count = len([m for m in st.session_state.messages if m["role"] == "user"])
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{msg_count}</div>
            <div class="stat-label">Questions Asked</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.chat_history = []
        st.rerun()

    st.divider()

    st.markdown("""
    <div style="font-size:0.72rem; color:rgba(255,255,255,0.35); text-align:center;">
        VIRA v1.0 &middot; For informational purposes only<br>
        Always verify with official VIT portals
    </div>
    """, unsafe_allow_html=True)


# === SESSION STATE ===
if "messages" not in st.session_state:
    st.session_state.messages = []

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "suggested_question" not in st.session_state:
    st.session_state.suggested_question = None


# === LOAD ENGINE ===
with st.spinner("Initializing VIRA... (first load takes ~10 seconds)"):
    engine, error = load_vira_engine()


# === ERROR HANDLING ===
if error:
    st.error(f"**VIRA could not start:** {error}")
    if "Vector store not found" in error:
        st.info("""
        **To fix this, run the ingestion script first:**
        ```
        python scripts/ingest.py
        ```
        """)
    elif "GOOGLE_API_KEY" in error:
        st.info("""
        **To fix this:**
        1. Edit `.env` and add your API key
        2. Get a free key at: https://aistudio.google.com/
        """)
    st.stop()


# === WELCOME MESSAGE (shown when no messages yet) ===
if not st.session_state.messages:
    with st.chat_message("assistant", avatar="🎓"):
        st.markdown("""
**Welcome! I'm VIRA** — your AI guide to VIT Academic Regulations.

Ask me anything about:
- **Attendance** requirements and consequences
- **Grading** and CGPA calculation
- **Examination** rules and debarment
- **Course re-registration** and arrears
- **Scholarships** and awards

I'll always tell you which regulation my answer is based on, or honestly flag if something isn't covered.
        """)

    st.markdown("**Try asking:**")
    cols = st.columns(2)
    for i, q in enumerate(SAMPLE_QUESTIONS):
        with cols[i % 2]:
            if st.button(q, key=f"sample_{i}", use_container_width=True):
                st.session_state.suggested_question = q
                st.rerun()


# === DISPLAY CHAT HISTORY ===
for msg in st.session_state.messages:
    role = msg["role"]
    avatar = "🎓" if role == "assistant" else "👤"

    with st.chat_message(role, avatar=avatar):
        st.markdown(msg["content"])

        # Show source citations for assistant messages
        if role == "assistant" and msg.get("sources"):
            with st.expander(f"View {len(msg['sources'])} regulation excerpts used", expanded=False):
                for i, src in enumerate(msg["sources"], 1):
                    excerpt = src["content"][:450] + ("..." if len(src["content"]) > 450 else "")
                    st.markdown(f"""
<div class="source-box">
    <div class="source-title">Source {i} &mdash; {src['source']}</div>
    {excerpt}
</div>
""", unsafe_allow_html=True)


# === CHAT INPUT ===
default_input = ""
if st.session_state.suggested_question:
    default_input = st.session_state.suggested_question
    st.session_state.suggested_question = None

user_input = st.chat_input(
    placeholder="Ask about VIT regulations... e.g., What happens if my attendance is below 75%?"
)

question = user_input or (default_input if default_input else None)

if question and question.strip():
    q = question.strip()

    # Show user message
    with st.chat_message("user", avatar="👤"):
        st.markdown(q)

    st.session_state.messages.append({"role": "user", "content": q})

    # Generate and show VIRA's response
    with st.chat_message("assistant", avatar="🎓"):
        with st.spinner("Searching VIT regulations..."):
            start_t = time.time()
            try:
                result = engine.chat(question=q, chat_history=st.session_state.chat_history)
                answer = result["answer"]
                sources = result["sources"]
                elapsed = round(time.time() - start_t, 1)
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "quota" in err_str.lower() or "RESOURCE_EXHAUSTED" in err_str:
                    answer = (
                        "**API Rate Limit Reached**\n\n"
                        "The free Gemini API has a daily request limit. "
                        "This typically resets at midnight Pacific Time (around 1:30 PM IST).\n\n"
                        "**What you can do:**\n"
                        "- Wait a few minutes and try again\n"
                        "- If the daily limit is hit, please try again tomorrow\n"
                        "- For production use, consider upgrading to a paid API tier"
                    )
                else:
                    answer = f"I encountered an error: {err_str[:200]}\n\nPlease try rephrasing your question."
                sources = []
                elapsed = 0

        st.markdown(answer)

        if sources:
            with st.expander(f"View {len(sources)} regulation excerpts used  ({elapsed}s)", expanded=False):
                for i, src in enumerate(sources, 1):
                    excerpt = src["content"][:450] + ("..." if len(src["content"]) > 450 else "")
                    st.markdown(f"""
<div class="source-box">
    <div class="source-title">Source {i} &mdash; {src['source']}</div>
    {excerpt}
</div>
""", unsafe_allow_html=True)

    # Save to history
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources,
    })

    st.session_state.chat_history.append((q, answer))

    # Keep last 10 exchanges in memory
    if len(st.session_state.chat_history) > 10:
        st.session_state.chat_history = st.session_state.chat_history[-10:]

    st.rerun()
