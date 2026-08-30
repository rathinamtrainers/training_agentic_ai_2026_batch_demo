"""STEP 2 -- retrieval, with the three lists side by side.

Run:  uv run python 02_hybrid_search.py
      uv run python 02_hybrid_search.py --tenant broker_support "NW-4471"

Four lists for one question: what the vector search found, what the keyword
search found, what reciprocal rank fusion made of the two, and what the
reranker did to that. No model writes an answer here -- this step is only about
what the agent will be given.

Two questions are run by default, and they make opposite points:

  * a paraphrase ("water coming through the ceiling from the flat upstairs")
    that the keyword search struggles with and the vector search walks;
  * an exact string (the broker portal error code) that the vector search
    ranks vaguely and the keyword search nails.

That is the entire argument for running both.
"""

import argparse

import config
import db
import rerank
import retrieval

DEFAULTS = [
    ("claims", "water is coming through the ceiling from the flat upstairs"),
    ("broker_support", "what does error NW-4471 mean"),
]


def show(label: str, hits: list[dict]) -> None:
    print(f"\n  {label}")
    if not hits:
        print("    (nothing)")
        return
    for rank, hit in enumerate(hits[:5], start=1):
        score = hit.get("rerank_score", hit.get("fused", hit.get("score", 0.0)))
        print(f"    {rank}. {hit['source_file']:<36} §{hit['clause']:<5}"
              f" {hit['heading'][:30]:<32} {score:.4f}")


def run(tenant: str, question: str) -> None:
    config.banner(f"[{config.TENANT_LABELS[tenant]}] {question}")

    conn = db.connect()
    try:
        vector = retrieval.vector_hits(conn, tenant, question, config.RERANK_CANDIDATES)
        lexical = retrieval.lexical_hits(conn, tenant, question, config.RERANK_CANDIDATES)
    finally:
        conn.close()

    show("VECTOR -- finds meaning, is bad at exact strings", vector)
    show("LEXICAL -- finds exact words, is blind to paraphrase", lexical)

    fused = retrieval.fuse(vector, lexical, config.RERANK_CANDIDATES)
    show("FUSED (reciprocal rank fusion) -- what the agent would get without a reranker", fused)

    if config.RERANK:
        show("RERANKED -- a model read the question and each passage together",
             rerank.rerank(question, list(fused), config.TOP_K))
    else:
        print("\n  RERANKER OFF (RERANK=off). Turn it on in .env to see the fourth list.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant", choices=config.TENANTS)
    parser.add_argument("question", nargs="*")
    args = parser.parse_args()

    config.check_credentials()

    if args.question:
        run(args.tenant or config.DEFAULT_TENANT, " ".join(args.question))
    else:
        for tenant, question in DEFAULTS:
            run(tenant, question)

    print("\nNext:  uv run python 03_ask.py")


if __name__ == "__main__":
    main()
