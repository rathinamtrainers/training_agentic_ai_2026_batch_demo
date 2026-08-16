"""One place where every setting comes from the environment.

Teaching point: nothing in this repository contains a key or a password. Every
one of them is read here, and a missing one stops the script and names the
variable, rather than producing a stack trace two hundred lines later in
somebody else's library.
"""

import os
import pathlib
import sys

from dotenv import load_dotenv

HERE = pathlib.Path(__file__).parent

# Read src/session_02/.env if it is there, so the room is set up once and every
# script in the run order picks it up. A real environment variable always beats
# the file -- override=False is the point, not an accident.
load_dotenv(HERE / ".env", override=False)

# Session 2 talks to the Gemini API with an API key: the shortest path from a
# clean laptop to a running agent. Vertex AI with Application Default
# Credentials is session 4's business, because session 4 is where we deploy.
# Set here so ADK does not quietly take the Vertex path on a machine that
# happens to export GOOGLE_CLOUD_PROJECT.
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "FALSE")


def fail(message: str) -> None:
    """Stop with a sentence a human can act on. Never a stack trace on stage."""
    print(f"\n[config] {message}\n")
    print("[config] See src/session_02/README.md, section 'Environment variables'.\n")
    sys.exit(1)


def required(name: str, why: str) -> str:
    value = os.environ.get(name)
    if not value:
        fail(f"MISSING ENVIRONMENT VARIABLE: {name}\n[config] It is needed for: {why}")
    return value


def optional(name: str, default: str) -> str:
    return os.environ.get(name) or default


# --- The model ---------------------------------------------------------------
# Pinned HERE and in README.md, never on a slide -- and this is exactly why.
# The course was written against gemini-2.5-flash, which was retired for new
# API keys mid-August 2026: it still appears in models.list(), but calling it
# returns 404 "no longer available to new users". A slide would still say the
# old name; a README and a config file get fixed in one commit.
#
# An exact version, not the gemini-flash-latest alias. The alias drifts, which
# would desync the recordings from the code, silently invalidate the hand-typed
# price list in usage.py, and make session 4's RAGAS score incomparable with
# session 3's. Same principle as the pinned pgvector image tag.
MODEL = optional("GEMINI_MODEL", "gemini-3.7-flash")
BACKEND = optional("MODEL_BACKEND", "gemini").lower()

OLLAMA_MODEL = optional("OLLAMA_MODEL", "llama3.1")
OLLAMA_API_BASE = optional("OLLAMA_API_BASE", "http://localhost:11434")


def model_for_adk():
    """What goes into Agent(model=...).

    For the hosted model that is just a string -- ADK builds the client itself
    from the environment. The Ollama branch is the stated fallback for the
    night the API is down; it is not taught tonight and it is not installed by
    default.
    """
    if BACKEND == "gemini":
        required(
            "GOOGLE_API_KEY",
            "the Gemini API key the agent authenticates with"
            " (get one at https://aistudio.google.com/apikey)",
        )
        return MODEL

    if BACKEND == "ollama":
        os.environ.setdefault("OLLAMA_API_BASE", OLLAMA_API_BASE)
        try:
            from google.adk.models.lite_llm import LiteLlm
        except ImportError:
            fail(
                "MODEL_BACKEND=ollama needs the LiteLLM extra, which is not"
                " installed by default:\n[config]     uv sync --extra ollama"
            )
        print(f"[config] FALLBACK PATH: local Ollama model {OLLAMA_MODEL!r} at {OLLAMA_API_BASE}")
        print("[config] This is not the hosted model. Answers and token counts will differ.")
        return LiteLlm(model=f"ollama_chat/{OLLAMA_MODEL}")

    fail(f"MODEL_BACKEND={BACKEND!r} is not a thing. Use 'gemini' or 'ollama'.")


def model_label() -> str:
    """What to print, so the room always knows which model answered."""
    return MODEL if BACKEND == "gemini" else f"ollama/{OLLAMA_MODEL}"


# --- Postgres (declared tonight, used from session 3) ------------------------
POSTGRES_HOST = optional("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(optional("POSTGRES_PORT", "5432"))


def banner(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)
