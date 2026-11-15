"""Lesson 1 demo: the agent loop, written by hand. Python standard library only.

Talks to any OpenAI-compatible chat endpoint. Default: Ollama on this machine.
    AGENT_BASE_URL  default http://127.0.0.1:11434/v1
    AGENT_MODEL     default qwen3:4b-instruct
    AGENT_API_KEY   default "ollama" (Ollama ignores it; a hosted provider needs a real one)

    python invoice_agent.py trace                      # Demo 1: one turn, traced
    python invoice_agent.py runaway                    # Demo 2: the step cap fires
    python invoice_agent.py budget                     # Demo 2: the token budget refuses
    python invoice_agent.py repeat 3                   # Demo 3: same question, three runs
    python invoice_agent.py repeat 3 --temperature 0 --seed 42
    python invoice_agent.py repeat 3 --invoice 4480    # Demo 3: the hard fact (unpaid)
"""
import argparse, csv, getpass, json, os, re, sys, time, urllib.request
from pathlib import Path

BASE_URL = os.environ.get("AGENT_BASE_URL", "http://127.0.0.1:11434/v1")
MODEL = os.environ.get("AGENT_MODEL", "qwen3:4b-instruct")
API_KEY = os.environ.get("AGENT_API_KEY", "ollama")
HERE = Path(__file__).resolve().parent
SYSTEM = "You are a finance assistant for the accounts team. Use the tools to answer."


def call_model(messages, tools, options):
    """One HTTPS/HTTP call to the model. Returns the reply message and the token usage."""
    body = {"model": MODEL, "messages": messages, "tools": tools, **options}
    req = urllib.request.Request(f"{BASE_URL}/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {API_KEY}"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"], data["usage"]


def estimate_tokens(messages, tools):
    """Rough count BEFORE sending: about 4 characters per token. A provider's token counter is better."""
    return len(json.dumps(messages)) // 4 + len(json.dumps(tools)) // 4


# ---------------------------------------------------------------- THE LOOP
def run_agent(question, tools, impls, max_steps=10, token_budget=20_000, options=None):
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]
    spent, path = 0, []
    for step in range(1, max_steps + 1):                           # LIMIT 2: the step cap
        about_to_send = estimate_tokens(messages, tools)
        if spent + about_to_send > token_budget:                    # LIMIT 3: budget, checked BEFORE
            return finish("BUDGET", f"refused step {step}: {spent} spent + ~{about_to_send} "
                          f"about to send > budget {token_budget}", step - 1, spent, path)
        try:
            reply, usage = call_model(messages, tools, options or {})
        except OSError as e:                                        # network or server failure
            return finish("MODEL_ERROR", f"model call failed at step {step}: {e}", step - 1, spent, path)
        spent += usage["prompt_tokens"] + usage["completion_tokens"]
        show_call(step, messages, reply, usage, spent)
        messages.append(reply)
        if not reply.get("tool_calls"):                             # LIMIT 1: the stop condition
            return finish("ANSWERED", reply.get("content", ""), step, spent, path)
        for call in reply["tool_calls"]:                            # the model ASKED; our code ACTS
            name, args = call["function"]["name"], json.loads(call["function"]["arguments"] or "{}")
            try:
                result = impls[name](**args)
            except Exception as e:                                  # a bad call goes back as a result
                result = json.dumps({"error": f"{type(e).__name__}: {e}"})
            path.append((name, args))
            show_tool(name, args, result)
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})
    return finish("STEP_CAP", f"agent did not finish within {max_steps} steps", max_steps, spent, path)
# ---------------------------------------------------------------- END OF THE LOOP


# ---- tools: plain functions, run by this process, with this process's rights
def load_invoices():
    with open(HERE / "invoices.csv", newline="") as f:
        return {int(r["invoice_number"]): r for r in csv.DictReader(f)}


def lookup_invoice(invoice_number):
    rows = load_invoices()                                          # the whole file is readable
    row = rows.get(int(invoice_number))
    return json.dumps(row) if row else json.dumps({"error": f"invoice {invoice_number} not found"})


def check_settlement(invoice_number):
    """A polling API that never reaches a final state. Every call is real; it just never settles."""
    return json.dumps({"invoice_number": int(invoice_number), "settlement": "IN_PROGRESS",
                       "final": False, "detail": "bank confirmation not yet received"})


def read_server_log(server):
    """Returns a real 40,000-line log, generated here, the way a careless log tool would."""
    lines = [f"2026-03-12T02:{(i // 60) % 60:02d}:{i % 60:02d}Z {server} export-job INFO "
             f"batch={i} rows=250 status=ok" for i in range(40_000)]
    lines[39_000] = f"2026-03-12T04:30:00Z {server} export-job ERROR disk full on /var/export"
    return "\n".join(lines)


def schema(name, description, param, ptype, pdesc):
    return {"type": "function", "function": {"name": name, "description": description,
            "parameters": {"type": "object", "properties": {param: {"type": ptype, "description": pdesc}},
                           "required": [param]}}}


LOOKUP = schema("lookup_invoice", "Look up one invoice in the finance database by its number. "
                "Returns customer, amount, status (paid/unpaid), paid_on date and payment reference.",
                "invoice_number", "integer", "The invoice number, e.g. 4471")
SETTLE = schema("check_settlement", "Check whether the bank has finally settled the payment for an "
                "invoice. Only report the invoice as settled once this returns final=true.",
                "invoice_number", "integer", "The invoice number")
LOG = schema("read_server_log", "Read the full export-job log of a server.",
             "server", "string", "Server name, e.g. fin-export-01")


# ---- printing the trace: the five questions of objective 1.1
def show_call(step, messages, reply, usage, spent):
    print(f"\n=== step {step}: call to the model ({MODEL} at {BASE_URL}) ===")
    print(f"  sent        : {len(messages)} messages, roles {[m['role'] for m in messages]}")
    print(f"  cost        : input {usage['prompt_tokens']} tokens, output {usage['completion_tokens']} tokens"
          f"   (run total so far: {spent})")
    if reply.get("tool_calls"):
        for c in reply["tool_calls"]:
            print(f"  model asked : {c['function']['name']}({c['function']['arguments']})"
                  f"   <- the model decided; nothing has run yet")
    else:
        print(f"  model said  : {reply.get('content', '').strip()!r}   <- no tool request: stop")


def show_tool(name, args, result):
    print(f"  --- our code runs {name}({args}) ---")
    print(f"  credentials : OS user '{getpass.getuser()}', pid {os.getpid()} - this process's rights,"
          f" not the model's")
    if name == "lookup_invoice":
        print(f"  reach       : this account can read all {len(load_invoices())} invoices in invoices.csv;"
              f" the model named 1")
    shown = result if len(result) < 300 else result[:150] + f" ... [{len(result):,} characters]"
    print(f"  result      : {shown}")


def finish(outcome, text, steps, spent, path):
    return {"outcome": outcome, "text": text, "steps": steps, "tokens": spent, "path": path}


def summary(r):
    print(f"\n>>> outcome: {r['outcome']}   steps: {r['steps']}   tokens this run: {r['tokens']}")
    print(f">>> tools run: {r['path']}")
    print(f">>> {r['text']}")


def check_facts(r, invoice, unpaid, max_steps, budget):
    """Assert the facts and the path, never the sentence."""
    t = r["text"].lower()
    checks = {
        f"called lookup_invoice with {invoice}": any(n == "lookup_invoice" and str(a.get("invoice_number")) == str(invoice)
                                                    for n, a in r["path"]),
        "touched no other tool": all(n == "lookup_invoice" for n, _ in r["path"]),
        f"finished inside {max_steps} steps": r["outcome"] == "ANSWERED" and r["steps"] <= max_steps,
        f"inside {budget} tokens": r["tokens"] <= budget,
    }
    if unpaid:
        checks["never says it was paid"] = bool(re.search(r"not (been |yet )?paid|unpaid|outstanding", t))
    else:
        checks["says it was paid"] = "paid" in t and not re.search(r"not (been |yet )?paid|unpaid", t)
        checks["gives the date 12 March"] = bool(re.search(r"\b12(th)?\b.*march|march\s+12|2026-03-12|12/03|03/12", t))
    return checks


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["trace", "runaway", "budget", "repeat"])
    p.add_argument("times", nargs="?", type=int, default=3)
    p.add_argument("--invoice", type=int, default=4471)
    p.add_argument("--max-steps", type=int, default=10)
    p.add_argument("--budget", type=int, default=20_000)
    p.add_argument("--temperature", type=float)
    p.add_argument("--seed", type=int)
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    opts = {k: v for k, v in (("temperature", a.temperature), ("seed", a.seed)) if v is not None}
    print(f"model {MODEL} | endpoint {BASE_URL} | step cap {a.max_steps} | budget {a.budget} tokens"
          f" | sampling {opts or 'model default'}")

    if a.mode == "trace":
        r = run_agent(f"Has invoice {a.invoice} been paid?", [LOOKUP], {"lookup_invoice": lookup_invoice},
                      a.max_steps, a.budget, opts)
        summary(r)
    elif a.mode == "runaway":
        r = run_agent("On what date did the bank settle the payment for invoice 4471? "
                      "Keep checking until the settlement is final.", [SETTLE],
                      {"check_settlement": check_settlement}, a.max_steps, a.budget, opts)
        summary(r)
    elif a.mode == "budget":
        r = run_agent("Why did last night's invoice export fail on server fin-export-01? Check its log.",
                      [LOG], {"read_server_log": read_server_log}, a.max_steps, a.budget, opts)
        summary(r)
    else:
        unpaid = load_invoices()[a.invoice]["status"] == "unpaid"
        results = []
        for i in range(1, a.times + 1):
            print(f"\n################ run {i} of {a.times} ################")
            t0 = time.time()
            r = run_agent(f"Has invoice {a.invoice} been paid?", [LOOKUP], {"lookup_invoice": lookup_invoice},
                          a.max_steps, a.budget, opts)
            summary(r)
            print(f">>> {time.time() - t0:.1f} s")
            results.append(r)
        print("\n================ the three sentences ================")
        for i, r in enumerate(results, 1):
            print(f"run {i}: {r['text'].strip()!r}")
        print(f"identical strings: {len({r['text'].strip() for r in results}) == 1}")
        print("\n================ the facts and the path ================")
        failed = 0
        for i, r in enumerate(results, 1):
            for name, ok in check_facts(r, a.invoice, unpaid, a.max_steps, a.budget).items():
                failed += not ok
                print(f"run {i}: {'PASS' if ok else 'FAIL'}  {name}")
        sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
