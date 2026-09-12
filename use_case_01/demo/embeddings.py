"""Text in, a list of numbers out. That is the whole of the embeddings idea.

Real Gemini calls on whichever credential path config selected. There is no
offline fallback here: if the call fails the demo says so rather than inventing
a vector. A retrieval system quietly running on made-up numbers is the one
failure a room would never spot.
"""

from google import genai
from google.genai import types

import config

_client = None


def client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(**config.genai_client_kwargs())
    return _client


def embed(texts: list[str], task_type: str) -> list[list[float]]:
    """task_type tells the model whether this text is a document being stored or
    a question being asked. The same sentence embeds differently depending on
    which, and using the wrong one quietly costs you retrieval quality -- no
    error, just worse answers."""
    out: list[list[float]] = []
    for start in range(0, len(texts), config.EMBED_BATCH):
        batch = texts[start:start + config.EMBED_BATCH]
        response = client().models.embed_content(
            model=config.EMBEDDING_MODEL,
            contents=batch,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=config.EMBEDDING_DIMS,
            ),
        )
        out.extend(e.values for e in response.embeddings)
    return out


def embed_documents(texts: list[str]) -> list[list[float]]:
    return embed(texts, "RETRIEVAL_DOCUMENT")


def embed_query(text: str) -> list[float]:
    return embed([text], "RETRIEVAL_QUERY")[0]
