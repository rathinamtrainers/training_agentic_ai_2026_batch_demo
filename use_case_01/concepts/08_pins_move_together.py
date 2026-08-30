"""A pin is not a preference. It is a constraint other packages have opinions about.

Real installed metadata, and the real PyPI metadata for the release you were about to upgrade to.
    uv run --project ../demo python 08_pins_move_together.py
"""
import json
import urllib.request
from importlib.metadata import requires, version

from packaging.requirements import Requirement

PINNED = ["google-adk", "google-genai", "psycopg", "pgvector", "fastapi"]
print("=== installed in this environment (demo/pyproject.toml, resolved by uv)")
for name in PINNED:
    print(f"  {name:<14} {version(name)}")

installed_genai = version("google-genai")
here = next(r for r in requires("google-adk") if r.startswith("google-genai"))
print(f"\n=== google-adk {version('google-adk')} requires: {here}")
print(f"  google-genai {installed_genai} satisfies it: "
      f"{Requirement(here).specifier.contains(installed_genai)}")

TARGET = "2.8.0"      # the release that is current while the lab stays on 2.6.3
url = f"https://pypi.org/pypi/google-adk/{TARGET}/json"
metadata = json.load(urllib.request.urlopen(url, timeout=20))["info"]["requires_dist"]
there = next(r for r in metadata if r.startswith("google-genai"))
print(f"\n=== google-adk {TARGET} on PyPI, read live, requires: {there}")
ok = Requirement(there).specifier.contains(installed_genai)
print(f"  google-genai {installed_genai} satisfies it: {ok}")
print(f"  -> upgrading google-adk alone is {'fine' if ok else 'a CONFLICT: both pins move, or neither'}")
