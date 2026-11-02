-- Track which interactions have already been turned into memories.
-- Run once in the Supabase SQL Editor. Safe to re-run.

alter table interactions
  add column if not exists memory_extracted boolean not null default false;

create index if not exists idx_interactions_pending
  on interactions (created_at)
  where memory_extracted = false;
