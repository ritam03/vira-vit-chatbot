"""
VIRA - VIT Intelligent Regulation Assistant
Main Streamlit Application

Run with:
    streamlit run app.py
"""

import streamlit as st
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
    page_icon="🎓",
    layout="wide",               # Premium wide layout for PC/Laptop
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://vit.ac.in",
        "About": "VIRA - VIT Intelligent Regulation Assistant v1.0",
    }
)

# --- Custom CSS ---
# Desktop-first design. @media queries handle mobile as an enhancement.
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    #MainMenu {visibility: hidden;}
    footer    {visibility: hidden;}
    header    {visibility: hidden;}

    /* ── Main container ── */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }

    /* ── Hero header ── */
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
        0%   { transform: rotate(0deg); }
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

    /* ── Chat messages ── */
    .stChatMessage {
        animation: fadeUp 0.3s ease-out;
    }

    @keyframes fadeUp {
        from { opacity: 0; transform: translateY(8px); }
        to   { opacity: 1; transform: translateY(0); }
    }

    /* ── Stat card in sidebar ── */
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

    hr { border-color: rgba(255,255,255,0.07) !important; }

    /* ════════════════════════════════════════
       MOBILE ADAPTATIONS  (≤ 768px)
       Only these rules change on phones.
       Everything above stays premium on desktop.
    ════════════════════════════════════════ */
    @media (max-width: 768px) {

        /* Tighten container padding */
        .main .block-container {
            padding-left: 0.6rem;
            padding-right: 0.6rem;
            padding-bottom: 4.5rem;
        }

        /* Scale header down gracefully */
        .vira-header {
            border-radius: 14px;
            padding: 1.5rem 1rem;
            margin-bottom: 1rem;
        }

        .vira-title    { font-size: 2rem; }
        .vira-subtitle { font-size: 0.88rem; }
        .vira-badge    { font-size: 0.72rem; padding: 0.28rem 0.75rem; }

        /* Buttons: 48px min tap target, text wraps */
        .stButton > button {
            min-height: 48px !important;
            white-space: normal !important;
            word-break: break-word !important;
            line-height: 1.35 !important;
            font-size: 0.88rem !important;
        }

        /* Chat input: bigger on mobile */
        .stChatInputContainer textarea {
            font-size: 1rem !important;
            min-height: 48px !important;
        }

        /* Readable text in chat bubbles */
        .stChatMessage p,
        .stChatMessage li {
            font-size: 0.95rem;
            line-height: 1.65;
        }
    }

    @media (max-width: 480px) {
        .vira-title    { font-size: 1.7rem; }
        .vira-header   { border-radius: 10px; }
        .main .block-container {
            padding-left: 0.4rem;
            padding-right: 0.4rem;
        }
    }
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
    <div class="vira-badge">Powered by Google Gemini AI &middot; VIT Academic Regulations 2026</div>
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

    # Active model card — reads from session_state (populated after engine loads)
    active_model = st.session_state.get("active_model", "Initializing...")
    st.markdown(f"""
    <div style="background:rgba(59,130,246,0.08);border:1px solid rgba(59,130,246,0.2);
                border-radius:10px;padding:0.5rem 0.75rem;margin-top:0.4rem;">
        <div style="font-size:0.65rem;color:rgba(255,255,255,0.4);text-transform:uppercase;letter-spacing:0.05em;">Active Model</div>
        <div style="font-size:0.78rem;color:#60A5FA;font-weight:500;margin-top:0.1rem;">{active_model}</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.chat_history = []
        st.rerun()

    st.divider()

    st.markdown("**Read the Source Document**")
    st.markdown("""
    <a href="https://drive.google.com/drive/folders/1qYHKwxWHTZ7qfQvVnongoCXuCQmNKIDg" target="_blank"
       style="display:flex;align-items:center;gap:0.5rem;background:rgba(108,62,232,0.12);
              border:1px solid rgba(108,62,232,0.3);border-radius:10px;padding:0.6rem 0.85rem;
              color:#C4B5FD;font-size:0.82rem;font-weight:500;text-decoration:none;
              transition:background 0.2s;">
        <span style="font-size:1rem;">&#128196;</span>
        VIT Academic Regulations PDF
    </a>
    """, unsafe_allow_html=True)

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

# Update session_state with the current model so the sidebar can read it
if engine is not None:
    st.session_state["active_model"] = getattr(engine, "current_model", "gemini-2.5-flash")


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
    # 2-column grid on desktop, gracefully stacks on mobile
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

        # Regulation basis is cited inline in the answer — no separate expander needed


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
            try:
                result = engine.chat(question=q, chat_history=st.session_state.chat_history)
                answer = result["answer"]
                model_used = result.get("model_used", "")
                # Keep sidebar model indicator current
                if model_used:
                    st.session_state["active_model"] = model_used
            except ResourceWarning:
                # All 7 models in the cascade are exhausted for the day
                answer = (
                    "**Daily Limit Reached Across All Models**\n\n"
                    "VIRA uses 7 different Gemini models to maximize free-tier capacity "
                    "(~140 requests/day total). Today's quota has been fully used.\n\n"
                    "**Quotas reset at:** midnight Pacific Time (~1:30 AM IST)\n\n"
                    "Please come back tomorrow — everything will work normally!"
                )
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "quota" in err_str.lower() or "RESOURCE_EXHAUSTED" in err_str:
                    answer = (
                        "**Rate Limit Hit**\n\n"
                        "Switching to the next available model... "
                        "Please send your question again."
                    )
                else:
                    answer = f"I encountered an error: {err_str[:200]}\n\nPlease try rephrasing."

        st.markdown(answer)

    # Save to history
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
    })

    st.session_state.chat_history.append((q, answer))

    # Keep last 10 exchanges in memory
    if len(st.session_state.chat_history) > 10:
        st.session_state.chat_history = st.session_state.chat_history[-10:]

    st.rerun()
