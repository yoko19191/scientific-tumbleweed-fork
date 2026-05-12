-- Initial ParadeDB extensions bootstrap.
-- The paradedb/* images preload these, but declaring them here makes the
-- setup portable to vanilla postgres + pgvector/pg_search packages and
-- guarantees a healthy schema on a fresh volume.

-- pgvector — ANN/embeddings search support.
CREATE EXTENSION IF NOT EXISTS vector;

-- pg_search — ParadeDB BM25 full-text search.
CREATE EXTENSION IF NOT EXISTS pg_search;

-- pg_stat_statements — query-level observability; used by production monitoring.
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
