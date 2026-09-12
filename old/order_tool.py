"""The tool. A plain Python function, and nothing else.

Deliberately NOT an LLM call. Session 2's lesson is tool calling, and a second
model inside the tool would make it impossible to tell which model got it wrong.
Retrieval becomes the real tool in sessions 3 and 4.

The docstring below is not a comment. ADK sends it to the model, word for word,
as the description of this tool. The type hints become the parameter schema.
Those two things are the entire interface the model gets -- so write them for
the model, the way you would brief a new colleague on their first day.
"""

# A fixed table, so the answer is the same every time and any variation the room
# sees comes from the model rather than from the data.
ORDERS = {
    "A-4471": {"status": "in transit", "carrier": "BlueDart", "expected": "2026-08-19"},
    "A-4472": {"status": "delivered", "carrier": "BlueDart", "expected": "2026-08-11"},
    "A-4480": {"status": "being packed", "carrier": "not assigned yet", "expected": "2026-08-22"},
}


def get_order_status(order_id: str) -> dict:
    """Look up the delivery status of one customer order.

    Use this whenever the user asks where an order is, whether it has shipped,
    when it will arrive, or who is delivering it. Do not answer those questions
    from memory -- this table is the only source of truth for order status.

    Do not use this for returns, refunds or payment questions.

    Args:
        order_id: The customer's order reference, in the form "A-4471".
            Pass it exactly as the user wrote it, including the letter and the
            hyphen.

    Returns:
        A dict with "order_id", "status", "carrier" and "expected" (a date).
        If the order reference is not in the system, "status" is "not found"
        and you should say so rather than guessing.
    """
    # Printed so the room watches the runtime -- not the model -- execute this.
    print(f"    [tool] get_order_status(order_id={order_id!r}) is running now, in Python")
    record = ORDERS.get(order_id.strip().upper())
    if record is None:
        return {"order_id": order_id, "status": "not found"}
    return {"order_id": order_id.strip().upper(), **record}
