"""An unsourced answer is worse than no answer: parse every citation on the way out and OPEN it.

Three real Gemini answers, checked against the documents on disk rather than against the retriever.
    uv run --project ../demo python 16_a_citation_you_can_open.py
"""
import os
import re

from dotenv import load_dotenv
from google import genai

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "demo", ".env"))
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI",
                      "TRUE" if os.getenv("GENAI_BACKEND") == "vertex" else "FALSE")
MODEL, client = os.getenv("GEMINI_MODEL", "gemini-3.7-flash"), genai.Client()

DOCUMENTS = {("01_escape_of_water.md", "4"): "Escape of water from a neighbouring flat is covered. Excess GBP 350."}
REFUSAL = "That is not in the documents."                              # demo/guardrails.py, verbatim
CITATION = re.compile(r"[\[(]\s*(?P<file>[\w\-.]+\.md)\s*[,;]?\s*(?:§|clause\s+)\s*(?P<clause>[0-9.]+)\s*[\])]")
GROUNDED = ("Answer only from the passages. Cite every claim inline as [source_file §clause]."
            f' If the passages do not answer it, reply with exactly: "{REFUSAL}"')
QUESTION = "is water escaping from the flat above covered, and what is the excess?"

def check(answer):
    """demo/guardrails.check_answer: refusal passes, a resolvable citation passes, nothing else does."""
    if answer.strip() == REFUSAL:
        return "PASS (honest refusal)"
    found = [(m.group("file"), m.group("clause")) for m in CITATION.finditer(answer)]
    if not found:
        return "BLOCKED (no citation at all)"
    unresolved = [c for c in found if c not in DOCUMENTS]
    return f"BLOCKED (citation does not open: {unresolved})" if unresolved else f"PASS (opens: {found})"

RUNS = [("passages attached", GROUNDED + "\n\nPassages:\n[01_escape_of_water.md §4] "
         + DOCUMENTS[("01_escape_of_water.md", "4")]),
        ("no passages, grounded instruction", GROUNDED + "\n\nPassages:\n(none)"),
        ("no passages, no grounding rule", "You are an insurance expert. Answer in three sentences.")]

for label, system in RUNS:
    reply = client.models.generate_content(model=MODEL, contents=f"{system}\n\nQuestion: {QUESTION}")
    print(f"\n=== {label}")
    print("  " + reply.text.strip().replace("\n", "\n  "))
    print(f"  -> {check(reply.text)}")
    if DOCUMENTS.get(("01_escape_of_water.md", "4")) and "01_escape_of_water.md" in reply.text:
        print(f"  -> opened [01_escape_of_water.md §4]: {DOCUMENTS[('01_escape_of_water.md', '4')]}")
