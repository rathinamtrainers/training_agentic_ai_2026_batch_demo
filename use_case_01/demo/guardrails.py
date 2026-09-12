"""Two guardrails: one on the way in, one on the way out.

This is THIN and it is labelled thin. Two functions is not a policy engine, a
classifier or a threat model -- it is the smallest honest thing that shows
WHERE guardrails live in the shape of the system. The hard version (Presidio,
jailbreak detection, action-level permissions, the OWASP agentic list) is UC3's
material. Here the point is that there is a place for it, and that place is not
"inside the prompt, and hope".

The third guardrail -- tenant isolation -- is deliberately NOT here. It lives in
the SQL (`retrieval.py`) and in the closure the tool is built from
(`agent.py`), because the safest place for a rule is the place nobody can
forget to call.

The output guardrail is the one that earns its keep in UC1. Northwind's
constraint is that an unsourced answer is worse than no answer, so an answer
that neither carries a resolvable clause citation nor admits it does not know
never reaches a user.
"""

import re

import corpus

MAX_QUESTION_CHARS = 500

# The exact sentence the service says when the documents do not contain the
# answer. Session 2 wrote this wording live, and the acceptance test asserts it
# character for character -- a criterion phrased as "says something like" is not
# a criterion.
REFUSAL = "That is not in the documents."

# Not a jailbreak detector. A tripwire for the phrasings that turn up in every
# demonstration, so the room sees the check happen rather than hears about it.
INJECTION_MARKERS = (
    "ignore previous",
    "ignore all previous",
    "disregard your instructions",
    "reveal your system prompt",
    "show me your instructions",
    "you are now",
)

# [01_escape_of_water.md §4]  or  [01_escape_of_water.md §4.2]
#
# Deliberately a little forgiving: round brackets, a comma, or the word "clause"
# instead of the section sign all still parse. The instruction asks for one exact
# form, and a model will occasionally produce a near miss -- failing a correct,
# resolvable citation over a bracket would teach the room the wrong lesson about
# where the risk in this system actually is.
CITATION = re.compile(
    r"[\[(]\s*(?P<file>[\w\-.]+\.md)\s*[,;]?\s*(?:§|clause\s+)\s*"
    r"(?P<clause>[0-9]+(?:\.[0-9]+)*)\s*[\])]"
)


class Blocked(Exception):
    """Raised when a guardrail stops a question or an answer."""


def check_question(question: str) -> str:
    """INPUT guardrail. Runs before the model sees a single token."""
    text = (question or "").strip()
    if not text:
        raise Blocked("empty question")
    if len(text) > MAX_QUESTION_CHARS:
        raise Blocked(
            f"question is {len(text)} characters, limit is {MAX_QUESTION_CHARS}"
            " -- a question that long here is usually a paste, not a question"
        )
    lowered = text.lower()
    for marker in INJECTION_MARKERS:
        if marker in lowered:
            raise Blocked(f"question contains the instruction-override phrase {marker!r}")
    return text


def citations_in(answer: str) -> list[tuple[str, str]]:
    """Every (source_file, clause) the answer claims to be quoting."""
    return [(m.group("file"), m.group("clause")) for m in CITATION.finditer(answer or "")]


def check_answer(answer: str, tenant_id: str) -> str:
    """OUTPUT guardrail. An answer must either carry a citation that resolves to
    a real clause of a real document belonging to THIS tenant, or admit that it
    does not know. A confident answer with no citation is the exact failure this
    whole use case exists to make visible."""
    text = (answer or "").strip()
    if not text:
        raise Blocked("the agent returned nothing")

    cited = citations_in(text)
    if cited:
        unresolvable = [
            f"{file} §{clause}"
            for file, clause in cited
            if corpus.resolve(tenant_id, file, clause) is None
        ]
        if unresolvable:
            raise Blocked(
                "the answer cites clauses that do not exist in this tenant's"
                f" documents: {', '.join(unresolvable)} -- an invented citation"
                " is worse than no answer"
            )
        return text

    if REFUSAL.lower().rstrip(".") in text.lower():
        return text

    raise Blocked(
        "the answer carries no citation and does not admit it does not know"
        " -- this is the ungrounded-answer case"
    )
