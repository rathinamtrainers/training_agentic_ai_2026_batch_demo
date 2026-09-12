# 08 — Pins move together

`../08_pins_move_together.py`

## Summary

The odd one out in the sequence: no model call, no credentials, no AI at all. It
reads package metadata.

It prints the versions actually installed in this environment, then asks
`google-adk` what it requires of `google-genai` — first the installed release,
then the newer one on PyPI, fetched live over HTTP. The last line answers the
only question that matters:

> upgrading google-adk alone is a CONFLICT: both pins move, or neither

That is the lesson. A pin is not a preference you hold about a package. It is a
constraint that other packages have opinions about, and the AI libraries move
fast enough that those opinions change monthly. `google-adk` is deliberately held
at 2.6.3 in `demo/pyproject.toml` while 2.8.0 is current, and the gap is taught
rather than tidied away.

---

## Aspect by aspect

### 1. What is installed, read from the environment

```python
from importlib.metadata import requires, version

PINNED = ["google-adk", "google-genai", "psycopg", "pgvector", "fastapi"]
for name in PINNED:
    print(f"  {name:<14} {version(name)}")
```

`importlib.metadata` reads the installed distribution metadata — what `uv`
actually resolved into this environment. It is not reading `pyproject.toml`, and
that distinction is the point: the file states intent, this states fact, and
diagnosing a dependency problem starts with the fact.

The five names are the ones that can break the demo. Note `psycopg`, not
`psycopg[binary]` — the extra is an install-time decision and does not appear in
the distribution name.

### 2. The requirement, parsed rather than eyeballed

```python
installed_genai = version("google-genai")
here = next(r for r in requires("google-adk") if r.startswith("google-genai"))
print(f"  google-genai {installed_genai} satisfies it: "
      f"{Requirement(here).specifier.contains(installed_genai)}")
```

`requires("google-adk")` returns the raw requirement strings from the installed
package — things like `google-genai>=2.17.0,<3.0.0`, sometimes with an
environment marker attached.

`packaging.requirements.Requirement` parses that properly, and
`.specifier.contains(...)` answers the comparison. This is done with the real
parser rather than a string comparison on purpose: version ordering is not
lexicographic, `2.10.0` sorts *after* `2.9.0` however it looks, and pre-releases
and epochs have rules nobody remembers. Comparing version strings by hand is a
recurring source of confident, wrong answers.

`next(...)` with a generator takes the first matching line and raises
`StopIteration` if `google-adk` ever stops depending on `google-genai`. Loud
failure, which is the right behaviour for a teaching script.

This first check should print `True` — the installed set is consistent, because
`uv` resolved it.

### 3. The upgrade you were about to do

```python
TARGET = "2.8.0"      # the release that is current while the lab stays on 2.6.3
url = f"https://pypi.org/pypi/google-adk/{TARGET}/json"
metadata = json.load(urllib.request.urlopen(url, timeout=20))["info"]["requires_dist"]
```

This is the interesting half. Rather than describing what would happen on
upgrade, the script asks PyPI directly. `/pypi/<name>/<version>/json` is a public
read-only endpoint; `info.requires_dist` is the same requirement list the
installed package exposes, for a release that is *not* installed.

So the comparison is between a real installed version and a real published
requirement. Nothing is asserted from memory or from a comment.

It is the only network call in the concepts folder that is not a model call, and
the only one that needs no credentials. `timeout=20` means a firewalled machine
fails in twenty seconds rather than hanging — worth knowing before running it in
a locked-down training room.

### 4. The verdict

```python
ok = Requirement(there).specifier.contains(installed_genai)
print(f"  -> upgrading google-adk alone is {'fine' if ok else 'a CONFLICT: both pins move, or neither'}")
```

ADK 2.8.0 requires `google-genai >= 2.19`, and 2.17.0 is pinned here, so `ok` is
`False`.

What that means in practice: `pip install -U google-adk` does not fail. It
upgrades `google-genai` too, silently, because that is what a resolver is for.
The pin in `pyproject.toml` was the only thing holding the line, and the upgrade
walked through it. If the newer `google-genai` changed a default or renamed a
field, you find out at runtime, in front of a room.

Hence the phrasing: **both pins move, or neither.** An upgrade is a deliberate
act — bump both, re-run `uv lock`, then walk the whole run order in `README.md`
before the session. That instruction is written into `demo/pyproject.toml`'s
comments, and this script is its evidence.

### 5. Why this sits in a course about agents

Because it is where the demos actually break. The model behaves; the dependency
graph does not. Two of these libraries — `google-adk` and `google-genai` — are
young and moving fast, and a transitive upgrade the night before a session is a
real risk with a real mitigation.

It also stands as the general case of a habit the rest of the folder relies on:
pin the version, write down the date you checked it, and re-check deliberately.
The same discipline appears as the price list in script 01 and the model ids in
the `.env`.

---

## What to take away

- A pin is a constraint other packages negotiate with, not a preference.
- `importlib.metadata` tells you what is installed; `pyproject.toml` tells you
  what was intended. Debug with the first.
- Parse versions with `packaging`. Do not compare version strings.
- PyPI's JSON API answers "what would this upgrade require?" without installing
  anything.
- `pip install -U <one package>` will move its dependencies without asking. Move
  the whole pinned set deliberately, re-lock, and re-run the demos.

## Related

- `demo/pyproject.toml` — the pins and the reasoning, in comments.
- `demo/uv.lock` — the resolved set this script reads back.
- `../run_logs/08_pins_move_together_RUN_LOG.md` — recorded runs.
