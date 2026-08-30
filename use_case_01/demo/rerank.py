"""The reranker: a second, more expensive opinion about the passages.

Hybrid search is cheap and approximate. It ranks by how a question looks, not
by whether a passage answers it. The reranker reads the question and each
candidate passage together and scores them -- so a chunk that mentions "escape
of water" nine times but is about broker commission drops down the list.

Two teaching points sit in this file.

1. **It is a switch.** RERANK=off in .env turns it off, and the RAGAS
   before/after in eval/ is exactly that switch flipped. A quality claim you
   cannot turn off is not a measurement.

2. **Structured output.** We do not ask the model for prose and then parse it
   with a regular expression. We ask for JSON against a schema, and the API
   constrains the generation to that schema. That is the difference between a
   model that answers and a model that returns data.

The honest cost: one extra model call per question, and latency the room will
see. A cross-encoder reranker (a small local model) is the production answer;
an LLM reranker is the answer that needs no GPU on a laptop, and it is labelled
as that trade rather than sold as best practice.
"""

import json

from google.genai import types

import config
import embeddings

PROMPT = """You are ranking retrieved passages for relevance to one question.

Question: {question}

Passages:
{passages}

Score each passage from 0.0 (irrelevant) to 1.0 (directly answers the question).
Judge only whether the passage helps answer THIS question. Do not reward length,
confidence or repeated keywords. Return one object per passage id.
"""

SCHEMA = types.Schema(
    type=types.Type.ARRAY,
    items=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "id": types.Schema(type=types.Type.INTEGER),
            "score": types.Schema(type=types.Type.NUMBER),
        },
        required=["id", "score"],
    ),
)


def rerank(question: str, hits: list[dict], limit: int) -> list[dict]:
    """Return the `limit` most relevant hits, most relevant first.

    On any failure this returns the input order and SAYS SO on stdout. A silent
    fallback would let the room believe it is watching a reranked result when
    it is not.
    """
    if not hits:
        return []

    listing = "\n\n".join(
        f"[{hit['id']}] {hit['source_file']} clause {hit['clause']}\n{hit['content'][:1200]}"
        for hit in hits
    )

    try:
        response = embeddings.client().models.generate_content(
            model=config.CHAT_MODEL,
            contents=PROMPT.format(question=question, passages=listing),
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
                response_schema=SCHEMA,
            ),
        )
        scores = {int(row["id"]): float(row["score"]) for row in json.loads(response.text)}
    except Exception as error:  # noqa: BLE001 -- a demo must never die here
        print(f"  [rerank] FAILED, falling back to the un-reranked order: {error}")
        return hits[:limit]

    ranked = sorted(hits, key=lambda hit: scores.get(hit["id"], 0.0), reverse=True)
    for hit in ranked:
        hit["rerank_score"] = scores.get(hit["id"], 0.0)

    # The relevance floor. Retrieval cannot say "there is nothing here"; a
    # relevance score can. This is what lets the agent refuse instead of
    # politely inventing an answer out of the five least-irrelevant
    # paragraphs it happened to be handed.
    kept = [hit for hit in ranked if hit["rerank_score"] >= config.RERANK_FLOOR]
    dropped = len(ranked) - len(kept)
    if dropped:
        print(f"  [rerank] dropped {dropped} passage(s) below the relevance"
              f" floor of {config.RERANK_FLOOR}")
    return kept[:limit]
