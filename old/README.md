# old — earlier material, kept for reference

This folder holds the work that came before `use_case_01/`, which is now the
main focus of the training. Nothing here is part of the current teaching path.
It is kept so earlier sessions stay reproducible and so the code can be looked
up when a question comes back to it.

What is in here:

| entry | what it was |
|---|---|
| `adk_01_core/`, `adk_02_tools/`, `adk_demo_1/` | the first ADK demos: core building blocks, then tools |
| `adk_concepts.md` | the ADK concepts reference written for those demos |
| `order_agent/`, `order_tool.py`, `tool_variants.py` | session 02 scaffolding: an order-lookup agent and tool variants |
| `config.py`, `usage.py`, `run_turn.py`, `uc1_service.py`, `00_check_environment.py` | the supporting runner and config code for that scaffolding |
| `db/`, `docker-compose.yml` | the local Postgres + pgvector setup used by it |
| `pyproject.toml`, `uv.lock`, `requirements.txt`, `.python-version`, `.env.example` | the environment definitions for the above |
| `ACCEPTANCE.md` | the acceptance notes for the session 02 scaffolding |

These files were moved here wholesale. Paths inside them still assume they sit
at the repository root, so run them from this folder, and expect to fix a path
or two before anything here works again.
