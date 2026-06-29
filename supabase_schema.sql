-- VIRA Database Schema
-- Run this in your Supabase SQL Editor to set up the necessary tables

-- 1. Create daily_usage table to track question limits
CREATE TABLE IF NOT EXISTS public.daily_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identifier TEXT NOT NULL, -- Either a guest cookie ID or authenticated user ID
    usage_date DATE NOT NULL DEFAULT CURRENT_DATE,
    question_count INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT unique_usage_per_day UNIQUE (identifier, usage_date)
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_daily_usage_identifier_date ON public.daily_usage(identifier, usage_date);

-- 2. Create chat_logs table for the Admin Dashboard Analytics
CREATE TABLE IF NOT EXISTS public.chat_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identifier TEXT NOT NULL, -- Either a guest cookie ID or authenticated user ID
    question TEXT NOT NULL,
    model_used TEXT,
    response_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- Index for chronological queries
CREATE INDEX IF NOT EXISTS idx_chat_logs_created_at ON public.chat_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_chat_logs_identifier ON public.chat_logs(identifier);

-- 3. Set up Row Level Security (RLS) policies
-- Note: Since VIRA connects via a single server-side service key (the Streamlit backend),
-- we can allow anon access for inserts/selects from the Streamlit backend.

-- Enable RLS (Recommended for safety)
ALTER TABLE public.daily_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_logs ENABLE ROW LEVEL SECURITY;

-- Allow all operations from anon/authenticated (Streamlit will securely manage the logic)
CREATE POLICY "Allow all operations for anon" ON public.daily_usage FOR ALL USING (true);
CREATE POLICY "Allow all operations for anon" ON public.chat_logs FOR ALL USING (true);

-- Done!
