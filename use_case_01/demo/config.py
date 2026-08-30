"""One place where every setting comes from the environment.

UC1 -- SageDesk's Grounded Answer Service, for Northwind Assurance.

Teaching point: nothing in this repository contains a key, a password or a
project id. Every one of them is read here, and a missing one stops the script
and names the variable, rather than producing a stack trace two hundred lines
later inside somebody else's library.

There are two credential paths and exactly one switch between them, because
this build has to run on a laptop AND deploy to Google Cloud:

    GENAI_BACKEND=api_key   a Gemini API key from AI Studio. The laptop path.
                            Everything except deployment and RAGAS runs on it.
    GENAI_BACKEND=vertex    Application Default Credentials against a Google
                            Cloud project. Required by deployment/ and by
                            eval/run_ragas.py, which use Google Cloud SDKs that
                            have no API-key path at all.
"""

import os
import pathlib
import sys

from dotenv import load_dotenv

HERE = pathlib.Path(__file__).parent

# Read demo/.env if it is there, so the room is set up once and every script in
# the run order picks it up. A real environment variable always beats the file
# -- override=False is the point, not an accident.
load_dotenv(HERE / ".env", override=False)


def fail(message: str) -> None:
    """Stop with a sentence a human can act on. Never a stack trace on stage."""
    print(f"\n[config] {message}\n")
    print("[config] See demo/README.md, section 'What you must set'.\n")
    sys.exit(1)


def required(name: str, why: str) -> str:
    value = os.environ.get(name)
    if not value:
        fail(f"MISSING ENVIRONMENT VARIABLE: {name}\n[config] It is needed for: {why}")
    return value


def optional(name: str, default: str) -> str:
    return os.environ.get(name) or default


# --- The credential switch ---------------------------------------------------
BACKEND = optional("GENAI_BACKEND", "api_key").lower()

if BACKEND not in ("api_key", "vertex"):
    fail(f"GENAI_BACKEND={BACKEND!r} is not a thing. Use 'api_key' or 'vertex'.")

if BACKEND == "api_key":
    # google-genai reads either name; ADK builds its OWN client from the
    # environment rather than taking ours, so the environment is where the
    # decision has to land. Setting the flag here means the demo does not
    # quietly take the Vertex path on a machine that exports
    # GOOGLE_CLOUD_PROJECT for unrelated reasons -- which surfaces as a 403 on
    # a project name nobody in the room recognises.
    if os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "FALSE"
else:
    # Both names on purpose: google-adk 2.6.3 warns that
    # GOOGLE_GENAI_USE_VERTEXAI is deprecated in favour of
    # GOOGLE_GENAI_USE_ENTERPRISE, and older code paths still read the old one.
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
    os.environ.setdefault("GOOGLE_GENAI_USE_ENTERPRISE", "TRUE")


def api_key() -> str:
    return required(
        "GOOGLE_API_KEY",
        "the Gemini API key the agent authenticates with"
        " (a free key from https://aistudio.google.com/apikey)",
    )


def project() -> str:
    return required("GOOGLE_CLOUD_PROJECT", "the Google Cloud project holding the Agent Platform")


LOCATION = optional("GOOGLE_CLOUD_LOCATION", "us-central1")


def genai_client_kwargs() -> dict:
    """What google.genai.Client() is built from, on whichever path is selected."""
    if BACKEND == "vertex":
        return {"vertexai": True, "project": project(), "location": LOCATION}
    return {"api_key": api_key()}


def check_credentials() -> None:
    """Called by scripts that are about to spend money, so a missing key fails
    on line one rather than after a two-minute ingest."""
    if BACKEND == "vertex":
        project()
    else:
        api_key()


# --- The models --------------------------------------------------------------
# Pinned HERE and in README.md, never on a slide, because names rot faster than
# a sixteen-week course runs. An exact id, not the `gemini-flash-latest` alias:
# an alias drifts, and a drifting model makes this week's RAGAS score
# incomparable with last week's.
#
# gemini-3.7-flash went GA on 2026-08-13 and is the id demonstrated live.
# gemini-2.5-flash GA still resolves -- the July 2026 retirement notice covered
# only the *preview* endpoints -- and is the documented fallback.
CHAT_MODEL = optional("GEMINI_MODEL", "gemini-3.7-flash")

# The second tier. UC3 builds the real router; here it is one env var and one
# command-line flag, which is enough for the room to see the same question
# answered by two tiers. Calling this a router would be a lie.
PRO_MODEL = optional("GEMINI_PRO_MODEL", "gemini-3.1-pro")

EMBEDDING_MODEL = optional("EMBEDDING_MODEL", "gemini-embedding-001")

# gemini-embedding-001 returns 3072 numbers by default. We ask for 768 so the
# pgvector column and its index stay small. Changing this means re-creating the
# table: the vector column's width is part of the schema.
EMBEDDING_DIMS = int(optional("EMBEDDING_DIMS", "768"))

# The embedding endpoint takes a batch, not a document. 32 is inside every
# published limit and keeps one failed request cheap to retry.
EMBED_BATCH = int(optional("EMBED_BATCH", "32"))


def model_label(tier: str = "flash") -> str:
    return PRO_MODEL if tier == "pro" else CHAT_MODEL


def model_for_tier(tier: str) -> str:
    if tier not in ("flash", "pro"):
        fail(f"--tier {tier!r} is not a tier. Use 'flash' or 'pro'.")
    return model_label(tier)


# --- Chunking ----------------------------------------------------------------
# Northwind's documents are clause-structured, so chunking follows the clauses
# rather than a character count. A clause longer than the ceiling is split, and
# every piece keeps the clause label -- because the label is what gets cited.
MAX_CHUNK_CHARS = int(optional("MAX_CHUNK_CHARS", "1800"))
CHUNK_OVERLAP_CHARS = int(optional("CHUNK_OVERLAP_CHARS", "200"))
# There is no exact Gemini tokenizer here. 1 token ~ 4 characters is an
# approximation, and 01_ingest.py prints it as one.
CHARS_PER_TOKEN = 4

# --- Retrieval ---------------------------------------------------------------
TOP_K = int(optional("TOP_K", "5"))
# How many fused candidates the reranker sees before it cuts back to TOP_K.
RERANK_CANDIDATES = int(optional("RERANK_CANDIDATES", "12"))
# The reranker is a switch on purpose: the before/after comparison is a demo,
# and a demo you cannot turn off is not a comparison.
RERANK = optional("RERANK", "on").lower() == "on"

# The relevance floor, and it matters more than it looks. A vector search ALWAYS
# returns its top five, however irrelevant they are -- so "the knowledge base has
# nothing on this" is not something retrieval can say on its own. The reranker
# scores relevance directly, so a floor turns that score into a refusal. Without
# it the agent is handed five unrelated passages and asked to be disciplined,
# which is a lot to ask of a model that wants to be helpful.
RERANK_FLOOR = float(optional("RERANK_FLOOR", "0.3"))

# --- Tenancy -----------------------------------------------------------------
# Northwind is multi-tenant to itself. These four teams hold documents the
# others must not see, and the key is a column from the first row inserted.
TENANTS = ("claims", "underwriting", "broker_support", "complaints")
TENANT_LABELS = {
    "claims": "Claims",
    "underwriting": "Underwriting",
    "broker_support": "Broker Support",
    "complaints": "Complaints",
}
DEFAULT_TENANT = optional("TENANT_ID", "claims")


def check_tenant(tenant_id: str) -> str:
    if tenant_id not in TENANTS:
        fail(f"tenant {tenant_id!r} is not one of Northwind's four: {', '.join(TENANTS)}")
    return tenant_id


# --- Acceptance --------------------------------------------------------------
# Session 2 wrote 10 seconds live and labelled it provisional. UC1's answer path
# is a retrieval call plus a rerank call plus a model call, so 10 seconds is a
# criterion that fails for being slow rather than for being wrong. 20 seconds,
# argued in ACCEPTANCE.md, and still a "the thing is alive" number rather than
# a service level anybody has signed.
LATENCY_CEILING_SECONDS = float(optional("LATENCY_CEILING_SECONDS", "20"))

# --- The store ---------------------------------------------------------------


def db_settings() -> dict:
    return {
        "host": optional("POSTGRES_HOST", "localhost"),
        "port": int(optional("POSTGRES_PORT", "5432")),
        "dbname": optional("POSTGRES_DB", "sagedesk"),
        "user": optional("POSTGRES_USER", "sagedesk"),
        "password": required(
            "POSTGRES_PASSWORD",
            "the Postgres password -- the same one docker-compose.yml starts the"
            " container with. Copy .env.example to .env and set it.",
        ),
    }


# --- Deployment (needs a Google Cloud project) -------------------------------


def staging_bucket() -> str:
    return required("STAGING_BUCKET", "the GCS bucket Agent Runtime stages the deployment through")


def agent_engine_id() -> str:
    return required(
        "AGENT_ENGINE_ID",
        "the deployed agent's resource name (run deployment/deploy.py first)",
    )


def banner(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)
