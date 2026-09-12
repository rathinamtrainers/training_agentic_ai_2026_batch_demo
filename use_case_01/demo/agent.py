"""The agent: one model, one tool, and the tool is the retrieval we just built.

Teaching point: almost nothing new is written here. `search_knowledge_base` is
`retrieval.search` with a docstring on it. That docstring is the whole interface
the model gets -- it is not a comment, it is the API description the model reads
when it decides whether to call the tool at all. Write it for the model.

Notice what we do NOT do. We never say "first search, then answer". We describe
the tool and let the agent choose. Run 03_ask.py with TOOL_DESCRIPTION=vague and
watch the choosing stop.

The tenant boundary is bound when the agent is BUILT, not passed in by the caller
at question time. A caller cannot ask for another team's documents because there
is no argument in which to ask.
"""

import dataclasses

from google.adk.agents import Agent

import config
import corpus
import guardrails
import retrieval
import turn as turn_module

# --- The instruction ---------------------------------------------------------
# Northwind's rule, in four lines: answer from the passages, cite the clause,
# say so when you cannot, be brief. Rule 3 is the one that stops the invention,
# and it names the sentence rather than describing it, because the acceptance
# test asserts that sentence character for character.
#
# NUDGE is separated out for one reason. It is the sentence that tells the agent
# to search, and TOOL_DESCRIPTION=vague removes it along with the docstring. If
# it stayed, the instruction would be what makes the agent call the tool and
# ruining the description would prove nothing. Removing both is also the honest
# lesson: in a real agent with nine tools, no instruction can name them all, so
# the description has to carry the decision on its own.
NUDGE = "Use the search_knowledge_base tool to find relevant passages before answering."

INSTRUCTION_TEMPLATE = f"""You are SageDesk, answering questions for one team inside Northwind
Assurance, a UK general insurer, from that team's own documents only.

{{nudge}}

Rules you must follow:
1. Answer ONLY from the passages the tool returns. Never use general knowledge
   about insurance, and never use another team's material.
2. Cite the clause behind every claim, inline, in exactly this form:
   [source_file §clause] -- for example [01_escape_of_water.md §4]. Use the
   source_file and clause values from the tool result, unchanged.
3. If the tool returns nothing relevant, reply with exactly this sentence and
   nothing else: "{guardrails.REFUSAL}" Do not add a citation to it, do not
   soften it, and do not guess.
4. Be brief. Two or three sentences and a citation is usually the whole answer.
"""

# The tool description, and the deliberately bad version of it. Swapping these
# is a demonstration: same model, same corpus, same question, and the agent
# stops calling the tool, because nobody told it what the tool is for.
GOOD_DESCRIPTION = """Search this team's own Northwind Assurance documents.

Use this for any question about policy wordings, cover, exclusions, claims
handling, underwriting appetite, broker terms, complaints procedure, error
codes, timescales or authority limits. Search first; never answer such a
question from memory.

Args:
    question: The user's question, in their own words. Do not paraphrase it
        into keywords -- a meaning search and a keyword search are both run
        over it.

Returns:
    A dict with a "passages" list. Each passage has "source_file" and "clause"
    (cite both, as [source_file §clause]), "heading" and "content". An empty
    list means these documents have nothing on the question.
"""

VAGUE_DESCRIPTION = """Looks things up.

Args:
    question: a string.

Returns:
    A dict.
"""


def vague_mode() -> bool:
    return config.optional("TOOL_DESCRIPTION", "good").lower() == "vague"


def instruction() -> str:
    """The instruction the agent runs with. In vague mode the sentence telling
    it to search is removed, along with the tool's docstring."""
    return INSTRUCTION_TEMPLATE.format(nudge="" if vague_mode() else NUDGE)


@dataclasses.dataclass
class Answer:
    text: str
    citations: list[tuple[str, str]]
    tenant_id: str
    model: str
    tool_calls: int = 0
    prompt_tokens: int = 0
    output_tokens: int = 0
    elapsed_seconds: float = 0.0
    blocked: str | None = None


def make_search_tool(tenant_id: str):
    """Build the tool for ONE tenant. The tenant id is captured in the closure,
    which is why no prompt can talk the agent into another team's documents."""

    def search_knowledge_base(question: str) -> dict:
        hits = retrieval.search(tenant_id, question, verbose=True)
        return {
            "passages": [
                {
                    "source_file": hit["source_file"],
                    "clause": hit["clause"],
                    "heading": hit["heading"],
                    "content": hit["content"],
                }
                for hit in hits
            ]
        }

    # ADK reads the docstring to build the function declaration it sends to the
    # model. Setting it here rather than writing it above is what lets the
    # TOOL_DESCRIPTION switch exist at all.
    vague = vague_mode()
    search_knowledge_base.__doc__ = VAGUE_DESCRIPTION if vague else GOOD_DESCRIPTION
    if vague:
        print("  [tool] DELIBERATELY VAGUE description (TOOL_DESCRIPTION=vague), and")
        print("  [tool] the instruction no longer says 'use the tool' either -- so the")
        print("  [tool] description is the only thing arguing for the tool now.")
    return search_knowledge_base


def build_agent(tenant_id: str | None = None, tier: str = "flash") -> Agent:
    tenant_id = config.check_tenant(tenant_id or config.DEFAULT_TENANT)
    return Agent(
        name="grounded_answer_service",
        model=config.model_for_tier(tier),
        description=(
            "Answers questions from one Northwind Assurance team's own documents,"
            " with clause-level citations."
        ),
        instruction=instruction(),
        tools=[make_search_tool(tenant_id)],
    )


# The module-level name `adk deploy` and Agent Runtime look for by convention.
root_agent = build_agent()


async def answer(question: str, tenant_id: str | None = None, tier: str = "flash",
                 verbose: bool = True) -> Answer:
    """One question in, one grounded answer out, with a guardrail on each side.

    That shape -- check, model, check -- is the thing to remember, even though
    the checks themselves are thin.
    """
    tenant_id = config.check_tenant(tenant_id or config.DEFAULT_TENANT)
    model = config.model_for_tier(tier)

    try:
        question = guardrails.check_question(question)          # <-- guardrail IN
    except guardrails.Blocked as blocked:
        return Answer(text="", citations=[], tenant_id=tenant_id, model=model,
                      blocked=f"input guardrail: {blocked}")

    result = await turn_module.run(build_agent(tenant_id, tier), question, verbose=verbose)

    out = Answer(
        text=result.text,
        citations=guardrails.citations_in(result.text),
        tenant_id=tenant_id,
        model=model,
        tool_calls=len(result.tool_calls),
        prompt_tokens=result.prompt_tokens,
        output_tokens=result.output_tokens,
        elapsed_seconds=result.elapsed_seconds,
    )

    try:
        out.text = guardrails.check_answer(result.text, tenant_id)   # <-- guardrail OUT
    except guardrails.Blocked as blocked:
        out.blocked = f"output guardrail: {blocked}"
    return out


def open_citation(tenant_id: str, source_file: str, clause: str) -> str | None:
    """What the trainer does live: take the citation off the screen and open the
    clause it points at. A citation nobody checks is decoration."""
    return corpus.resolve(tenant_id, source_file, clause)
