"""UC1 -- the Grounded Answer Service. The shape of it, before it exists.

Nothing in here works, and that is the point of tonight. This module is the
interface the five acceptance criteria are written against, so the tests are
real tests of a real thing rather than a wish list in a comment.

Two rules this file obeys, both of which matter on stage:

  1. It imports NOTHING. No ADK, no database driver, no config. `pytest` must
     produce five assertion failures and not one import error, because a stack
     trace in front of a room teaches "the tests are broken", which is the
     opposite of the lesson.

  2. The stubs RETURN empty results rather than raising NotImplementedError.
     A raise is an error; an empty result is a failed assertion with a sentence
     attached. Red should read like a specification, not like a crash.

Session 3 builds `search`. Session 4 builds `answer` and `resolve_citation`,
and these five go green.
"""

from dataclasses import dataclass, field

# Provisional, named as provisional (see ACCEPTANCE.md). A "the thing is alive"
# ceiling, not a service level anybody has agreed to.
LATENCY_CEILING_SECONDS = 10.0

# The exact sentence the service must say when the documents do not contain the
# answer. A confident wrong answer with a fake citation is far worse than this.
REFUSAL = "That is not in the documents."

# Multi-tenancy from row one, not retrofitted. Session 3 writes the first row
# and it carries a tenant key.
TENANTS = ("tenant_a", "tenant_b")


@dataclass
class Passage:
    """One retrieved chunk of one document, and who it belongs to."""

    tenant_id: str
    source_document: str
    text: str


@dataclass
class Answer:
    """What the service gives back. Citations are source document names."""

    text: str = ""
    citations: list[str] = field(default_factory=list)
    latency_seconds: float | None = None


def search(tenant_id: str, question: str) -> list[Passage]:
    """Retrieve passages for this tenant only.

    SESSION 3 BUILDS THIS: loaders, chunking, embeddings, pgvector, hybrid
    search. Tonight it finds nothing, because there is nothing to find.
    """
    return []


def answer(question: str, tenant_id: str) -> Answer:
    """Answer a question from that tenant's documents, with citations.

    SESSION 4 BUILDS THIS: grounded generation, citation, refusal, and the
    retrieval above wrapped as the tool the agent chooses to call.
    """
    return Answer()


def resolve_citation(citation: str, tenant_id: str) -> Passage | None:
    """Turn a citation back into the passage it came from.

    SESSION 4 BUILDS THIS. A citation you cannot open is decoration.
    """
    return None
