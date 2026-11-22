"""Schema, loose: the list tool's status is free text described in prose, and it is required.
The invoice tool is the repaired one from t4_format.py."""
import invoice_db
from common import get_supplier_contact
from t4_format import get_invoice_status


def list_supplier_invoices(supplier: str, status: str) -> dict:
    """Lists the invoices from one supplier with one payment status.
    Use this when the user asks about a supplier's invoices in general.
    Do not use this to look up one invoice by its number.

    Args:
        supplier: The supplier's company name, e.g. Calder Engineering.
        status: The payment status of the invoices.
    """
    rows = invoice_db.for_supplier(supplier, status)
    if not rows:
        return {"status": "not_found",
                "message": f"No invoices found for supplier {supplier!r} with status {status!r}."}
    return {"status": "ok", "count": len(rows), "invoices": rows}


TOOLS = [get_invoice_status, list_supplier_invoices, get_supplier_contact]
