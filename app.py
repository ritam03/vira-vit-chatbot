"""
VIRA - VIT Intelligent Regulation Assistant
Main Streamlit Application

Run with:
    streamlit run app.py
"""

import re
import base64
import urllib.parse
import streamlit as st
import streamlit.components.v1 as components
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
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://vit.ac.in",
        "About": "VIRA - VIT Intelligent Regulation Assistant v1.0",
    }
)

# ── Constants ──────────────────────────────────────────────────────────────────
QUESTION_LIMIT   = 15    # Max questions per session
QUESTION_WARNING = 12    # Show warning when this many used
MAX_INPUT_CHARS  = 500   # Max characters per question

# ── Helpers ───────────────────────────────────────────────────────────────────
def sanitize_input(text: str) -> str:
    """Strip HTML/script tags and enforce max length."""
    clean = re.sub(r"<[^>]+>", "", text)   # strip HTML tags
    clean = clean[:MAX_INPUT_CHARS]         # enforce length cap
    return clean.strip()

def render_copy_button(answer_text: str, key: str):
    """
    Render a styled 'Copy Answer' button using JavaScript.
    Uses execCommand('copy') which works inside iframes (Streamlit components)
    without needing clipboard-write permission.
    """
    b64 = base64.b64encode(answer_text.encode("utf-8")).decode("utf-8")
    html_content = f"""
    <style>
      .vira-copy-btn {{
        background: rgba(108,62,232,0.12);
        border: 1px solid rgba(108,62,232,0.3);
        border-radius: 8px;
        color: #C4B5FD;
        padding: 5px 16px;
        font-size: 0.78rem;
        cursor: pointer;
        font-family: Inter, sans-serif;
        font-weight: 500;
        transition: all 0.2s;
        margin-top: 4px;
      }}
      .vira-copy-btn:hover {{
        background: rgba(108,62,232,0.28);
        border-color: rgba(168,85,247,0.5);
      }}
    </style>
    <button class="vira-copy-btn" onclick="
      const text = atob('{b64}');
      const el = document.createElement('textarea');
      el.value = text;
      el.style.cssText = 'position:fixed;opacity:0;top:0;left:0;';
      document.body.appendChild(el);
      el.focus(); el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
      this.textContent = '✓ Copied!';
      this.style.color = '#34D399';
      this.style.borderColor = 'rgba(52,211,153,0.4)';
      setTimeout(() => {{
        this.textContent = '📋 Copy Answer';
        this.style.color = '#C4B5FD';
        this.style.borderColor = 'rgba(108,62,232,0.3)';
      }}, 2000);
    ">📋 Copy Answer</button>
    """
    components.html(html_content, height=40)


# --- Custom CSS ---
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

    /* ── Quota warning bar ── */
    .quota-warning {
        background: rgba(251,191,36,0.1);
        border: 1px solid rgba(251,191,36,0.3);
        border-radius: 10px;
        padding: 0.5rem 0.9rem;
        font-size: 0.82rem;
        color: #FCD34D;
        margin-bottom: 0.75rem;
    }

    /* ── Chat messages ── */
    .stChatMessage {
        animation: fadeUp 0.3s ease-out;
    }

    @keyframes fadeUp {
        from { opacity: 0; transform: translateY(8px); }
        to   { opacity: 1; transform: translateY(0); }
    }

    /* ── Sidebar stat card ── */
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

    /* ── Input char counter ── */
    .char-counter {
        font-size: 0.7rem;
        color: rgba(255,255,255,0.3);
        text-align: right;
        margin-top: -0.5rem;
        margin-bottom: 0.5rem;
    }
    .char-counter.warn { color: #F87171; }

    /* ── Mobile adaptations ── */
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 0.6rem;
            padding-right: 0.6rem;
            padding-bottom: 4.5rem;
        }
        .vira-header { border-radius: 14px; padding: 1.5rem 1rem; margin-bottom: 1rem; }
        .vira-title    { font-size: 2rem; }
        .vira-subtitle { font-size: 0.88rem; }
        .vira-badge    { font-size: 0.72rem; padding: 0.28rem 0.75rem; }
        .stButton > button {
            min-height: 48px !important;
            white-space: normal !important;
            word-break: break-word !important;
            line-height: 1.35 !important;
        }
        .stChatMessage p, .stChatMessage li { font-size: 0.95rem; line-height: 1.65; }
    }

    @media (max-width: 480px) {
        .vira-title  { font-size: 1.7rem; }
        .vira-header { border-radius: 10px; }
        .main .block-container { padding-left: 0.4rem; padding-right: 0.4rem; }
    }
</style>
""", unsafe_allow_html=True)


# --- Load VIRA Engine (cached - only runs once) ---
@st.cache_resource(show_spinner=False)
def load_vira_engine():
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

# ── Share URLs ─────────────────────────────────────────────────────────────────
_WA_TEXT = urllib.parse.quote(
    "🎓 Ask anything about VIT Academic Regulations instantly!\n\n"
    "VIRA is a free AI chatbot — get answers with regulation citations, "
    "no login needed.\n\n"
    "Try it: https://vitchat.streamlit.app"
)
WHATSAPP_URL = f"https://api.whatsapp.com/send?text={_WA_TEXT}"

REDDIT_URL = (
    "https://www.reddit.com/submit"
    "?url=https%3A%2F%2Fvitchat.streamlit.app"
    "&title=VIRA+%E2%80%94+Free+AI+chatbot+for+VIT+Academic+Regulations+%28instant+answers+with+citations%29"
)


# ═══════════════════════════════════════════════════════════════════════════════
# HERO HEADER
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="vira-header">
    <div class="vira-title">VIRA</div>
    <div class="vira-subtitle">VIT Intelligent Regulation Assistant</div>
    <div class="vira-badge">Powered by Google Gemini AI &middot; VIT Academic Regulations 2026</div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
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

    # Stats
    if "messages" in st.session_state:
        q_count = st.session_state.get("question_count", 0)
        msg_count = len([m for m in st.session_state.messages if m["role"] == "user"])
        remaining = QUESTION_LIMIT - q_count

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">{msg_count}</div>
                <div class="stat-label">Questions Asked</div>
            </div>
            """, unsafe_allow_html=True)
        with col_b:
            color = "#F87171" if remaining <= 3 else "#A855F7"
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value" style="color:{color};">{remaining}</div>
                <div class="stat-label">Remaining</div>
            </div>
            """, unsafe_allow_html=True)

    # Active model
    active_model = st.session_state.get("active_model", "Initializing...")
    st.markdown(f"""
    <div style="background:rgba(59,130,246,0.08);border:1px solid rgba(59,130,246,0.2);
                border-radius:10px;padding:0.5rem 0.75rem;margin-top:0.2rem;">
        <div style="font-size:0.65rem;color:rgba(255,255,255,0.4);text-transform:uppercase;letter-spacing:0.05em;">Active Model</div>
        <div style="font-size:0.78rem;color:#60A5FA;font-weight:500;margin-top:0.1rem;">{active_model}</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.chat_history = []
        st.session_state.question_count = 0
        st.rerun()

    st.divider()

    # Source document
    st.markdown("**Read the Source Document**")
    st.markdown("""
    <a href="https://drive.google.com/drive/folders/1qYHKwxWHTZ7qfQvVnongoCXuCQmNKIDg" target="_blank"
       style="display:flex;align-items:center;gap:0.5rem;background:rgba(108,62,232,0.12);
              border:1px solid rgba(108,62,232,0.3);border-radius:10px;padding:0.6rem 0.85rem;
              color:#C4B5FD;font-size:0.82rem;font-weight:500;text-decoration:none;">
        <span>📄</span> VIT Academic Regulations PDF
    </a>
    """, unsafe_allow_html=True)

    st.divider()

    # Share section
    st.markdown("**Share VIRA**")
    st.caption("Help fellow VIT students discover VIRA")
    col1, col2 = st.columns(2)
    with col1:
        st.link_button("💬 WhatsApp", WHATSAPP_URL, use_container_width=True)
    with col2:
        st.link_button("🔗 Reddit", REDDIT_URL, use_container_width=True)

    st.divider()

    st.markdown("""
    <div style="font-size:0.72rem; color:rgba(255,255,255,0.35); text-align:center;">
        VIRA v1.0 &middot; For informational purposes only<br>
        Always verify with official VIT portals
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════════
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "suggested_question" not in st.session_state:
    st.session_state.suggested_question = None
if "question_count" not in st.session_state:
    st.session_state.question_count = 0


# ═══════════════════════════════════════════════════════════════════════════════
# LOAD ENGINE
# ═══════════════════════════════════════════════════════════════════════════════
with st.spinner("Initializing VIRA... (first load takes ~10 seconds)"):
    engine, error = load_vira_engine()

if engine is not None:
    st.session_state["active_model"] = getattr(engine, "current_model", "gemini-2.5-flash")


# ═══════════════════════════════════════════════════════════════════════════════
# ERROR HANDLING
# ═══════════════════════════════════════════════════════════════════════════════
if error:
    st.error(f"**VIRA could not start:** {error}")
    if "Vector store not found" in error:
        st.info("**Fix:** Run `python scripts/ingest.py` first to build the vector database.")
    elif "GOOGLE_API_KEY" in error:
        st.info("**Fix:** Add your API key to `.env`. Get one free at https://aistudio.google.com/")
    st.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# QUOTA WARNING BANNER
# ═══════════════════════════════════════════════════════════════════════════════
q_count = st.session_state.question_count
if q_count >= QUESTION_WARNING and q_count < QUESTION_LIMIT:
    remaining = QUESTION_LIMIT - q_count
    st.markdown(f"""
    <div class="quota-warning">
        ⚠️ <strong>{remaining} question{"s" if remaining != 1 else ""} remaining</strong>
        in this session &mdash; refresh the page to start a new session.
    </div>
    """, unsafe_allow_html=True)

if q_count >= QUESTION_LIMIT:
    st.error(
        "**Session limit reached (15 questions)**\n\n"
        "This limit prevents overloading the free API for other users. "
        "Please **refresh the page** to start a new session."
    )
    st.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# WELCOME MESSAGE
# ═══════════════════════════════════════════════════════════════════════════════
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


# ═══════════════════════════════════════════════════════════════════════════════
# DISPLAY CHAT HISTORY
# ═══════════════════════════════════════════════════════════════════════════════
for idx, msg in enumerate(st.session_state.messages):
    role = msg["role"]
    avatar = "🎓" if role == "assistant" else "👤"

    with st.chat_message(role, avatar=avatar):
        st.markdown(msg["content"])
        # Copy button on every assistant answer
        if role == "assistant":
            render_copy_button(msg["content"], key=f"hist_{idx}")


# ═══════════════════════════════════════════════════════════════════════════════
# CHAT INPUT
# ═══════════════════════════════════════════════════════════════════════════════
default_input = ""
if st.session_state.suggested_question:
    default_input = st.session_state.suggested_question
    st.session_state.suggested_question = None

user_input = st.chat_input(
    placeholder="Ask about VIT regulations... e.g., What happens if my attendance is below 75%?"
)

question = user_input or (default_input if default_input else None)

if question and question.strip():
    # ── Input validation ──────────────────────────────────────────────────────
    raw_q = question.strip()
    q = sanitize_input(raw_q)

    if not q:
        st.warning("Please enter a valid question.")
        st.stop()

    if len(raw_q) > MAX_INPUT_CHARS:
        st.warning(f"Question too long — please keep it under {MAX_INPUT_CHARS} characters.")
        st.stop()

    # ── Display user message ──────────────────────────────────────────────────
    with st.chat_message("user", avatar="👤"):
        st.markdown(q)

    st.session_state.messages.append({"role": "user", "content": q})
    st.session_state.question_count += 1

    # ── Generate VIRA's response ──────────────────────────────────────────────
    with st.chat_message("assistant", avatar="🎓"):
        with st.spinner("Searching VIT regulations..."):
            try:
                result = engine.chat(question=q, chat_history=st.session_state.chat_history)
                answer = result["answer"]
                model_used = result.get("model_used", "")
                if model_used:
                    st.session_state["active_model"] = model_used
            except ResourceWarning:
                answer = (
                    "**Daily Limit Reached Across All Models**\n\n"
                    "VIRA uses 7 different Gemini models (~140 requests/day total). "
                    "Today's quota has been fully used.\n\n"
                    "**Quotas reset at:** midnight Pacific Time (~1:30 AM IST)\n\n"
                    "Please come back tomorrow — everything will work normally!"
                )
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "quota" in err_str.lower() or "RESOURCE_EXHAUSTED" in err_str:
                    answer = (
                        "**Rate Limit Hit** — switching to the next available model.\n\n"
                        "Please send your question again."
                    )
                else:
                    answer = f"I encountered an error: {err_str[:200]}\n\nPlease try rephrasing."

        st.markdown(answer)
        render_copy_button(answer, key=f"new_{st.session_state.question_count}")

    # ── Save to history ───────────────────────────────────────────────────────
    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.session_state.chat_history.append((q, answer))

    # Keep last 10 exchanges in memory
    if len(st.session_state.chat_history) > 10:
        st.session_state.chat_history = st.session_state.chat_history[-10:]

    st.rerun()
