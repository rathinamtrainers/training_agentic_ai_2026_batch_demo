"""Hybrid search: the meaning librarian and the keyword librarian, merged, then
a reranker over the merged list.

Teaching point: vector search finds MEANING and is surprisingly bad at exact
strings like the broker portal error code NW-4471. Lexical search finds exact
words and ranks by how many of them a passage shares -- ask it about "water
coming through the ceiling from upstairs" and the only word it can match on is
"water", because it has never heard of a paraphrase. Run both, fuse the
ranks, and you rarely go home empty-handed.

The tenant filter lives INSIDE the SQL, not in application code above it,
because the safest place for a rule is the place nobody can forget to call.
Both halves of the hybrid carry it. Delete either `WHERE tenant_id = %s` and
04_cross_tenant.py fails immediately -- which is the point of having that
script.
"""

import config
import db
import embeddings
import rerank as rerank_module

RRF_K = 60  # reciprocal rank fusion constant; 60 is the value the papers use

# websearch_to_tsquery ANDs every word it is given, so a whole question --
# "what does error NW-4471 mean" -- parses to 'error' & 'nw-4471' & 'mean' and
# matches nothing at all. The lexical half then returns an empty list for every
# natural-language question, and hybrid search quietly degrades into vector
# search with a fusion step that has only one list to fuse. Rewriting the parsed
# query's & into | keeps everything websearch_to_tsquery is good at (phrases,
# quoting, the hyphen in NW-4471) and asks for ANY term instead of all of them;
# ts_rank still puts the passages that match more of them at the top.
ANY_TERM = "replace(websearch_to_tsquery('english', %s)::text, '&', '|')::tsquery"


def _row(row) -> dict:
    return {
        "id": row[0],
        "source_file": row[1],
        "clause": row[2],
        "heading": row[3],
        "chunk_index": row[4],
        "content": row[5],
        "score": row[6],
    }


def vector_hits(conn, tenant_id: str, question: str, limit: int) -> list[dict]:
    vector = embeddings.embed_query(question)
    rows = conn.execute(
        "SELECT id, source_file, clause, heading, chunk_index, content,"
        "       1 - (embedding <=> %s::vector) AS similarity"
        "  FROM chunks"
        " WHERE tenant_id = %s"                       # <-- the tenant boundary, in the query
        " ORDER BY embedding <=> %s::vector ASC LIMIT %s",
        (vector, tenant_id, vector, limit),
    ).fetchall()
    return [_row(r) for r in rows]


def lexical_hits(conn, tenant_id: str, question: str, limit: int) -> list[dict]:
    rows = conn.execute(
        "SELECT id, source_file, clause, heading, chunk_index, content,"
        f"       ts_rank(tsv, {ANY_TERM}) AS rank"
        "  FROM chunks"
        " WHERE tenant_id = %s"                       # <-- and again here
        f"   AND tsv @@ {ANY_TERM}"
        " ORDER BY rank DESC LIMIT %s",
        (question, tenant_id, question, limit),
    ).fetchall()
    return [_row(r) for r in rows]


def fuse(vector: list[dict], lexical: list[dict], limit: int) -> list[dict]:
    """Reciprocal rank fusion: a passage scores on WHERE it ranked in each list,
    so a cosine distance and a ts_rank -- two numbers on completely different
    scales -- can be added together honestly."""
    fused: dict[int, dict] = {}
    for hits, label in ((vector, "vector"), (lexical, "lexical")):
        for rank, hit in enumerate(hits, start=1):
            entry = fused.setdefault(hit["id"], {**hit, "fused": 0.0, "found_by": []})
            entry["fused"] += 1.0 / (RRF_K + rank)
            entry["found_by"].append(label)
    return sorted(fused.values(), key=lambda hit: hit["fused"], reverse=True)[:limit]


def search(tenant_id: str, question: str, limit: int | None = None,
           use_rerank: bool | None = None, verbose: bool = False) -> list[dict]:
    """The whole retrieval path, and the only way anything reads the store."""
    config.check_tenant(tenant_id)
    limit = limit or config.TOP_K
    use_rerank = config.RERANK if use_rerank is None else use_rerank

    conn = db.connect()
    try:
        candidates = config.RERANK_CANDIDATES if use_rerank else limit
        vector = vector_hits(conn, tenant_id, question, candidates)
        lexical = lexical_hits(conn, tenant_id, question, candidates)
    finally:
        conn.close()

    fused = fuse(vector, lexical, candidates)
    if verbose:
        print(f"  [retrieval] vector {len(vector)}, lexical {len(lexical)},"
              f" fused {len(fused)}, rerank={'on' if use_rerank else 'OFF'}")

    if not use_rerank:
        return fused[:limit]
    return rerank_module.rerank(question, fused, limit)


def citation_of(hit: dict) -> str:
    """The one place the citation format is defined. Everything else -- the
    agent instruction, the guardrail, the acceptance test -- refers here."""
    return f"[{hit['source_file']} §{hit['clause']}]"
