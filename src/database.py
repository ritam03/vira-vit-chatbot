import os
import time
from datetime import datetime, timezone
from supabase import create_client, Client
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def get_supabase() -> Client:
    """Initialize and return the Supabase client."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Supabase URL and Key must be set in environment variables.")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def get_usage(identifier: str) -> int:
    """Get the number of questions asked today for a given identifier."""
    supabase = get_supabase()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    response = supabase.table("daily_usage").select("question_count").eq("identifier", identifier).eq("usage_date", today_str).execute()
    
    if len(response.data) > 0:
        return response.data[0]["question_count"]
    return 0

def increment_usage(identifier: str) -> int:
    """Increment and return the usage count for today."""
    supabase = get_supabase()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    current = get_usage(identifier)
    
    if current == 0:
        # First question today, insert new row
        supabase.table("daily_usage").insert({
            "identifier": identifier,
            "usage_date": today_str,
            "question_count": 1
        }).execute()
        return 1
    else:
        # Update existing row
        new_count = current + 1
        supabase.table("daily_usage").update({
            "question_count": new_count
        }).eq("identifier", identifier).eq("usage_date", today_str).execute()
        return new_count

def log_chat(identifier: str, question: str, model_used: str, response_time_ms: int):
    """Log the chat query for analytics."""
    supabase = get_supabase()
    try:
        supabase.table("chat_logs").insert({
            "identifier": identifier,
            "question": question,
            "model_used": model_used,
            "response_time_ms": response_time_ms
        }).execute()
    except Exception as e:
        print(f"Error logging chat: {e}")
