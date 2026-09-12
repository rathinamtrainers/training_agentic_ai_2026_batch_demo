"""Two tools, and two sets of words describing them. The code never changes.

This is the whole of demo 6. Below are two real Python functions. Their bodies
are written once and are never touched again. What the flag switches is their
DOCSTRINGS -- the English the model reads -- by assigning to __doc__ before the
agent is built.

The bad variant is not a strawman. It is the mistake everybody makes: two tools
that sound like each other, and the less relevant one described better than the
relevant one. Slide 26: ambiguity between two tools is the top cause of wrong
calls.
"""

ORDERS = {
    "A-4471": {"status": "in transit", "carrier": "BlueDart", "expected": "2026-08-19"},
    "A-4472": {"status": "delivered", "carrier": "BlueDart", "expected": "2026-08-11"},
}

RETURNS = {
    "R-1180": {"status": "refund issued", "refunded": "2026-08-08"},
}


def get_order_status(order_id: str) -> dict:
    """Look up the delivery status of one customer order.

    Use this whenever the user asks where an order is, whether it has shipped,
    when it will arrive, or who is delivering it.

    Do not use this for returns or refunds -- use get_return_status for those.

    Args:
        order_id: The customer's order reference, which always looks like
            "A-4471". Pass it exactly as the user wrote it.

    Returns:
        A dict with "status", "carrier" and "expected". If the reference is not
        an order reference, "status" is "not found".
    """
    print(f"    [tool] get_order_status(order_id={order_id!r})")
    record = ORDERS.get(order_id.strip().upper())
    return {"order_id": order_id, **(record or {"status": "not found"})}


def get_return_status(return_id: str) -> dict:
    """Look up progress on a return the customer has already sent back to us.

    Use this only after the customer has posted an item back and wants to know
    whether we received it or refunded it.

    Do not use this to find out where an order is -- use get_order_status.

    Args:
        return_id: The return reference from the returns label, which always
            looks like "R-1180". This is not an order reference.

    Returns:
        A dict with "status" and, if refunded, the date.
    """
    print(f"    [tool] get_return_status(return_id={return_id!r})")
    record = RETURNS.get(return_id.strip().upper())
    return {"return_id": return_id, **(record or {"status": "not found"})}


# --- The same two tools, described badly -------------------------------------
#
# A first attempt at this made both descriptions merely vague, and
# gemini-3.7-flash saw straight through it and called the right tool anyway.
# Vagueness is not what breaks tools in real systems. THIS is: descriptions
# that were true once and were never updated after somebody repurposed the
# functions. Every line below is a sentence a real team has shipped.
#
# Two independent traps, so the demo fails on one or the other:
#
#   1. get_order_status now describes itself as internal stock control and
#      explicitly warns the model off customer questions, while
#      get_return_status describes itself as exactly what the user is asking
#      for. The model does the sensible thing with the words it was given, and
#      calls the wrong function.
#   2. If it calls get_order_status anyway, the Args line tells it to strip the
#      letter prefix -- so it passes "4471", the lookup misses, and the customer
#      is told their order does not exist.
#
# Neither trap touches a line of the function bodies above.

BAD_ORDER_DOC = """Registers and updates warehouse order records.

Internal stock-control use only. Not for answering customer questions about
deliveries.

Args:
    order_id: The numeric part of the reference only, with no letter prefix and
        no hyphen. For example, for reference A-4471 pass 4471.
"""

BAD_RETURN_DOC = """Look up where a customer's item is right now and when it is
expected to arrive.

Use this for any customer question about an order, a delivery, a parcel or a
shipment.

Args:
    return_id: The reference the customer quoted, exactly as they wrote it.
"""


def apply(variant: str) -> list:
    """Switch the words. One flag, one assignment, no change to any function
    body. Returns the tool list to hand to the agent."""
    if variant == "bad":
        get_order_status.__doc__ = BAD_ORDER_DOC
        get_return_status.__doc__ = BAD_RETURN_DOC
    return [get_order_status, get_return_status]
