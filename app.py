"""
VIRA - VIT Intelligent Regulation Assistant
Main Streamlit Application
"""

import re
import os
import time
import uuid
import base64
import urllib.parse
import streamlit as st
import streamlit.components.v1 as components
import sys
import io
import pandas as pd
from streamlit_cookies_controller import CookieController
from src.database import get_usage, increment_usage, log_chat, get_supabase

# Force UTF-8 stdout
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

st.set_page_config(
    page_title="VIRA - VIT Regulation Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://vit.ac.in",
        "About": "VIRA - VIT Intelligent Regulation Assistant v2.0 (Prod)",
    }
)

# ── Constants ──────────────────────────────────────────────────────────────────
GUEST_LIMIT      = 3     # Max questions per day for guests
USER_LIMIT       = 15    # Max questions per day for logged-in users
MAX_INPUT_CHARS  = 500   # Max characters per question
ADMIN_SECRET     = os.environ.get("ADMIN_SECRET", "VITADMIN")

supabase = get_supabase()
cookies = CookieController()

# ── Identity Management ───────────────────────────────────────────────────────
vira_user_id = cookies.get('vira_user_id')
vira_guest_id = cookies.get('vira_guest_id')

is_logged_in = bool(vira_user_id)
limit = USER_LIMIT if is_logged_in else GUEST_LIMIT

# If cookie hasn't loaded or doesn't exist, use a placeholder.
# We DO NOT call cookies.set() here to prevent overwriting during rapid page reloads!
if is_logged_in:
    identifier = vira_user_id
elif vira_guest_id:
    identifier = vira_guest_id
else:
    if "temp_guest_id" not in st.session_state:
        st.session_state.temp_guest_id = str(uuid.uuid4())
    identifier = st.session_state.temp_guest_id

# ── Helpers ───────────────────────────────────────────────────────────────────
def sanitize_input(text: str) -> str:
    clean = re.sub(r"<[^>]+>", "", text)
    clean = clean[:MAX_INPUT_CHARS]
    return clean.strip()

def render_copy_button(answer_text: str, key: str):
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

    .main .block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 1200px; }

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
    .vira-title { font-size: 2.8rem; font-weight: 700; color: white; margin: 0; }
    .vira-subtitle { font-size: 1rem; color: rgba(255,255,255,0.85); margin-top: 0.5rem; }
    .vira-badge {
        display: inline-block; background: rgba(255,255,255,0.2);
        backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.3);
        border-radius: 50px; padding: 0.3rem 1rem; font-size: 0.8rem;
        color: white; margin-top: 1rem; font-weight: 500;
    }
    .quota-warning {
        background: rgba(251,191,36,0.1); border: 1px solid rgba(251,191,36,0.3);
        border-radius: 10px; padding: 0.5rem 0.9rem; font-size: 0.82rem;
        color: #FCD34D; margin-bottom: 0.75rem; text-align: center;
    }
    .stat-card {
        background: rgba(108, 62, 232, 0.12); border: 1px solid rgba(108, 62, 232, 0.25);
        border-radius: 12px; padding: 0.75rem; margin-bottom: 0.5rem; text-align: center;
    }
    .stat-value { font-size: 1.8rem; font-weight: 700; color: #A855F7; }
    .stat-label { font-size: 0.72rem; color: rgba(255,255,255,0.45); }
    hr { border-color: rgba(255,255,255,0.07) !important; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
query_params = st.query_params
if query_params.get("admin") == ADMIN_SECRET:
    st.markdown("## 🔒 VIRA Admin Dashboard")
    st.info("You are viewing the hidden admin dashboard. Regular users cannot see this.")
    
    col1, col2, col3 = st.columns(3)
    try:
        # Fetch data
        logs = supabase.table("chat_logs").select("*").execute().data
        usage = supabase.table("daily_usage").select("*").execute().data
        
        df_logs = pd.DataFrame(logs)
        df_usage = pd.DataFrame(usage)
        
        total_questions = len(df_logs) if not df_logs.empty else 0
        total_users = len(df_usage['identifier'].unique()) if not df_usage.empty else 0
        avg_time = df_logs['response_time_ms'].mean() / 1000 if not df_logs.empty else 0
        
        col1.metric("Total Questions Asked", total_questions)
        col2.metric("Total Unique Users", total_users)
        col3.metric("Avg Response Time (s)", f"{avg_time:.2f}")
        
        st.divider()
        st.markdown("### Recent Questions")
        if not df_logs.empty:
            df_display = df_logs[['created_at', 'model_used', 'response_time_ms', 'question']].sort_values(by="created_at", ascending=False)
            st.dataframe(df_display, use_container_width=True)
        else:
            st.write("No logs yet.")
            
    except Exception as e:
        st.error(f"Failed to load analytics: {e}")
        
    st.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# ENGINE LOAD & SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════════
@st.cache_resource(show_spinner=False)
def load_vira_engine():
    try:
        from src.rag_pipeline import VIRAEngine
        return VIRAEngine(), None
    except Exception as e:
        return None, str(e)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "suggested_question" not in st.session_state:
    st.session_state.suggested_question = None

with st.spinner("Initializing VIRA..."):
    engine, error = load_vira_engine()
if engine:
    st.session_state["active_model"] = getattr(engine, "current_model", "gemini-2.5-flash")

if error:
    st.error(f"**VIRA Error:** {error}")
    st.stop()

# ═══════════════════════════════════════════════════════════════════════════════
# UI: HERO
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
# Calculate persistent usage limit
current_usage = get_usage(identifier)
remaining = max(0, limit - current_usage)

with st.sidebar:
    st.markdown("### Authentication")
    if is_logged_in:
        st.success(f"**Student Account Active**\n\nDaily Quota: {USER_LIMIT} questions")
        if st.button("Log Out", use_container_width=True):
            cookies.remove('vira_user_id')
            st.rerun()
    else:
        st.info(f"**Guest Mode**\n\nDaily Quota: {GUEST_LIMIT} questions")
        with st.expander("🔐 Log In / Sign Up"):
            auth_mode = st.radio("Mode", ["Sign In", "Sign Up"], horizontal=True)
            email = st.text_input("Email (VIT or Personal)")
            password = st.text_input("Password", type="password")
            
            if st.button(auth_mode, use_container_width=True):
                if email and password:
                    try:
                        if auth_mode == "Sign Up":
                            res = supabase.auth.sign_up({"email": email, "password": password})
                            st.success("Signed up successfully! Please sign in now.")
                        else:
                            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                            cookies.set('vira_user_id', res.user.id)
                            st.success("Logged in successfully!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.warning("Provide both email and password.")

    st.divider()
    
    st.markdown("### Today's Usage")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{current_usage}</div>
            <div class="stat-label">Used</div>
        </div>
        """, unsafe_allow_html=True)
    with col_b:
        color = "#F87171" if remaining == 0 else "#34D399"
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value" style="color:{color};">{remaining}</div>
            <div class="stat-label">Remaining</div>
        </div>
        """, unsafe_allow_html=True)

    if not is_logged_in and current_usage >= GUEST_LIMIT:
        st.markdown("""
        <div class="quota-warning">
            Unlock 15 daily questions by creating a free account above.
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # Context clearing (doesn't reset db quota)
    if st.button("➕ Start New Chat", use_container_width=True, help="Clears conversation memory. Does NOT reset daily quota."):
        st.session_state.messages = []
        st.session_state.chat_history = []
        st.rerun()

    st.divider()
    st.markdown("**Read the Source Document**")
    st.markdown("""
    <a href="https://drive.google.com/drive/folders/1qYHKwxWHTZ7qfQvVnongoCXuCQmNKIDg" target="_blank"
       style="display:flex;align-items:center;gap:0.5rem;background:rgba(108,62,232,0.12);
              border:1px solid rgba(108,62,232,0.3);border-radius:10px;padding:0.6rem 0.85rem;
              color:#C4B5FD;font-size:0.82rem;font-weight:500;text-decoration:none;">
        <span>📄</span> VIT Academic Regulations PDF
    </a>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# QUOTA ENFORCEMENT & WARNING
# ═══════════════════════════════════════════════════════════════════════════════
if remaining == 0:
    st.error(
        f"**Daily Limit Reached ({limit} questions)**\n\n"
        "Your quota resets at midnight. "
        + ("Log in or sign up to unlock 15 questions per day!" if not is_logged_in else "")
    )
    st.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# WELCOME MESSAGE & MAIN CHAT
# ═══════════════════════════════════════════════════════════════════════════════
if not st.session_state.messages:
    with st.chat_message("assistant", avatar="🎓"):
        st.markdown("**Welcome! I'm VIRA** — your AI guide to VIT Academic Regulations.")
    
    SAMPLE_QUESTIONS = [
        "What is the minimum attendance required at VIT?",
        "How is CGPA calculated at VIT?",
        "What happens if I fail a subject?",
        "What are the scholarship criteria?"
    ]
    st.markdown("**Try asking:**")
    cols = st.columns(2)
    for i, q in enumerate(SAMPLE_QUESTIONS):
        with cols[i % 2]:
            if st.button(q, key=f"sample_{i}", use_container_width=True):
                st.session_state.suggested_question = q
                st.rerun()

for idx, msg in enumerate(st.session_state.messages):
    role = msg["role"]
    avatar = "🎓" if role == "assistant" else "👤"
    with st.chat_message(role, avatar=avatar):
        st.markdown(msg["content"])
        if role == "assistant":
            render_copy_button(msg["content"], key=f"hist_{idx}")

default_input = st.session_state.suggested_question if st.session_state.suggested_question else ""
st.session_state.suggested_question = None

user_input = st.chat_input(placeholder="Ask about VIT regulations... e.g., What happens if my attendance is below 75%?")
question = user_input or default_input

if question and question.strip():
    q = sanitize_input(question)
    if not q: st.stop()
    
    # If using the temporary ID, they truly had no cookie. Lock it in now.
    if identifier == st.session_state.get("temp_guest_id"):
        cookies.set('vira_guest_id', identifier)

    # User message
    with st.chat_message("user", avatar="👤"):
        st.markdown(q)
    st.session_state.messages.append({"role": "user", "content": q})

    # Assistant processing
    with st.chat_message("assistant", avatar="🎓"):
        with st.spinner("Searching VIT regulations..."):
            start_time = time.time()
            model_used = "unknown"
            try:
                result = engine.chat(question=q, chat_history=st.session_state.chat_history)
                answer = result["answer"]
                model_used = result.get("model_used", "gemini-2.5-flash")
                st.session_state["active_model"] = model_used
            except Exception as e:
                answer = f"I encountered an error: {str(e)[:200]}"
            
            elapsed_ms = int((time.time() - start_time) * 1000)

        st.markdown(answer)
        render_copy_button(answer, key=f"new_{current_usage}")

    # Track usage & Log
    increment_usage(identifier)
    log_chat(identifier, q, model_used, elapsed_ms)

    # State update
    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.session_state.chat_history.append((q, answer))
    if len(st.session_state.chat_history) > 10:
        st.session_state.chat_history = st.session_state.chat_history[-10:]

    st.rerun()
