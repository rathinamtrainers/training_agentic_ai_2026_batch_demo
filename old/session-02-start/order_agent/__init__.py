# Makes this folder an agent ADK can load, so `adk run order_agent` and
# `adk web .` both find it. ADK looks for `root_agent` in agent.py.
from . import agent  # noqa: F401
