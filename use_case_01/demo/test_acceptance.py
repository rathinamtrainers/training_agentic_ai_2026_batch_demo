"""ACCEPTANCE.md, executed. Five criteria, in the same order and the same words.

Run:  uv run --extra dev pytest -v

If ACCEPTANCE.md and this file ever disagree, the markdown is wrong and this
one is right, because this one runs.

These tests call a real model and a real Postgres. There is no mock, because a
test that passes without touching either would prove nothing about the thing we
are about to deploy. They are slow and they cost a few cents; that is the honest
price of "done" meaning something.
"""

import asyncio
import os
import time

import pytest

import agent as agent_module
import config
import corpus
import guardrails
import retrieval

TENANT = "claims"
OTHER_TENANT = "broker_support"

ANSWERABLE = "Does our cover include an escape of water from a neighbouring flat?"
UNANSWERABLE = "What is Northwind's policy on keeping tropical fish in the office?"

_credentialled = bool(
    os.environ.get("GOOGLE_API_KEY")
    or os.environ.get("GEMINI_API_KEY")
    or os.environ.get("GOOGLE_CLOUD_PROJECT")
)

pytestmark = pytest.mark.skipif(
    not (_credentialled and os.environ.get("POSTGRES_PASSWORD")),
    reason="needs a Gemini key (or a GCP project) and a running Postgres:"
           " copy .env.example to .env, `docker compose up -d`, `python 01_ingest.py`",
)


@pytest.fixture(scope="module")
def answer():
    """One paid answer, reused by three criteria. Asking the same question four
    times would be four bills and four chances for non-determinism to make one
    of them flap."""
    return asyncio.run(agent_module.answer(ANSWERABLE, tenant_id=TENANT, verbose=False))


# --- AC1 ---------------------------------------------------------------------
def test_ac1_answers_a_corpus_question_with_at_least_one_citation(answer):
    """AC1 -- a question the documents can answer gets a real answer."""
    assert answer.blocked is None, f"a guardrail stopped it: {answer.blocked}"
    assert answer.text.strip(), "the service returned no answer at all"
    assert answer.citations, f"the answer carried no citation: {answer.text!r}"


# --- AC2 ---------------------------------------------------------------------
def test_ac2_every_citation_resolves_to_a_real_passage(answer):
    """AC2 -- a citation you cannot open is decoration.

    Resolved against the file on disk, not against the database, because a
    check that only asks the retriever is marking its own homework."""
    assert answer.citations, "there are no citations to resolve"
    for source_file, clause in answer.citations:
        assert source_file in corpus.files(TENANT), f"cited a file this team does not hold: {source_file}"
        passage = corpus.resolve(TENANT, source_file, clause)
        assert passage, f"citation {source_file} §{clause} resolves to nothing"
        assert passage.strip(), f"citation {source_file} §{clause} resolves to an empty passage"


# --- AC3 ---------------------------------------------------------------------
def test_ac3_a_tenant_never_receives_another_tenants_content():
    """AC3 -- tenant separation, from the first row we ever wrote.

    Checked at the retrieval layer rather than through the model, because the
    boundary must hold whatever the model decides to say.

    Deliberately un-reranked. With the reranker on, the relevance floor throws
    away everything Broker Support holds for a Claims question -- which is the
    right behaviour, and 04_cross_tenant.py demonstrates it -- but it leaves
    this criterion with an empty list and nothing to inspect. The un-reranked
    hybrid list is both the larger surface to look for a leak in and a list
    that is only ever empty when nothing has been ingested."""
    hits = retrieval.search(OTHER_TENANT, ANSWERABLE, use_rerank=False)
    assert hits, (
        f"retrieval returned nothing at all for {OTHER_TENANT} -- an empty"
        " retriever cannot demonstrate isolation. Has 01_ingest.py been run?"
    )
    claims_files = corpus.files(TENANT)
    leaked = [hit["source_file"] for hit in hits if hit["source_file"] in claims_files]
    assert not leaked, f"{OTHER_TENANT} was shown Claims documents: {leaked}"


# --- AC4 ---------------------------------------------------------------------
def test_ac4_says_it_is_not_in_the_documents_when_it_is_not():
    """AC4 -- the refusal, word for word. 'Something like' is not a criterion."""
    result = asyncio.run(agent_module.answer(UNANSWERABLE, tenant_id=TENANT, verbose=False))
    if result.blocked:
        pytest.fail(
            "the agent answered without grounding and the output guardrail caught"
            f" it: {result.blocked}\n"
            "Two likely causes, in order: (1) RERANK is off, or the reranker call"
            " failed and fell back to the un-reranked order -- either way the"
            " relevance floor never ran and the agent was handed five irrelevant"
            " passages to be disciplined about; (2) the instruction's rule 3 is"
            " not doing its job. Check the [rerank] lines in the output first."
        )
    assert guardrails.REFUSAL.lower().rstrip(".") in result.text.lower(), (
        f"expected {guardrails.REFUSAL!r}, got: {result.text!r}"
    )
    assert not result.citations, f"refused and cited something anyway: {result.citations}"


# --- AC5 ---------------------------------------------------------------------
def test_ac5_answers_within_the_agreed_latency_ceiling():
    """AC5 -- not a performance target. A 'the thing is alive' target, argued in
    ACCEPTANCE.md and settable with LATENCY_CEILING_SECONDS."""
    started = time.monotonic()
    asyncio.run(agent_module.answer(ANSWERABLE, tenant_id=TENANT, verbose=False))
    elapsed = time.monotonic() - started
    assert elapsed < config.LATENCY_CEILING_SECONDS, (
        f"took {elapsed:.1f}s against a ceiling of {config.LATENCY_CEILING_SECONDS}s"
    )
