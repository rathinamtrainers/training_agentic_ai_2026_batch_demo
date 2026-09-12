"""DEPLOY -- the agent leaves this laptop and runs on Google Cloud Agent Platform.

Run FROM demo/:   uv run python deployment/deploy.py

This packages the agent and the modules it stands on, ships them to **Agent
Runtime** (the service formerly called Agent Engine, on the platform formerly
called Vertex AI, in a Python namespace that still says `vertexai`), and prints
the resource name. Put that in `AGENT_ENGINE_ID` in `.env` and then run
`deployment/call_remote.py`.

It takes several minutes, because it builds a container. That is the moment for
the architecture recap, or for the pre-recorded deploy.

**This needs a Google Cloud project, billing, and a GCS bucket.** It is the one
part of UC1 that a laptop and a free API key cannot do.

Three things worth saying out loud while it builds:

1. The database credentials go up as environment variables on the deployed
   agent. That is fine for a walking skeleton and wrong for production, where
   they belong in Secret Manager. It is on the debt list, said rather than hidden.
2. `agent.answer()`'s guardrails do NOT travel. Agent Runtime runs the ADK
   agent, not our Python wrapper, so the deployed service has the instruction
   and the SQL tenant filter but not the two checks around them. Putting them
   where they survive deployment -- ADK callbacks -- is later material. Do not
   let the room believe the deployed thing is guarded.
3. The deployed agent is bound to ONE tenant, the one in `TENANT_ID`, because
   the tenant is captured in the tool's closure. Four tenants means four
   deployments or a per-request identity, and choosing between those is a real
   architectural decision rather than a detail.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import config  # noqa: E402

# Everything agent.py imports, plus the corpus the citation check reads.
# There is no package here, so the list is explicit -- tedious, and completely
# legible, which is the right trade for something a room has to follow.
EXTRA_PACKAGES = [
    "agent.py",
    "chunking.py",
    "config.py",
    "corpus.py",
    "db.py",
    "embeddings.py",
    "guardrails.py",
    "rerank.py",
    "retrieval.py",
    "turn.py",
    "usage.py",
    "corpus",
]

# Pinned to match pyproject.toml. The deployed container resolves these itself,
# so a floating version here would mean the deployed agent differs from the one
# that was rehearsed.
REQUIREMENTS = [
    "google-adk==2.6.3",
    "google-genai==2.17.0",
    "google-cloud-aiplatform[adk,agent_engines]==1.163.0",
    "psycopg[binary]==3.3.4",
    "pgvector==0.5.0",
    "python-dotenv==1.2.2",
]

LOOPBACK = ("localhost", "127.0.0.1", "::1", "0.0.0.0", "host.docker.internal")


def main() -> None:
    config.banner("DEPLOY -- SageDesk UC1 to Google Cloud Agent Platform (Agent Runtime)")

    here = pathlib.Path.cwd()
    missing = [name for name in EXTRA_PACKAGES if not (here / name).exists()]
    if missing:
        print(f"[deploy] run this from demo/, not from {here}")
        print(f"[deploy] cannot see: {', '.join(missing)}")
        sys.exit(1)

    if config.BACKEND != "vertex":
        print("[deploy] GENAI_BACKEND is 'api_key'. Agent Runtime is a Google Cloud service.")
        print("[deploy] Set GENAI_BACKEND=vertex and GOOGLE_CLOUD_PROJECT in .env, then")
        print("[deploy]   gcloud auth application-default login")
        sys.exit(1)

    db = config.db_settings()
    if db["host"] in LOOPBACK:
        # The failure this prevents: the deploy SUCCEEDS, and then every query
        # against the deployed agent fails, because "localhost" inside Google's
        # network is Google's network. It costs ten minutes of container build
        # to discover that the slow way, in front of a room.
        print(f"[deploy] POSTGRES_HOST is {db['host']!r}, which is this laptop.")
        print("[deploy] The deployed agent runs inside Google's network and cannot reach it.")
        print("[deploy] Point POSTGRES_HOST at a Cloud SQL instance (or any reachable")
        print("[deploy] Postgres with pgvector), re-run 01_ingest.py against it, then deploy.")
        sys.exit(1)

    import vertexai
    from vertexai import agent_engines

    bucket = config.staging_bucket()
    if not bucket.startswith("gs://"):
        bucket = f"gs://{bucket}"

    project = config.project()
    print(f"[deploy] project        : {project}")
    print(f"[deploy] location       : {config.LOCATION}")
    print(f"[deploy] staging bucket : {bucket}")
    print(f"[deploy] model          : {config.CHAT_MODEL}")
    print(f"[deploy] tenant         : {config.DEFAULT_TENANT}  (bound into the tool)")
    print(f"[deploy] database       : {db['host']}:{db['port']}/{db['dbname']}")

    vertexai.init(project=project, location=config.LOCATION, staging_bucket=bucket)

    import agent  # noqa: E402  -- imported after init so it builds against the right project

    app = agent_engines.AdkApp(
        agent=agent.root_agent,
        enable_tracing=True,   # traces on the deployed agent depend on this line
    )

    env_vars = {
        "GENAI_BACKEND": "vertex",
        "GOOGLE_CLOUD_PROJECT": project,
        "GOOGLE_CLOUD_LOCATION": config.LOCATION,
        "GEMINI_MODEL": config.CHAT_MODEL,
        "EMBEDDING_MODEL": config.EMBEDDING_MODEL,
        "EMBEDDING_DIMS": str(config.EMBEDDING_DIMS),
        "TENANT_ID": config.DEFAULT_TENANT,
        "RERANK": "on" if config.RERANK else "off",
        "POSTGRES_HOST": db["host"],
        "POSTGRES_PORT": str(db["port"]),
        "POSTGRES_DB": db["dbname"],
        "POSTGRES_USER": db["user"],
        # Debt: Secret Manager. Said out loud, not hidden.
        "POSTGRES_PASSWORD": db["password"],
        # OpenTelemetry gen_ai metrics from the deployed agent (ADK 2.6+).
        "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY": "true",
    }

    print("\n[deploy] building and uploading -- this takes several minutes.\n")

    remote = agent_engines.create(
        app,
        display_name=f"SageDesk UC1 Grounded Answer Service ({config.DEFAULT_TENANT})",
        description="Answers questions from one Northwind team's documents, with clause citations.",
        requirements=REQUIREMENTS,
        extra_packages=EXTRA_PACKAGES,
        env_vars=env_vars,
    )

    print("\n[deploy] DEPLOYED.")
    print(f"[deploy] resource name: {remote.resource_name}")
    print("\n[deploy] Put this line in demo/.env, then run:")
    print(f"           AGENT_ENGINE_ID={remote.resource_name}")
    print("           uv run python deployment/call_remote.py")


if __name__ == "__main__":
    main()
