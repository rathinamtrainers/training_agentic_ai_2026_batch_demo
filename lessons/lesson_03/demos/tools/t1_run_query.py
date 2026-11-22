"""Step 1: the tool from the story. The code works. The description does not."""
import invoice_db
from common import get_supplier_contact, list_supplier_invoices


def run_query(ref: str) -> dict:
    """Queries the system."""
    row = invoice_db.find(ref)
    if row is None:
        return {"status": "not_found", "message": f"No invoice exists with number {ref}."}
    return {"status": "ok", "invoice": row}


TOOLS = [run_query, list_supplier_invoices, get_supplier_contact]
