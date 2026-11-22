"""Lesson 3 demo: the tool description is the interface. Python standard library only.

Loads the plain Python functions in one file under tools/, builds the tool definitions
from them the way ADK, CrewAI and LangChain do (function name -> tool name, type hints ->
schema types, docstring -> description, "Args:" lines -> parameter descriptions,
no default -> required), sends them to a real model, runs the loop, and answers the three
questions: did it call, did it call correctly, what did it say.

Talks to any OpenAI-compatible chat endpoint. Default: Ollama on this machine.
    AGENT_BASE_URL  default http://127.0.0.1:11434/v1
    AGENT_MODEL     default qwen3:4b-instruct
    AGENT_API_KEY   default "ollama"

    python tool_lab.py tools/t1_run_query.py "Has invoice 4471 been paid?"
    python tool_lab.py tools/t1_run_query.py "Has invoice 4471 been paid?" --runs 3
    python tool_lab.py tools/t1_run_query.py "..." --system "YOU MUST ALWAYS USE THE run_query TOOL."
    python tool_lab.py tools/t4_format.py --show          # print the definition only, no model call
"""
import argparse, importlib.util, inspect, json, os, sys, time, types, typing, urllib.request
from pathlib import Path

BASE_URL = os.environ.get("AGENT_BASE_URL", "http://127.0.0.1:11434/v1")
MODEL = os.environ.get("AGENT_MODEL", "qwen3:4b-instruct")
API_KEY = os.environ.get("AGENT_API_KEY", "ollama")
HERE = Path(__file__).resolve().parent
SYSTEM = "You are an assistant for the accounts team. Answer the user's question."
JSON_TYPES = {str: "string", int: "integer", float: "number", bool: "boolean", list: "array", dict: "object"}


# ------------------------------------------------ WHAT A FRAMEWORK DOES WITH YOUR FUNCTION
def split_docstring(fn):
    """Docstring text before 'Args:' is the description; 'name: text' lines after it describe parameters."""
    doc = inspect.getdoc(fn) or ""
    head, _, args = doc.partition("Args:")
    params, current, base = {}, None, None
    for line in args.splitlines():
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        base = indent if base is None else base
        name, sep, text = line.strip().partition(":")
        if indent == base and sep and name.isidentifier():
            current = name
            params[current] = text.strip()
        elif current:
            params[current] += " " + line.strip()
    return " ".join(head.split()), params


def json_type(hint):
    """Python type hint -> JSON Schema fragment. Literal[...] becomes an enum."""
    if typing.get_origin(hint) is typing.Literal:
        return {"type": "string", "enum": list(typing.get_args(hint))}
    if typing.get_origin(hint) in (typing.Union, types.UnionType):
        inner = [a for a in typing.get_args(hint) if a is not type(None)]
        return json_type(inner[0])
    return {"type": JSON_TYPES.get(typing.get_origin(hint) or hint, "string")}


def tool_definition(fn):
    description, param_docs = split_docstring(fn)
    hints = typing.get_type_hints(fn)
    props, required = {}, []
    for name, p in inspect.signature(fn).parameters.items():
        props[name] = json_type(hints.get(name, str))
        if name in param_docs:
            props[name]["description"] = param_docs[name]
        if p.default is inspect.Parameter.empty:
            required.append(name)
    return {"type": "function", "function": {"name": fn.__name__, "description": description,
            "parameters": {"type": "object", "properties": props, "required": required}}}


def as_tool_result(value):
    """What the model reads back. Dicts and lists go as JSON; anything else as str(value)."""
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str)
    return str(value)
# ------------------------------------------------ END


def load_tools(path):
    spec = importlib.util.spec_from_file_location(Path(path).stem, path)
    module = importlib.util.module_from_spec(spec)
    sys.path[:0] = [str(HERE), str(Path(path).resolve().parent)]
    spec.loader.exec_module(module)
    return module.TOOLS


def call_model(messages, tools, options):
    body = {"model": MODEL, "messages": messages, "tools": tools, **options}
    req = urllib.request.Request(f"{BASE_URL}/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {API_KEY}"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"], data["usage"]


def run_once(question, system, funcs, definitions, options, max_steps):
    import invoice_db
    invoice_db.QUERIES.clear()
    impls = {f.__name__: f for f in funcs}
    messages = [{"role": "system", "content": system}, {"role": "user", "content": question}]
    calls, first_input_tokens = [], None
    for step in range(1, max_steps + 1):
        t0 = time.time()
        try:
            reply, usage = call_model(messages, definitions, options)
        except OSError as e:
            print(f"  MODEL_ERROR: cannot reach {BASE_URL}: {e}")
            sys.exit(2)
        first_input_tokens = first_input_tokens or usage["prompt_tokens"]
        print(f"  step {step} ({time.time() - t0:.1f}s, input {usage['prompt_tokens']} tokens)")
        messages.append(reply)
        if not reply.get("tool_calls"):
            answer = (reply.get("content") or "").strip()
            print(f"    model answered : {answer!r}")
            return calls, answer, first_input_tokens
        for call in reply["tool_calls"]:
            name, raw = call["function"]["name"], call["function"]["arguments"] or "{}"
            print(f"    model asked    : {name}({raw})")
            try:
                args = json.loads(raw) if isinstance(raw, str) else raw
                result = as_tool_result(impls[name](**args))
            except Exception as e:
                result = f"{type(e).__name__}: {e}"
            print(f"    our code ran it: returned {result!r}")
            calls.append((name, raw, list(invoice_db.QUERIES)))
            invoice_db.QUERIES.clear()
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})
    return calls, f"(stopped: no answer within {max_steps} steps)", first_input_tokens


def main():
    p = argparse.ArgumentParser()
    p.add_argument("tool_file")
    p.add_argument("question", nargs="?")
    p.add_argument("--runs", type=int, default=1)
    p.add_argument("--system", default=SYSTEM)
    p.add_argument("--show", action="store_true", help="print the definitions and stop")
    p.add_argument("--max-steps", type=int, default=4)
    p.add_argument("--temperature", type=float)
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    funcs = load_tools(a.tool_file)
    definitions = [tool_definition(f) for f in funcs]
    print(f"=== what the model is sent about your tools ({a.tool_file}) ===")
    print(json.dumps(definitions, indent=2))
    print(f"(about {len(json.dumps(definitions)) // 4} tokens, sent again on every call of the loop)")
    if a.show:
        return
    if not a.question:
        p.error("a question is needed unless --show is given")
    print(f"\nmodel {MODEL} | system prompt {a.system!r}")
    print(f"user: {a.question!r}")

    opts = {"temperature": a.temperature} if a.temperature is not None else {}
    called = 0
    for i in range(1, a.runs + 1):
        print(f"\n--- run {i} of {a.runs} ---")
        calls, answer, tokens = run_once(a.question, a.system, funcs, definitions, opts, a.max_steps)
        called += bool(calls)
        print("  1. Did it call the tool?      " + ("YES: " + ", ".join(n for n, _, _ in calls) if calls else "NO"))
        if calls:
            for name, raw, queries in calls:
                seen = "; ".join(f"{q} -> {n} row(s)" for q, n in queries) or "no database query"
                print(f"  2. Did it call it correctly?  {name}({raw}) -> database saw: {seen}")
        else:
            print("  2. Did it call it correctly?  (nothing was called)")
        print(f"  3. Did it understand?         read the answer above aloud")
    print(f"\n>>> tool called in {called} of {a.runs} run(s)")


if __name__ == "__main__":
    main()
