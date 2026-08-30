"""The vectors live in Postgres, and the search is one SQL statement.

Real PostgreSQL 18 + pgvector 0.8.6 (the course's own container) and real gemini-embedding-001.
    docker compose -f ../demo/docker-compose.yml up -d
    uv run --project ../demo python 11_pgvector_is_the_store.py
"""
import os

import psycopg
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pgvector.psycopg import register_vector

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "demo", ".env"))
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI",
                      "TRUE" if os.getenv("GENAI_BACKEND") == "vertex" else "FALSE")
client, DIMS = genai.Client(), int(os.getenv("EMBEDDING_DIMS", "768"))
EMBED = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")

ROWS = [("claims", "01_escape_of_water.md", "4", "Escape of water from a neighbouring flat is covered. Excess GBP 350."),
        ("claims", "03_gradual_seepage.md", "1", "Damage from gradual seepage over weeks or months is excluded."),
        ("claims", "08_excess_and_settlement.md", "2", "The standard buildings excess is GBP 250."),
        ("claims", "07_complaints.md", "3", "A final response to a complaint is due within eight weeks.")]
QUESTION = "water coming through the ceiling from the flat upstairs"

def embed(texts, task):
    config = types.EmbedContentConfig(task_type=task, output_dimensionality=DIMS)
    return [e.values for e in client.models.embed_content(model=EMBED, contents=texts, config=config).embeddings]

conn = psycopg.connect(f"host={os.getenv('POSTGRES_HOST', 'localhost')} dbname={os.getenv('POSTGRES_DB', 'sagedesk')}"
                       f" user={os.getenv('POSTGRES_USER', 'sagedesk')} password={os.environ['POSTGRES_PASSWORD']}"
                       f" port={os.getenv('POSTGRES_PORT', '5432')}", autocommit=True)
conn.execute("CREATE EXTENSION IF NOT EXISTS vector")     # the type has to exist before psycopg is told about it
register_vector(conn)
conn.execute("DROP TABLE IF EXISTS concept_chunks")
conn.execute(f"""CREATE TABLE concept_chunks (id bigserial PRIMARY KEY, tenant_id text NOT NULL,
                 source_file text NOT NULL, clause text NOT NULL, content text NOT NULL,
                 embedding vector({DIMS}) NOT NULL)""")    # tenant_id and clause are here from row one
for (tenant, file, clause, text), vector in zip(ROWS, embed([r[3] for r in ROWS], "RETRIEVAL_DOCUMENT")):
    conn.execute("INSERT INTO concept_chunks (tenant_id, source_file, clause, content, embedding)"
                 " VALUES (%s, %s, %s, %s, %s)", (tenant, file, clause, text, vector))

query = embed([QUESTION], "RETRIEVAL_QUERY")[0]
hits = conn.execute(
    "SELECT source_file, clause, content, 1 - (embedding <=> %s::vector) FROM concept_chunks"
    " WHERE tenant_id = %s ORDER BY embedding <=> %s::vector ASC LIMIT 3",
    (query, "claims", query)).fetchall()
print(f"=== SELECT ... ORDER BY embedding <=> query LIMIT 3   for {QUESTION!r}")
for file, clause, content, similarity in hits:
    print(f"  {similarity:.3f}  [{file} §{clause}]  {content}")
total = conn.execute("SELECT count(*) FROM concept_chunks").fetchone()[0]
total = conn.execute("SELECT count(*) FROM concept_chunks").fetchone()[0]
print(f"\n{total} rows in the table and 3 came back, the last of them scoring {hits[-1][3]:.3f}:")
print(f"  {hits[-1][2]}")
print("LIMIT always returns LIMIT: a vector search has no way to say 'nothing here'.")
