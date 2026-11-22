"""Schema, tight: the list tool from common.py. Status is a fixed list of three values
(Literal -> enum) and it is optional (it has a default). Nothing else changed from s1."""
from common import get_supplier_contact, list_supplier_invoices
from t4_format import get_invoice_status

TOOLS = [get_invoice_status, list_supplier_invoices, get_supplier_contact]
