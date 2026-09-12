"""Run the meaning search and the keyword search, and fuse them by rank -- their scores do not compare.

Real Postgres (pgvector `<=>` and `tsvector`) and real embeddings, two questions that pull opposite ways.
    docker compose -f ../demo/docker-compose.yml up -d
    uv run --project ../demo python 12_hybrid_search_and_rrf.py
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
client, DIMS, RRF_K = genai.Client(), int(os.getenv("EMBEDDING_DIMS", "768")), 60
EMBED = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
ROWS = ["A pending mid-term adjustment blocks the quote; the portal shows NW-4471.",
        "If the broker portal shows an error, ask what the message says and retry after a minute.",
        "Portal error messages and what they mean are listed in the monthly broker bulletin index.",
        "Escape of water from a neighbouring flat is covered. Excess GBP 350.",
        "Broker commission is settled monthly in arrears."]
ANY_TERM = "replace(websearch_to_tsquery('english', %s)::text, '&', '|')::tsquery"   # demo/retrieval.py

def embed(texts, task):
    config = types.EmbedContentConfig(task_type=task, output_dimensionality=DIMS)
    return [e.values for e in client.models.embed_content(model=EMBED, contents=texts, config=config).embeddings]

conn = psycopg.connect(f"host={os.getenv('POSTGRES_HOST', 'localhost')} dbname={os.getenv('POSTGRES_DB', 'sagedesk')}"
                       f" user={os.getenv('POSTGRES_USER', 'sagedesk')} password={os.environ['POSTGRES_PASSWORD']}"
                       f" port={os.getenv('POSTGRES_PORT', '5432')}", autocommit=True)
conn.execute("CREATE EXTENSION IF NOT EXISTS vector"); register_vector(conn)
conn.execute("DROP TABLE IF EXISTS concept_chunks")
conn.execute(f"""CREATE TABLE concept_chunks (id bigserial PRIMARY KEY, content text NOT NULL,
    embedding vector({DIMS}) NOT NULL,
    tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED)""")
for text, vector in zip(ROWS, embed(ROWS, "RETRIEVAL_DOCUMENT")):
    conn.execute("INSERT INTO concept_chunks (content, embedding) VALUES (%s, %s)", (text, vector))
for row_id, content in conn.execute("SELECT id, content FROM concept_chunks ORDER BY id").fetchall():
    print(f"  [{row_id}] {content}")

for question in ("what does error NW-4471 mean", "water coming through the ceiling from upstairs"):
    query = embed([question], "RETRIEVAL_QUERY")[0]
    ids = lambda rows: [r[0] for r in rows]
    vector_ranked = ids(conn.execute("SELECT id FROM concept_chunks ORDER BY embedding <=> %s::vector LIMIT 3", (query,)).fetchall())
    lexical_ranked = ids(conn.execute(f"SELECT id FROM concept_chunks WHERE tsv @@ {ANY_TERM}"
                                      f" ORDER BY ts_rank(tsv, {ANY_TERM}) DESC LIMIT 3", (question, question)).fetchall())
    all_terms = ids(conn.execute("SELECT id FROM concept_chunks WHERE tsv @@ websearch_to_tsquery('english', %s)", (question,)).fetchall())
    fused = {}
    for ranked in (vector_ranked, lexical_ranked):
        for rank, row_id in enumerate(ranked, start=1):
            fused[row_id] = fused.get(row_id, 0.0) + 1.0 / (RRF_K + rank)
    print(f"\n=== {question!r}")
    print(f"  vector <=>         {vector_ranked}")
    print(f"  lexical any-term   {lexical_ranked}")
    print(f"  lexical ALL-term   {all_terms}   <- websearch_to_tsquery ANDs every word of the question")
    print(f"  fused by RRF       {sorted(fused, key=fused.get, reverse=True)}"
          f"  scores {({k: round(v, 4) for k, v in sorted(fused.items(), key=lambda kv: -kv[1])})}")
