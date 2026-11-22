"""The two other tools in the agent's toolbox. Both are written well, and neither changes
during the demo. Only the invoice tool in each t*.py file changes."""
from typing import Literal

import invoice_db


def list_supplier_invoices(supplier: str, status: Literal["paid", "unpaid", "overdue"] | None = None) -> dict:
    """Lists the invoices from one supplier, optionally only those with one payment status.
    Use this when the user asks about a supplier's invoices in general.
    Do not use this to look up one invoice by its number.

    Args:
        supplier: The supplier's company name, e.g. Calder Engineering.
        status: Only return invoices with this status. Leave it out to return all of them.
    """
    rows = invoice_db.for_supplier(supplier, status)
    if not rows:
        return {"status": "not_found", "message": f"No invoices found for supplier {supplier!r}"
                + (f" with status {status!r}." if status else ".")}
    return {"status": "ok", "count": len(rows), "invoices": rows}


def get_supplier_contact(supplier: str) -> dict:
    """Returns the accounts contact name, email and phone number for one supplier.
    Use this when the user wants to get in touch with a supplier.

    Args:
        supplier: The supplier's company name, e.g. Calder Engineering.
    """
    row = invoice_db.contact(supplier)
    if row is None:
        return {"status": "not_found", "message": f"No supplier called {supplier!r}."}
    return {"status": "ok", "contact": row}
