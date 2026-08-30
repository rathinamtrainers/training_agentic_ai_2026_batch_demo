"""The model never sees your function. It sees the declaration ADK builds from your docstring.

Real google-adk 2.6.3 doing the derivation, the good description and the vague one side by side.
    uv run --project ../demo python 05_the_docstring_is_the_interface.py
"""
from google.adk.tools import FunctionTool

GOOD = """Search this team's own Northwind Assurance documents.

Use this for any question about policy wordings, cover, exclusions, claims handling,
underwriting appetite, broker terms, complaints procedure, error codes, timescales or
authority limits. Search first; never answer such a question from memory.

Args:
    question: The user's question, in their own words. Do not paraphrase it into keywords.

Returns:
    A dict with a "passages" list; each passage has "source_file" and "clause" (cite both
    as [source_file §clause]), "heading" and "content". An empty list means nothing matched.
"""
VAGUE = """Looks things up.

Args:
    question: a string.

Returns:
    A dict.
"""

def make_search_tool(doc: str):
    """A fresh function per agent, exactly as demo/agent.py's make_search_tool does it.
    ADK caches the declaration per function object, so the docstring is swapped on a new one."""
    def search_knowledge_base(question: str) -> dict:
        return {"passages": []}
    search_knowledge_base.__doc__ = doc
    return search_knowledge_base

for label, doc in (("GOOD", GOOD), ("VAGUE", VAGUE)):
    declaration = FunctionTool(make_search_tool(doc))._get_declaration()   # what is sent to Gemini
    print(f"\n=== {label} docstring -> declaration, {len(declaration.description)} chars of description")
    print(f"  name        : {declaration.name}")
    print(f"  parameters  : {declaration.parameters_json_schema}")
    print(f"  description : {declaration.description}")
