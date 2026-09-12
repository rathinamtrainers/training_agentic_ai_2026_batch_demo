-- Runs once, the first time the Postgres volume is created.
--
-- Nothing in session 2 uses this. It is here so that session 3 opens with a
-- database that already has the extension, instead of five minutes of
-- "CREATE EXTENSION" in front of a live room.
CREATE EXTENSION IF NOT EXISTS vector;

-- Proof for the demo: `docker compose exec postgres psql -U agentic -d agentic
-- -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"`
