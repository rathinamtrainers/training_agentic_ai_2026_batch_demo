"""Lesson 4 demo: the lesson 1 invoice agent, rebuilt in Google ADK.

Same model as lessons 1 to 3 (qwen3:4b-instruct on local Ollama), same question, same
invoices.csv, same tool. ADK reaches Ollama through LiteLLM ("ollama_chat/..." model string).

    python adk_invoice_agent.py trace                    # Demo 1: the same agent, inside ADK
    python adk_invoice_agent.py cap --max-llm-calls 1    # Demo 2: the call cap, set to one
    python adk_invoice_agent.py cap                      # Demo 2: cap from RunConfig() (default or ADK_MAX_LLM_CALLS)
    python adk_invoice_agent.py budget                   # Demo 3: the budget, as a before-model callback
    python adk_invoice_agent.py upgrade                  # Demo 4: run it under ADK 2.8.0 and 2.10.0

    AGENT_MODEL       default qwen3:4b-instruct   (any Ollama model with the "tools" capability)
    OLLAMA_API_BASE   default http://127.0.0.1:11434
"""
import argparse, asyncio, csv, getpass, json, logging, os, sys, time, warnings
from importlib.metadata import version
from pathlib import Path

# ADK 2.10.0 prints a one-line "[EXPERIMENTAL] feature JSON_SCHEMA_FOR_FUNC_DECL" UserWarning on
# every tool declaration. It is noise on a projector; this line hides only that warning.
warnings.filterwarnings("ignore", message=r"\[EXPERIMENTAL\] feature FeatureName\.JSON_SCHEMA_FOR_FUNC_DECL")

os.environ.setdefault("OLLAMA_API_BASE", "http://127.0.0.1:11434")
logging.basicConfig(level=logging.WARNING, format="  [log %(levelname)s %(name)s] %(message)s")
for noisy in ("LiteLLM", "litellm", "httpx"):
    logging.getLogger(noisy).setLevel(logging.ERROR)

from google.adk.agents import LlmAgent                                   # noqa: E402
from google.adk.agents.run_config import RunConfig                       # noqa: E402
from google.adk.events import Event                                      # noqa: E402
from google.adk.models.lite_llm import LiteLlm                           # noqa: E402
from google.adk.models.llm_response import LlmResponse                   # noqa: E402
from google.adk.runners import Runner                                    # noqa: E402
from google.adk.sessions import InMemorySessionService, Session          # noqa: E402
from google.genai import types                                           # noqa: E402

HERE = Path(__file__).resolve().parent
MODEL_NAME = os.environ.get("AGENT_MODEL", "qwen3:4b-instruct")
SYSTEM = "You are a finance assistant for the accounts team. Use the tools to answer."
APP, USER = "invoice_app", "priya"


# ---- the tools: plain Python functions. ADK reads the name, type hints and docstring.
def load_invoices():
    with open(HERE / "invoices.csv", newline="") as f:
        return {int(r["invoice_number"]): r for r in csv.DictReader(f)}


def lookup_invoice(invoice_number: int) -> dict:
    """Look up one invoice in the finance database by its number.

    Returns customer, amount, status (paid/unpaid), paid_on date and payment reference.

    Args:
        invoice_number: The invoice number, e.g. 4471
    """
    print(f"  --- ADK calls our function lookup_invoice({invoice_number!r}) ---")
    print(f"  credentials : OS user '{getpass.getuser()}', pid {os.getpid()} - this process's rights")
    row = load_invoices().get(int(invoice_number))
    return row if row else {"error": f"invoice {invoice_number} not found"}


def read_server_log(server: str) -> str:
    """Read the full export-job log of a server.

    Args:
        server: Server name, e.g. fin-export-01
    """
    lines = [f"2026-03-12T02:{(i // 60) % 60:02d}:{i % 60:02d}Z {server} export-job INFO "
             f"batch={i} rows=250 status=ok" for i in range(40_000)]
    lines[39_000] = f"2026-03-12T04:30:00Z {server} export-job ERROR disk full on /var/export"
    text = "\n".join(lines)
    print(f"  --- ADK calls our function read_server_log({server!r}) -> {len(text):,} characters ---")
    return text


# ---- printing: one line per thing that happened, read from ADK's own events
def show_event(ev, totals):
    u = ev.usage_metadata
    if u is not None and ev.author != "user":
        totals["calls"] += 1
        totals["tokens"] += (u.prompt_token_count or 0) + (u.candidates_token_count or 0)
        print(f"\n=== model call {totals['calls']} (event by '{ev.author}') ===")
        print(f"  cost        : input {u.prompt_token_count} tokens, output {u.candidates_token_count} tokens"
              f"   (run total so far: {totals['tokens']})")
    for part in (ev.content.parts if ev.content and ev.content.parts else []):
        if part.function_call:
            print(f"  model asked : {part.function_call.name}({json.dumps(part.function_call.args)})")
        elif part.function_response:
            shown = json.dumps(part.function_response.response)
            shown = shown if len(shown) < 300 else shown[:150] + f" ... [{len(shown):,} characters]"
            print(f"  tool result : {shown}   <- ADK appended this to the session")
        elif part.text and ev.author != "user":
            print(f"  model said  : {part.text.strip()!r}   <- no tool request: ADK stops the loop")


async def run(agent, question, session_service, session_id, run_config=None):
    """The whole of lesson 1's while loop, as far as our code is concerned."""
    runner = Runner(agent=agent, app_name=APP, session_service=session_service)  # <- THE LOOP lives in here
    totals = {"calls": 0, "tokens": 0}
    message = types.Content(role="user", parts=[types.Part(text=question)])
    async for ev in runner.run_async(user_id=USER, session_id=session_id, new_message=message,
                                     run_config=run_config or RunConfig()):
        show_event(ev, totals)
    return totals


def show_request(callback_context, llm_request):
    """A before-model callback that only prints. Shows what ADK hands the model client."""
    if getattr(show_request, "done", False):
        return None
    show_request.done = True
    print("=== what ADK built from our function, sent with every model call ===")
    for tool in (llm_request.config.tools or []):
        for decl in tool.function_declarations or []:
            print(json.dumps(decl.model_dump(mode="json", exclude_none=True), indent=2))
    return None


def header(extra=""):
    print(f"google-adk {version('google-adk')} | model ollama_chat/{MODEL_NAME} at {os.environ['OLLAMA_API_BASE']}"
          f"{extra}")


# ---------------------------------------------------------------- Demo 1
async def cmd_trace(invoice):
    header()
    agent = LlmAgent(name="invoice_agent",
                     model=LiteLlm(model=f"ollama_chat/{MODEL_NAME}"),   # <- THE MODEL CLIENT: one string
                     instruction=SYSTEM,
                     tools=[lookup_invoice],                            # <- THE TOOL REGISTRY: a list
                     before_model_callback=show_request)
    sessions = InMemorySessionService()                                 # <- THE MESSAGES LIST lives in here
    s = await sessions.create_session(app_name=APP, user_id=USER)
    print(f"session created: id {s.id} for user '{USER}', events in it: {len(s.events)}\n")
    t0 = time.time()
    totals = await run(agent, f"Has invoice {invoice} been paid?", sessions, s.id)
    print(f"\n>>> model calls: {totals['calls']}   tokens this run: {totals['tokens']}   {time.time() - t0:.1f} s")
    s = await sessions.get_session(app_name=APP, user_id=USER, session_id=s.id)
    print(f"\n=== the session after the run: {len(s.events)} events (this was your messages list) ===")
    show_session(s)


# ---------------------------------------------------------------- Demo 2
async def cmd_cap(invoice, max_llm_calls):
    cfg = RunConfig() if max_llm_calls is None else RunConfig(max_llm_calls=max_llm_calls)
    env = os.environ.get("ADK_MAX_LLM_CALLS")
    header(f" | RunConfig().max_llm_calls default here: {RunConfig().max_llm_calls}"
           f" (ADK_MAX_LLM_CALLS={env!r}) | this run: {cfg.max_llm_calls}")
    agent = LlmAgent(name="invoice_agent", model=LiteLlm(model=f"ollama_chat/{MODEL_NAME}"),
                     instruction=SYSTEM, tools=[lookup_invoice])
    sessions = InMemorySessionService()
    s = await sessions.create_session(app_name=APP, user_id=USER)
    totals = {"calls": 0, "tokens": 0}
    try:
        totals = await run(agent, f"Has invoice {invoice} been paid?", sessions, s.id, cfg)
        print(f"\n>>> finished normally. model calls: {totals['calls']}")
    except Exception as e:
        print(f"\n>>> {type(e).__module__}.{type(e).__name__}: {e}")
    s = await sessions.get_session(app_name=APP, user_id=USER, session_id=s.id)
    print(f">>> the session kept {len(s.events)} events:")
    show_session(s)


def show_session(s):
    for i, ev in enumerate(s.events, 1):
        kinds = [("function_call" if p.function_call else "function_response" if p.function_response else "text")
                 for p in (ev.content.parts if ev.content and ev.content.parts else [])]
        err = f"  error_code={ev.error_code!r} error_message={ev.error_message!r}" if ev.error_code else ""
        print(f"  {i}. author={ev.author:<14} {kinds}{err}")


# ---------------------------------------------------------------- Demo 3
def make_budget_guard(budget):
    """Lesson 1's LIMIT 3, moved into a callback. ADK gives the hook; the rule is ours."""
    spent = {"tokens": 0}

    def before_model(callback_context, llm_request):
        about_to_send = len(json.dumps([c.model_dump(mode="json", exclude_none=True)
                                        for c in llm_request.contents])) // 4
        if spent["tokens"] + about_to_send > budget:
            msg = (f"BUDGET: refused this model call: {spent['tokens']} spent + ~{about_to_send} "
                   f"about to send > budget {budget}")
            print(f"\n  [before_model_callback] {msg}")
            return LlmResponse(content=types.Content(role="model", parts=[types.Part(text=msg)]))
        print(f"\n  [before_model_callback] ok: {spent['tokens']} spent + ~{about_to_send} about to send"
              f" <= budget {budget}")
        return None

    def after_model(callback_context, llm_response):
        u = llm_response.usage_metadata
        if u:
            spent["tokens"] += (u.prompt_token_count or 0) + (u.candidates_token_count or 0)
        return None

    return before_model, after_model


async def cmd_budget(budget):
    header(f" | budget {budget} tokens")
    before, after = make_budget_guard(budget)
    agent = LlmAgent(name="log_agent", model=LiteLlm(model=f"ollama_chat/{MODEL_NAME}"),
                     instruction=SYSTEM, tools=[read_server_log],
                     before_model_callback=before, after_model_callback=after)
    sessions = InMemorySessionService()
    s = await sessions.create_session(app_name=APP, user_id=USER)
    totals = await run(agent, "Why did last night's invoice export fail on server fin-export-01? Check its log.",
                       sessions, s.id)
    print(f"\n>>> model calls actually made (events with usage): {totals['calls']}"
          f"   tokens this run: {totals['tokens']}")


# ---------------------------------------------------------------- Demo 4
async def cmd_upgrade():
    header(" | same file, run under each installed version")

    print("\n--- A. run the agent on a session id we made up, never created ---")
    agent = LlmAgent(name="invoice_agent", model=LiteLlm(model=f"ollama_chat/{MODEL_NAME}"),
                     instruction=SYSTEM, tools=[lookup_invoice])
    try:
        await run(agent, "Has invoice 4471 been paid?", InMemorySessionService(), "demo-session-1")
        print(">>> the run went ahead")
    except Exception as e:
        print(f">>> {type(e).__name__}: {e}")

    print("\n--- B. write one message into a session the store has never heard of ---")
    sessions = InMemorySessionService()
    ghost = Session(id="made-up-123", app_name=APP, user_id=USER)
    ev = Event(author="user", content=types.Content(role="user", parts=[types.Part(text="hello")]))
    try:
        await sessions.append_event(ghost, ev)
        print(">>> append_event returned normally")
    except Exception as e:
        print(f">>> {type(e).__name__}: {e}")
    stored = await sessions.get_session(app_name=APP, user_id=USER, session_id="made-up-123")
    print(f">>> is that message in the store now? {'yes' if stored else 'no - there is no such session'}")

    print("\n--- C. an instruction with ${tenant_id}, and tenant_id='Northwind' in session state ---")
    seen = {}

    def capture(callback_context, llm_request):
        seen["instruction"] = llm_request.config.system_instruction
        return None

    agent = LlmAgent(name="tenant_agent", model=LiteLlm(model=f"ollama_chat/{MODEL_NAME}"),
                     instruction="You work for the tenant ${tenant_id}. Answer in one short sentence.",
                     before_model_callback=capture)
    sessions = InMemorySessionService()
    s = await sessions.create_session(app_name=APP, user_id=USER, state={"tenant_id": "Northwind"})
    runner = Runner(agent=agent, app_name=APP, session_service=sessions)
    answer = ""
    async for e in runner.run_async(user_id=USER, session_id=s.id, new_message=types.Content(
            role="user", parts=[types.Part(text="Which tenant do you work for? Quote its name exactly.")])):
        if e.content and e.content.parts and e.author != "user":
            answer += "".join(p.text or "" for p in e.content.parts)
    print(f"  instruction the model received: {seen.get('instruction')!r}")
    print(f"  model said                    : {answer.strip()!r}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["trace", "cap", "budget", "upgrade"])
    p.add_argument("--invoice", type=int, default=4471)
    p.add_argument("--max-llm-calls", type=int)
    p.add_argument("--budget", type=int, default=20_000)
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if a.mode == "trace":
        asyncio.run(cmd_trace(a.invoice))
    elif a.mode == "cap":
        asyncio.run(cmd_cap(a.invoice, a.max_llm_calls))
    elif a.mode == "budget":
        asyncio.run(cmd_budget(a.budget))
    else:
        asyncio.run(cmd_upgrade())


if __name__ == "__main__":
    main()
