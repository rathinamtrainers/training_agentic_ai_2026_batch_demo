"""Step 4: one change from step 3. The parameter is described, with its format as an example."""
import invoice_db
from common import get_supplier_contact, list_supplier_invoices


def get_invoice_status(invoice_number: str) -> dict:
    """Looks up one supplier invoice by its invoice number and returns the payment status,
    the amount and the due date. Use this when the user asks about a specific invoice.
    Do not use this to list invoices for a supplier.

    Args:
        invoice_number: The invoice number as printed on the invoice, in the form INV-4471.
    """
    row = invoice_db.find(invoice_number)
    if row is None:
        return {"status": "not_found",
                "message": f"No invoice exists with number {invoice_number}. Ask the user to check the number."}
    return {"status": "ok", "invoice": row}


TOOLS = [get_invoice_status, list_supplier_invoices, get_supplier_contact]
