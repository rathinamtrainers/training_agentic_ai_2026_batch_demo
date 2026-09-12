"""Splitting a Northwind document into chunks that can be cited.

Two decisions, and only one of them is arbitrary.

NOT arbitrary: the split follows the document's own clause headings. Northwind's
material is clause-structured -- "## 4. Escape of water" -- and a retrieval
system whose answers must carry a clause reference should cut on the clause
boundary, not every 800 characters. Cut arbitrarily and half your chunks
straddle two clauses, and then no citation you produce is true.

Arbitrary: MAX_CHUNK_CHARS. A clause longer than that gets split, with an
overlap so a sentence on the boundary survives. That number is a default and
nothing more, it is printed as one, and it is the thing to change when the room
asks "what happens if we chunk differently?"
"""

import dataclasses
import pathlib
import re

import config

# "## 4. Escape of water"  ->  clause "4", heading "Escape of water"
HEADING = re.compile(r"^##\s+(?P<clause>[0-9]+(?:\.[0-9]+)*)\.?\s+(?P<heading>.+?)\s*$")
TITLE = re.compile(r"^#\s+(?P<title>.+?)\s*$")


@dataclasses.dataclass
class Chunk:
    clause: str
    heading: str
    content: str


def split_document(text: str) -> list[Chunk]:
    """Markdown in, citable chunks out."""
    sections: list[Chunk] = []
    current: Chunk | None = None
    preamble: list[str] = []

    for line in text.splitlines():
        heading = HEADING.match(line)
        if heading:
            if current:
                sections.append(current)
            current = Chunk(
                clause=heading.group("clause"),
                heading=heading.group("heading"),
                content=f"{heading.group('clause')}. {heading.group('heading')}\n",
            )
            continue
        if current:
            current.content += line + "\n"
        elif not TITLE.match(line):
            preamble.append(line)

    if current:
        sections.append(current)

    # A document with no clause headings still has to be ingestable, so the
    # whole of it becomes clause "0". None of Northwind's forty look like that;
    # a real DocStore export will, and silently dropping the file would be the
    # worst possible failure mode.
    if not sections:
        body = "\n".join(preamble).strip()
        return _enforce_ceiling(Chunk(clause="0", heading="(no clause headings)", content=body))

    out: list[Chunk] = []
    for section in sections:
        out.extend(_enforce_ceiling(section))
    return out


def _enforce_ceiling(section: Chunk) -> list[Chunk]:
    """The arbitrary half. Split an over-long clause, keeping its label on
    every piece -- the citation must survive the split."""
    body = section.content.strip()
    if not body:
        return []
    if len(body) <= config.MAX_CHUNK_CHARS:
        return [Chunk(section.clause, section.heading, body)]

    pieces: list[Chunk] = []
    start = 0
    while start < len(body):
        end = start + config.MAX_CHUNK_CHARS
        piece = body[start:end].strip()
        if piece:
            pieces.append(Chunk(section.clause, section.heading, piece))
        if end >= len(body):
            break
        start = end - config.CHUNK_OVERLAP_CHARS
    return pieces


def load_tenant(corpus_root: pathlib.Path, tenant_id: str) -> list[tuple[str, Chunk]]:
    """Every (source_file, chunk) pair for one tenant, in file order."""
    tenant_dir = corpus_root / tenant_id
    if not tenant_dir.is_dir():
        config.fail(f"no corpus directory for tenant {tenant_id!r} at {tenant_dir}")
    rows: list[tuple[str, Chunk]] = []
    for path in sorted(tenant_dir.glob("*.md")):
        for chunk in split_document(path.read_text(encoding="utf-8")):
            rows.append((path.name, chunk))
    return rows


def describe() -> str:
    return (
        "chunk = one clause of one document. A clause over "
        f"{config.MAX_CHUNK_CHARS} chars is split with "
        f"{config.CHUNK_OVERLAP_CHARS} chars of overlap "
        f"(~{config.MAX_CHUNK_CHARS // config.CHARS_PER_TOKEN} tokens at "
        f"1 token ~ {config.CHARS_PER_TOKEN} chars -- an approximation, not a "
        "tokenizer). The ceiling is a default and nothing more."
    )
