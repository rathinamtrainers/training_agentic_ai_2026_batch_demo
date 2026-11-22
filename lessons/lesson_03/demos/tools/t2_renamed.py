"""Step 2: one change from step 1. The name and the parameter name. The docstring is the same."""
import invoice_db
from common import get_supplier_contact, list_supplier_invoices


def get_invoice_status(invoice_number: str) -> dict:
    """Queries the system."""
    row = invoice_db.find(invoice_number)
    if row is None:
        return {"status": "not_found", "message": f"No invoice exists with number {invoice_number}."}
    return {"status": "ok", "invoice": row}


TOOLS = [get_invoice_status, list_supplier_invoices, get_supplier_contact]
