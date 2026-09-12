"""Northwind's DocStore export, as this demo sees it: forty markdown documents
in four tenant folders.

This module exists so that a citation can be RESOLVED -- turned back into the
paragraph it came from -- without going near the database. Acceptance criterion
2 is "every citation resolves to a real passage in a real document", and a
check that only asks the database is checking the retriever's own homework.
Here we go back to the file on disk, which is the thing a Northwind employee
would open.
"""

import functools
import pathlib

import chunking

ROOT = pathlib.Path(__file__).parent / "corpus"


@functools.lru_cache(maxsize=None)
def clauses(tenant_id: str) -> dict[tuple[str, str], str]:
    """{(source_file, clause): passage text} for one tenant."""
    index: dict[tuple[str, str], str] = {}
    for path in sorted((ROOT / tenant_id).glob("*.md")):
        for chunk in chunking.split_document(path.read_text(encoding="utf-8")):
            key = (path.name, chunk.clause)
            index[key] = index.get(key, "") + chunk.content
    return index


def files(tenant_id: str) -> set[str]:
    return {path.name for path in (ROOT / tenant_id).glob("*.md")}


def resolve(tenant_id: str, source_file: str, clause: str) -> str | None:
    """The passage behind a citation, or None if the citation is invented."""
    return clauses(tenant_id).get((source_file, clause))


def document_count(tenant_id: str) -> int:
    return len(list((ROOT / tenant_id).glob("*.md")))
