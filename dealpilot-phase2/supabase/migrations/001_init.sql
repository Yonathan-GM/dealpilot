-- DealPilot schema. Run once in the Supabase SQL Editor. Safe to re-run.

create extension if not exists vector;

-- 1) Customers ---------------------------------------------------------
create table if not exists customers (
  id            uuid primary key default gen_random_uuid(),
  name          text not null unique,
  industry      text,
  contact_name  text,
  contact_email text,
  status        text not null default 'lead'
                check (status in ('lead', 'active', 'at_risk', 'churned')),
  notes         text,
  created_at    timestamptz not null default now()
);

-- 2) Interactions: every call / email / meeting with a customer ---------
create table if not exists interactions (
  id          uuid primary key default gen_random_uuid(),
  customer_id uuid not null references customers(id) on delete cascade,
  channel     text not null check (channel in ('email', 'call', 'meeting', 'note')),
  content     text not null,
  occurred_at timestamptz not null default now(),
  created_at  timestamptz not null default now()
);
create index if not exists idx_interactions_customer
  on interactions (customer_id, occurred_at desc);

-- 3) Documents: one row per uploaded file --------------------------------
create table if not exists documents (
  id          uuid primary key default gen_random_uuid(),
  filename    text not null unique,
  doc_type    text,
  customer_id uuid references customers(id) on delete set null, -- null = company-wide
  created_at  timestamptz not null default now()
);

-- 4) Chunks: pieces of documents + their embeddings (768 dims) -----------
create table if not exists chunks (
  id          uuid primary key default gen_random_uuid(),
  document_id uuid not null references documents(id) on delete cascade,
  chunk_index int  not null,
  content     text not null,
  embedding   vector(768) not null,
  fts         tsvector generated always as (to_tsvector('english', content)) stored,
  created_at  timestamptz not null default now()
);
create index if not exists idx_chunks_embedding
  on chunks using hnsw (embedding vector_cosine_ops);
create index if not exists idx_chunks_fts on chunks using gin (fts);
create index if not exists idx_chunks_document on chunks (document_id);

-- 5) Memories: short facts learned about a customer ----------------------
create table if not exists memories (
  id                    uuid primary key default gen_random_uuid(),
  customer_id           uuid not null references customers(id) on delete cascade,
  fact                  text not null,
  embedding             vector(768) not null,
  source_interaction_id uuid references interactions(id) on delete set null,
  created_at            timestamptz not null default now()
);
create index if not exists idx_memories_embedding
  on memories using hnsw (embedding vector_cosine_ops);
create index if not exists idx_memories_customer on memories (customer_id);

-- 6) Search functions (called from Python via supabase.rpc) --------------
create or replace function match_chunks(
  query_embedding vector(768),
  match_count     int   default 5,
  match_threshold float default 0.0
)
returns table (
  id uuid, document_id uuid, filename text,
  chunk_index int, content text, similarity float
)
language sql stable
as $$
  select c.id, c.document_id, d.filename, c.chunk_index, c.content,
         1 - (c.embedding <=> query_embedding) as similarity
  from chunks c
  join documents d on d.id = c.document_id
  where 1 - (c.embedding <=> query_embedding) > match_threshold
  order by c.embedding <=> query_embedding
  limit match_count;
$$;

create or replace function match_memories(
  query_embedding vector(768),
  p_customer_id   uuid,
  match_count     int default 5
)
returns table (id uuid, fact text, similarity float, created_at timestamptz)
language sql stable
as $$
  select m.id, m.fact,
         1 - (m.embedding <=> query_embedding) as similarity,
         m.created_at
  from memories m
  where m.customer_id = p_customer_id
  order by m.embedding <=> query_embedding
  limit match_count;
$$;

-- 7) Security: lock tables to the public (anon) key. -----------------------
-- Our backend uses the secret key, which bypasses RLS.
alter table customers    enable row level security;
alter table interactions enable row level security;
alter table documents    enable row level security;
alter table chunks       enable row level security;
alter table memories     enable row level security;
