"""The 'finance database': invoices.csv, read fresh on every query.

Every query is recorded in QUERIES with how many rows it matched, so the runner can
answer "did it call correctly?" from what the database actually saw.
"""
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
QUERIES = []          # (description of the query, number of rows matched)


def _rows():
    with open(HERE / "invoices.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def find(invoice_number):
    """Exact match on the number as stored, e.g. 'INV-4471'. Returns the row or None."""
    hits = [r for r in _rows() if r["invoice_number"] == str(invoice_number)]
    QUERIES.append((f"invoice_number == {invoice_number!r}", len(hits)))
    return hits[0] if hits else None


def for_supplier(supplier, status=None):
    """Rows for one supplier (case-insensitive), optionally only one status."""
    hits = [r for r in _rows() if r["supplier"].lower() == str(supplier).lower()
            and (status is None or r["status"] == status)]
    QUERIES.append((f"supplier == {supplier!r}" + (f" and status == {status!r}" if status is not None else ""),
                    len(hits)))
    return hits


def contact(supplier):
    """The accounts contact for one supplier (case-insensitive), from suppliers.csv, or None."""
    with open(HERE / "suppliers.csv", newline="", encoding="utf-8") as f:
        hits = [r for r in csv.DictReader(f) if r["supplier"].lower() == str(supplier).lower()]
    QUERIES.append((f"contact for supplier == {supplier!r}", len(hits)))
    return hits[0] if hits else None
