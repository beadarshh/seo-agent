from supabase import create_client, Client
from config import settings

def get_supabase() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

SETUP_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url TEXT NOT NULL,
    title TEXT,
    meta_description TEXT,
    content TEXT,
    target_keyword TEXT,
    headings JSONB,
    word_count INT,
    seo_score INT,
    published_at TIMESTAMPTZ,
    performance_status TEXT DEFAULT 'tracking',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Migration for User Email
ALTER TABLE pages ADD COLUMN IF NOT EXISTS user_email TEXT;
ALTER TABLE pages DROP CONSTRAINT IF EXISTS pages_url_key;
ALTER TABLE pages ADD CONSTRAINT pages_user_url_unique UNIQUE (user_email, url);

CREATE TABLE IF NOT EXISTS suggestions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    page_id UUID REFERENCES pages(id),
    type TEXT,
    priority TEXT,
    original_value TEXT,
    suggested_value TEXT,
    reason TEXT,
    is_accepted BOOLEAN DEFAULT FALSE,
    accepted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS two_week_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    page_id UUID REFERENCES pages(id),
    competitor_urls TEXT[],
    competitor_analysis JSONB,
    gap_suggestions JSONB,
    overall_score INT,
    completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS seo_knowledge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT,
    embedding vector(384),
    source TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Function for vector search
CREATE OR REPLACE FUNCTION match_seo_knowledge (
  query_embedding vector(384),
  match_threshold float,
  match_count int
)
RETURNS TABLE (
  id uuid,
  content text,
  source text,
  similarity float
)
LANGUAGE sql STABLE
AS $$
  SELECT
    seo_knowledge.id,
    seo_knowledge.content,
    seo_knowledge.source,
    1 - (seo_knowledge.embedding <=> query_embedding) AS similarity
  FROM seo_knowledge
  WHERE 1 - (seo_knowledge.embedding <=> query_embedding) > match_threshold
  ORDER BY similarity DESC
  LIMIT match_count;
$$;
"""
