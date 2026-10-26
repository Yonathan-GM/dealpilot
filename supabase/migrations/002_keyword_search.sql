-- Keyword (full-text) search over chunks. Run once in the Supabase SQL Editor.
-- websearch_to_tsquery understands plain text; our Python code joins the
-- question's words with "or" so a chunk matching MORE words ranks higher.

create or replace function keyword_chunks(
  query_text  text,
  match_count int default 5
)
returns table (
  id uuid, document_id uuid, filename text,
  chunk_index int, content text, rank float
)
language sql stable
as $$
  select c.id, c.document_id, d.filename, c.chunk_index, c.content,
         ts_rank_cd(c.fts, websearch_to_tsquery('english', query_text))::float as rank
  from chunks c
  join documents d on d.id = c.document_id
  where c.fts @@ websearch_to_tsquery('english', query_text)
  order by rank desc
  limit match_count;
$$;
