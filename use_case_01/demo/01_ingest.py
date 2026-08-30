"""STEP 1 -- ingestion. Northwind's DocStore export becomes rows in Postgres.

Run:  uv run python 01_ingest.py
      uv run python 01_ingest.py --tenant claims        (one team only)

Forty documents -> clause-shaped chunks -> 768-number vectors -> rows that each
carry a tenant key and a clause reference. Watch the tenant_id column: it is
written on the very first insert, not added later when somebody notices that
Claims can read Underwriting's files.

This costs real embedding calls. It truncates the table first, so it is safe to
re-run in front of a room.
"""

import argparse
import pathlib
import time

import chunking
import config
import db
import embeddings

CORPUS = pathlib.Path(__file__).parent / "corpus"


def ingest_tenant(conn, tenant_id: str) -> int:
    rows = chunking.load_tenant(CORPUS, tenant_id)
    documents = len({name for name, _ in rows})
    print(f"\n[{tenant_id}] {documents} documents -> {len(rows)} chunks")

    texts = [
        # The heading is prepended to the embedded text on purpose. "4. Escape
        # of water" is often the most searchable sentence in the clause, and a
        # chunk that only says "cover applies where..." embeds badly.
        f"{chunk.heading}\n{chunk.content}"
        for _, chunk in rows
    ]
    started = time.monotonic()
    vectors = embeddings.embed_documents(texts)
    print(f"[{tenant_id}] embedded in {time.monotonic() - started:.1f}s"
          f" ({config.EMBEDDING_MODEL}, {config.EMBEDDING_DIMS} dims)")

    with conn.cursor() as cur:
        for index, ((source_file, chunk), vector) in enumerate(zip(rows, vectors)):
            cur.execute(
                "INSERT INTO chunks"
                " (tenant_id, source_file, clause, heading, chunk_index, content, embedding)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (tenant_id, source_file, chunk.clause, chunk.heading, index,
                 chunk.content, vector),
            )
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant", choices=config.TENANTS, help="ingest one team only")
    args = parser.parse_args()

    config.banner("STEP 1 -- INGESTION: Northwind's documents become searchable rows")
    config.check_credentials()

    print(f"[ingest] backend        : {config.BACKEND}")
    print(f"[ingest] chunking       : {chunking.describe()}")

    conn = db.connect()
    db.ensure_schema(conn)

    tenants = [args.tenant] if args.tenant else list(config.TENANTS)
    if args.tenant:
        conn.execute("DELETE FROM chunks WHERE tenant_id = %s", (args.tenant,))
    else:
        print("[ingest] TRUNCATE chunks -- this script is safe to re-run")
        conn.execute("TRUNCATE chunks")

    total = sum(ingest_tenant(conn, tenant) for tenant in tenants)

    config.banner("What is in the store now")
    print(f"{'tenant':<18}{'chunks':>8}{'documents':>12}")
    for tenant, chunks, documents in db.counts_by_tenant(conn):
        print(f"{tenant:<18}{chunks:>8}{documents:>12}")
    print(f"\n{total} chunks written. Every one of them carries a tenant_id and a clause.")

    sample = conn.execute(
        "SELECT tenant_id, source_file, clause, heading, left(content, 60)"
        "  FROM chunks ORDER BY id LIMIT 3"
    ).fetchall()
    print("\nThe first three rows, as the database holds them:")
    for row in sample:
        print(f"  {row[0]:<15} {row[1]:<34} §{row[2]:<5} {row[3][:28]:<30} {row[4]!r}...")

    conn.close()
    print("\nNext:  uv run python 02_hybrid_search.py")


if __name__ == "__main__":
    main()
