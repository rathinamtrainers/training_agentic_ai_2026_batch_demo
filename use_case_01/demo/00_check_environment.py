"""STEP 0 -- the proof that `uv sync` and `docker compose up -d` worked.

Run:  uv run python 00_check_environment.py

Every line here is something that ruins somebody's evening if it is wrong.
Nothing in this file calls a model, so nothing in it costs money.
"""

import importlib.metadata
import os
import sys

import config
import corpus
import db

config.banner("UC1 -- SageDesk Grounded Answer Service: environment check")

ok = True

# 1. The runtime, pinned for all sixteen weeks. uv installs it from
#    .python-version, so nobody has to own a pyenv.
version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
pinned = sys.version_info[:2] == (3, 13)
ok &= pinned
print(f"{'Python':<24} {version:<14} {'OK (pinned 3.13)' if pinned else 'NOT 3.13 -- see README'}")

# 2. The libraries, at the exact versions pyproject.toml pins.
for package in ("google-adk", "google-genai", "psycopg", "pgvector", "fastapi"):
    try:
        print(f"{package:<24} {importlib.metadata.version(package):<14} OK")
    except importlib.metadata.PackageNotFoundError:
        ok = False
        print(f"{package:<24} {'MISSING':<14} run `uv sync`")

# 3. Credentials. The key itself is never printed, not even partly.
print(f"{'GENAI_BACKEND':<24} {config.BACKEND:<14} "
      f"{'API key path (laptop)' if config.BACKEND == 'api_key' else 'Vertex / ADC path'}")
if config.BACKEND == "api_key":
    key = bool(os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"))
    ok &= key
    print(f"{'GOOGLE_API_KEY':<24} {'set' if key else 'MISSING':<14}"
          f" {'' if key else 'copy .env.example to .env and put a key in it'}")
else:
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    ok &= bool(project)
    print(f"{'GOOGLE_CLOUD_PROJECT':<24} {(project or 'MISSING'):<14}"
          f" {'' if project else 'set it, then `gcloud auth application-default login`'}")

print(f"{'chat model':<24} {config.CHAT_MODEL:<14} (pro tier: {config.PRO_MODEL})")
print(f"{'embedding model':<24} {config.EMBEDDING_MODEL:<14} {config.EMBEDDING_DIMS} dimensions")
print(f"{'reranker':<24} {'on' if config.RERANK else 'off':<14} RERANK in .env")

# 4. The corpus on disk, before anything is ingested.
total_docs = 0
for tenant in config.TENANTS:
    count = corpus.document_count(tenant)
    total_docs += count
    ok &= count > 0
    print(f"{'corpus/' + tenant:<24} {count:<14} documents")

# 5. Postgres, and whatever is already in it.
try:
    conn = db.connect()
    if conn.execute("SELECT to_regclass('public.chunks')").fetchone()[0]:
        for tenant, chunks, docs in db.counts_by_tenant(conn):
            print(f"{'chunks/' + tenant:<24} {chunks:<14} rows from {docs} documents")
    else:
        print(f"{'chunks table':<24} {'not there':<14} run `uv run python 01_ingest.py`")
    conn.close()
except SystemExit:
    # config.fail() already printed the sentence to act on.
    ok = False
except Exception as error:  # noqa: BLE001
    ok = False
    print(f"{'postgres':<24} {'FAILED':<14} {error}")

print()
print(f"{total_docs} Northwind documents across {len(config.TENANTS)} tenants.")
print("Environment looks usable." if ok
      else "SOMETHING ABOVE IS NOT READY -- fix it before the session.")
