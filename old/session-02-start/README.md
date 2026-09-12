# session-02-start — the session 02 starting point

This is the scaffolding the class began session 02 from, as it stood on the
`session-02-start` branch. It is kept for reference; the current teaching path
is `use_case_01/`.

| entry | what it is |
|---|---|
| `order_agent/`, `order_tool.py`, `tool_variants.py` | the order-lookup agent, its tool, and the tool-description variants compared in the session |
| `run_turn.py`, `uc1_service.py` | the runner used to drive a turn, and the service wrapper around it |
| `config.py`, `usage.py`, `00_check_environment.py` | configuration, token-usage reporting, and the environment pre-flight check |
| `db/`, `docker-compose.yml` | local Postgres with pgvector, used by the retrieval work |
| `pyproject.toml`, `uv.lock`, `.python-version`, `.env.example` | the environment definition; the packages are restored with `uv sync` |
| `ACCEPTANCE.md` | what the session had to demonstrate before it counted as done |

These files were written to sit at the repository root. They now sit two levels
down, so paths inside them need adjusting before anything here will run.
