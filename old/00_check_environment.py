"""DEMO 1 (part 1) -- the proof that `uv sync` and `docker compose up` worked.

Run:  uv run python 00_check_environment.py

Six lines of output, and every one of them is something that breaks somebody's
evening if it is wrong. Nothing here calls the model or costs money.
"""

import importlib.metadata
import os
import socket
import sys

import config

config.banner("SESSION 2 -- environment check")

# 1. The runtime. Pinned for all sixteen weeks; uv installs it from
#    .python-version, so nobody has to own a pyenv.
version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
pinned = sys.version_info[:2] == (3, 13)
print(f"Python                 {version:<12} {'OK (pinned 3.13)' if pinned else 'NOT 3.13 -- see README'}")

# 2. The libraries, at the exact versions pyproject.toml pins.
for package in ("google-adk", "google-genai"):
    try:
        print(f"{package:<22} {importlib.metadata.version(package):<12} OK")
    except importlib.metadata.PackageNotFoundError:
        print(f"{package:<22} {'MISSING':<12} run `uv sync`")

# 3. The model. The key is never printed, not even partly.
key_set = bool(os.environ.get("GOOGLE_API_KEY"))
print(f"{'GOOGLE_API_KEY':<22} {'set' if key_set else 'MISSING':<12}"
      f" {'' if key_set else 'copy .env.example to .env and fill it in'}")
print(f"{'model':<22} {config.model_label():<12} backend={config.BACKEND}"
      f" vertex={os.environ.get('GOOGLE_GENAI_USE_VERTEXAI')}")

# 4. Postgres. Tonight we only check that something answers on the port --
#    session 3 is what actually queries it. No database driver is installed yet,
#    and pretending otherwise would be a dependency we do not need.
try:
    with socket.create_connection((config.POSTGRES_HOST, config.POSTGRES_PORT), timeout=2):
        print(f"{'postgres port':<22} {'answering':<12}"
              f" {config.POSTGRES_HOST}:{config.POSTGRES_PORT} (used from session 3)")
except OSError as error:
    print(f"{'postgres port':<22} {'silent':<12} {error} -- run `docker compose up -d`")

print("\nThat is the whole environment. Three commands, and nothing installed on the host.")
