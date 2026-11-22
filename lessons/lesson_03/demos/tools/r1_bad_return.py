"""Return value, careless: the same name, docstring and schema as t4_format.py.
Only the return changes. A found invoice comes back as a Python object; a missing one as None."""
import invoice_db
from common import get_supplier_contact, list_supplier_invoices


class Invoice:
    def __init__(self, row):
        self.number, self.status, self.paid_on = row["invoice_number"], row["status"], row["paid_on"]


def get_invoice_status(invoice_number: str) -> dict:
    """Looks up one supplier invoice by its invoice number and returns the payment status,
    the amount and the due date. Use this when the user asks about a specific invoice.
    Do not use this to list invoices for a supplier.

    Args:
        invoice_number: The invoice number as printed on the invoice, in the form INV-4471.
    """
    row = invoice_db.find(invoice_number)
    if row is None:
        return None
    return Invoice(row)


TOOLS = [get_invoice_status, list_supplier_invoices, get_supplier_contact]
