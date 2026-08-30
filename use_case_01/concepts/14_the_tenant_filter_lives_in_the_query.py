"""The tenant boundary belongs inside the SQL, because that is the place nobody can forget to call.

Real Postgres, two teams' rows in one table, the same search run three ways.
    docker compose -f ../demo/docker-compose.yml up -d
    uv run --project ../demo python 14_the_tenant_filter_lives_in_the_query.py
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
        ("broker_support", "21_portal_errors.md", "2", "A pending mid-term adjustment blocks the quote; the portal shows NW-4471."),
        ("broker_support", "22_commission.md", "6", "Broker commission is settled monthly in arrears.")]
QUESTION = "is water damage from the flat upstairs covered?"

def embed(texts, task):
    config = types.EmbedContentConfig(task_type=task, output_dimensionality=DIMS)
    return [e.values for e in client.models.embed_content(model=EMBED, contents=texts, config=config).embeddings]

conn = psycopg.connect(f"host={os.getenv('POSTGRES_HOST', 'localhost')} dbname={os.getenv('POSTGRES_DB', 'sagedesk')}"
                       f" user={os.getenv('POSTGRES_USER', 'sagedesk')} password={os.environ['POSTGRES_PASSWORD']}"
                       f" port={os.getenv('POSTGRES_PORT', '5432')}", autocommit=True)
conn.execute("CREATE EXTENSION IF NOT EXISTS vector"); register_vector(conn)
conn.execute("DROP TABLE IF EXISTS concept_chunks")
conn.execute(f"""CREATE TABLE concept_chunks (id bigserial PRIMARY KEY, tenant_id text NOT NULL,
    source_file text NOT NULL, clause text NOT NULL, content text NOT NULL, embedding vector({DIMS}) NOT NULL)""")
for (tenant, file, clause, text), vector in zip(ROWS, embed([r[3] for r in ROWS], "RETRIEVAL_DOCUMENT")):
    conn.execute("INSERT INTO concept_chunks (tenant_id, source_file, clause, content, embedding)"
                 " VALUES (%s, %s, %s, %s, %s)", (tenant, file, clause, text, vector))

query = embed([QUESTION], "RETRIEVAL_QUERY")[0]
SCOPED = ("SELECT tenant_id, source_file, clause FROM concept_chunks WHERE tenant_id = %s"
          " ORDER BY embedding <=> %s::vector LIMIT 2")
FORGOTTEN = ("SELECT tenant_id, source_file, clause FROM concept_chunks"        # no WHERE clause at all
             " ORDER BY embedding <=> %s::vector LIMIT 2")
print(f"question: {QUESTION!r}\n")
for tenant in ("claims", "broker_support"):
    hits = conn.execute(SCOPED, (tenant, query)).fetchall()
    print(f"  asked as {tenant:<15} -> {[f'{t}:{f} §{c}' for t, f, c in hits]}")
leak = conn.execute(FORGOTTEN, (query,)).fetchall()
print(f"  filter left to the caller -> {[f'{t}:{f} §{c}' for t, f, c in leak]}")
print(f"  cross-tenant rows in that result: {sum(1 for t, _, _ in leak if t != 'broker_support')}"
      " -- no error, no log line, just Claims' wording in a Broker Support session.")
