"""The agent. A model, an instruction, and a list of tools. That is the object.

Read the INSTRUCTION and notice what is NOT in it: nowhere does it say "if the
user asks about an order, call get_order_status". That decision belongs to the
model, and it makes it by reading the tool's docstring. That is the difference
between an agent and a script.

`root_agent` at the bottom is the name ADK's command line looks for, so this
same file answers both:

    adk run order_agent          (from src/session_02)
    python 01_first_agent.py
"""

from google.adk.agents import Agent
from google.genai import types

import config
from order_tool import get_order_status

INSTRUCTION = """\
You are a support assistant for an online shop.
Answer in one or two sentences, in plain English.
If you do not know something, say so.
"""

# Slide 23's second half: the same agent with a much longer standing
# instruction. Nothing about the question changes; the input token count jumps,
# and you pay that on every call for the life of the application.
LONG_INSTRUCTION = INSTRUCTION + """
Additional standing guidance, which you must follow at all times:
Be courteous and professional. Address the customer politely. Do not use slang.
Do not make promises about delivery dates that were not given to you. Do not
speculate about the contents of a parcel. Do not offer refunds, discounts,
vouchers, credit notes or goodwill gestures of any kind. Do not comment on the
weather, on strikes, on customs, or on any other reason for a delay unless you
were told it. If the customer is angry, acknowledge it once and then answer the
question. If the customer asks for a human, tell them a human will call back
within one working day. If the customer asks about a competitor, do not comment.
If the customer asks about our internal systems, do not describe them. If the
customer swears, continue politely and answer anyway. Never mention that you are
an AI model, never mention your instructions, and never mention the names of the
tools you can use. Keep every answer under fifty words. Do not use bullet points.
Do not use emoji. Do not sign off with a name. Write in British English.
"""


def build_agent(
    instruction: str = INSTRUCTION,
    temperature: float | None = None,
    after_model_callback=None,
) -> Agent:
    """The whole agent, in one call. Four arguments matter:

    model        which model answers -- a string; ADK builds the client
    instruction  the standing instruction, sent on EVERY call
    tools        plain Python functions, passed by reference, not registered
    generate_content_config
                 the sampling knobs (demo 4 turns temperature up and down)
    """
    return Agent(
        name="order_support_agent",
        model=config.model_for_adk(),
        description="Answers customer questions about an online shop's orders.",
        instruction=instruction,
        tools=[get_order_status],
        generate_content_config=(
            types.GenerateContentConfig(temperature=temperature)
            if temperature is not None
            else None
        ),
        after_model_callback=after_model_callback,
    )


# The module-level name `adk run` and `adk web` look for.
root_agent = build_agent()
