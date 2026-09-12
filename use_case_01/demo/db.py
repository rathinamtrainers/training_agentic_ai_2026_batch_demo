"""The store. One table, and `tenant_id` is in it from the first row.

Teaching point: isolation is a column, present at the first insert. There is no
cheap moment later to add it -- retrofitting a tenant key onto a table that
already holds four teams' documents means re-ingesting everything and trusting
that you got the backfill right.

`clause` is the other column that matters here. Northwind's answer is not
"it is in the escape-of-water document", it is "clause 4.2 of the
escape-of-water document". A citation you cannot open at the right paragraph is
decoration, so the clause travels with the chunk from ingestion onwards.
"""

import psycopg
from pgvector.psycopg import register_vector

import config

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS chunks (
    id           bigserial PRIMARY KEY,
    tenant_id    text NOT NULL,              -- <-- row one. Not bolted on later.
    source_file  text NOT NULL,
    clause       text NOT NULL,              -- "4"  -- what gets cited
    heading      text NOT NULL,              -- "Escape of water"
    chunk_index  int  NOT NULL,
    content      text NOT NULL,
    embedding    vector({config.EMBEDDING_DIMS}) NOT NULL,
    -- the lexical half of hybrid search, maintained by Postgres itself so it
    -- can never drift out of step with the content column
    tsv          tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
);

CREATE INDEX IF NOT EXISTS chunks_tenant_idx ON chunks (tenant_id);
CREATE INDEX IF NOT EXISTS chunks_tsv_idx    ON chunks USING gin (tsv);
"""


def connect() -> psycopg.Connection:
    settings = config.db_settings()
    print(
        f"[db] connecting to {settings['user']}@{settings['host']}:"
        f"{settings['port']}/{settings['dbname']}"
    )
    try:
        conn = psycopg.connect(**settings, autocommit=True, connect_timeout=10)
    except psycopg.OperationalError as error:
        config.fail(
            "POSTGRES IS NOT ANSWERING.\n"
            f"[config] {error}\n"
            "[config] Start it with:  docker compose up -d"
        )
    # The extension has to exist BEFORE psycopg is told about the vector type,
    # otherwise there is no type for it to look up. On a database that has been
    # ingested once this is a no-op; on a fresh container it is the difference
    # between the demo running and the demo not running.
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    register_vector(conn)
    return conn


def ensure_schema(conn: psycopg.Connection) -> None:
    print("[db] applying schema (CREATE EXTENSION vector, CREATE TABLE chunks ...)")
    conn.execute(SCHEMA)
    print("[db] schema ready")


def counts_by_tenant(conn: psycopg.Connection) -> list[tuple[str, int, int]]:
    """(tenant, chunks, documents) -- the shape of the store, in one query."""
    return conn.execute(
        "SELECT tenant_id, count(*), count(DISTINCT source_file)"
        "  FROM chunks GROUP BY tenant_id ORDER BY tenant_id"
    ).fetchall()
