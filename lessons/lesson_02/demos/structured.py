"""Lesson 2 demos: structured output, and when not to use an agent.

One file. Talks to a real model through any OpenAI-compatible /chat/completions
endpoint (default: Ollama on this laptop). Needs pydantic, nothing else.

  python structured.py prose   invoices/inv_4471_sharma.txt
  python structured.py extract invoices/inv_4472_sharma.txt
  python structured.py batch   invoices
  python structured.py batch   invoices --max-tokens 40
  python structured.py function-vs-model system_invoices
  python structured.py classify messages.txt
"""
import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

BASE_URL = os.environ.get("AGENT_BASE_URL", "http://127.0.0.1:11434/v1")
MODEL = os.environ.get("AGENT_MODEL", "qwen3:4b-instruct")
API_KEY = os.environ.get("AGENT_API_KEY", "ollama")
HERE = Path(__file__).parent


# ---------------------------------------------------------------- the model call
def call_model(messages, schema=None, max_tokens=None):
    """One real HTTP call. Returns (content, finish_reason, refusal, usage, seconds)."""
    body = {"model": MODEL, "messages": messages, "temperature": 0}
    if schema is not None:  # THE CONTRACT TRAVELS WITH THE REQUEST
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": schema["title"], "schema": schema, "strict": True},
        }
    if max_tokens:
        body["max_tokens"] = max_tokens
    req = urllib.request.Request(
        BASE_URL.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"},
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read())
    seconds = time.perf_counter() - t0
    choice = data["choices"][0]
    msg = choice["message"]
    return msg.get("content") or "", choice.get("finish_reason"), msg.get("refusal"), data.get("usage", {}), seconds


# ---------------------------------------------------------------- the shape (layer 1)
class Invoice(BaseModel):
    """One supplier invoice. All amounts in rupees."""
    model_config = ConfigDict(extra="forbid")  # -> "additionalProperties": false

    supplier: str
    invoice_number: str
    date: dt.date
    subtotal: float   # taxable value, before tax
    tax: float        # GST / IGST amount
    amount: float     # total payable, including tax

    # ------------------------------------------------------------ the meaning (layer 2)
    # These rules are NOT in the schema sent to the model. They run in our code,
    # after the object comes back.
    @model_validator(mode="after")
    def business_rules(self):
        problems = []
        if self.amount <= 0:
            problems.append(f"amount must be positive, got {self.amount}")
        if not (0 <= self.tax < self.amount):
            problems.append(f"tax {self.tax} must be between 0 and the total {self.amount}")
        if self.date > dt.date.today():
            problems.append(f"date {self.date} is in the future")
        if abs(self.subtotal + self.tax - self.amount) > 1.0:
            problems.append(f"subtotal {self.subtotal} + tax {self.tax} = {self.subtotal + self.tax:.2f}, "
                            f"but amount is {self.amount}")
        if problems:
            raise ValueError("; ".join(problems))
        return self


SYSTEM = ("You read supplier invoices and fill in the given JSON schema. "
          "Amounts are plain numbers in rupees, no commas. Dates are YYYY-MM-DD.")


def ask_for_invoice(text):
    return [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": "Extract this invoice:\n\n" + text}]


def short(s, n=400):
    s = s.replace("\n", " ")
    return s if len(s) <= n else s[:n] + f"... [{len(s) - n} more chars]"


# ---------------------------------------------------------------- demo 1a: prose
def cmd_prose(args):
    text = Path(args.file).read_text(encoding="utf-8")
    messages = [{"role": "user", "content": "Read this invoice and tell me the supplier, invoice number, "
                                            "date, amount and tax.\n\n" + text}]
    content, finish, _, usage, secs = call_model(messages)
    print(f"model {MODEL} | no schema | {secs:.1f}s | tokens in {usage.get('prompt_tokens')} out {usage.get('completion_tokens')}")
    print("\n--- what came back (a string) ---")
    print(content)
    print("\n--- what the program can do with it ---")
    print(f"type(reply) = {type(content).__name__}")
    try:
        content.amount  # noqa: B018
    except AttributeError as e:
        print(f"reply.amount -> AttributeError: {e}")


# ---------------------------------------------------------------- demo 1b: extract
def cmd_extract(args):
    text = Path(args.file).read_text(encoding="utf-8")
    schema = Invoice.model_json_schema()
    print("--- the schema that travels with the request (from the Invoice class) ---")
    print(json.dumps(schema))
    content, finish, refusal, usage, secs = call_model(ask_for_invoice(text), schema)
    print(f"\nmodel {MODEL} | {secs:.1f}s | tokens in {usage.get('prompt_tokens')} out {usage.get('completion_tokens')} | finish_reason={finish}")
    print("\n--- what came back ---")
    print(content)
    invoice = Invoice.model_validate_json(content)   # the one line that replaces the parser
    print("\n--- invoice = Invoice.model_validate_json(reply) ---")
    print(repr(invoice))
    print(f"invoice.date.month         = {invoice.date.month}")
    print(f"invoice.subtotal * 0.18    = {invoice.subtotal * 0.18:.2f}")
    print(f"spreadsheet row            = {[invoice.supplier, invoice.invoice_number, invoice.date.isoformat(), invoice.amount, invoice.tax]}")


# ---------------------------------------------------------------- demo 2: the batch
def extract_with_policy(text, max_tokens, retries):
    """Returns (invoice or None, outcome, reason, calls, tokens)."""
    messages = ask_for_invoice(text)
    schema = Invoice.model_json_schema()
    calls = tokens = 0
    for attempt in range(retries + 1):
        content, finish, refusal, usage, secs = call_model(messages, schema, max_tokens)
        calls += 1
        tokens += usage.get("total_tokens", 0)
        print(f"    call {calls}: {secs:.1f}s, finish_reason={finish}, reply: {short(content, 160)}")
        # 1. why did it stop? check BEFORE reading the content
        if finish == "length":
            return None, "TRUNCATED", f"reply cut off at max_tokens={max_tokens}; nothing to validate", calls, tokens
        # 2. a refusal arrives in its own field, not as a broken answer
        if refusal:
            return None, "REFUSED", refusal, calls, tokens
        # 3. shape and meaning
        try:
            return Invoice.model_validate_json(content), "OK", "", calls, tokens
        except ValidationError as e:
            errors = "; ".join(f"{'.'.join(map(str, err['loc'])) or 'invoice'}: {err['msg']}" for err in e.errors())
            print(f"    validation failed: {errors}")
            if attempt < retries:
                # retry DIFFERENTLY: send the error back
                messages = messages + [
                    {"role": "assistant", "content": content},
                    {"role": "user", "content": f"Your JSON failed validation: {errors}. Return corrected JSON."},
                ]
            else:
                return None, "SET_ASIDE", errors, calls, tokens
    raise AssertionError("unreachable")


def cmd_batch(args):
    files = sorted(Path(args.dir).glob("*.txt"))
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    print(f"model {MODEL} | {len(files)} invoices | retries {args.retries} | max_tokens {args.max_tokens} | "
          f"stop if failure rate > {args.stop_rate:.0%} after {args.min_seen} invoices\n")
    rows, set_aside, seen, failed, total_calls, total_tokens = [], [], 0, 0, 0, 0
    for f in files:
        print(f"[{f.name}]")
        inv, outcome, reason, calls, tokens = extract_with_policy(f.read_text(encoding="utf-8"), args.max_tokens, args.retries)
        seen += 1
        total_calls += calls
        total_tokens += tokens
        if inv:
            rows.append([f.name, inv.supplier, inv.invoice_number, inv.date.isoformat(), inv.subtotal, inv.tax, inv.amount])
            print(f"  -> OK         {inv.supplier} | {inv.invoice_number} | {inv.date} | {inv.amount}")
        else:
            failed += 1
            set_aside.append([f.name, outcome, reason])
            print(f"  -> {outcome:<10} {reason}")
        if seen >= args.min_seen and failed / seen > args.stop_rate:
            print(f"\n!!! STOPPING THE RUN: {failed} of {seen} failed ({failed / seen:.0%}) > {args.stop_rate:.0%}. "
                  f"{len(files) - seen} invoices not attempted.")
            break
    with open(out / "invoices.csv", "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows([["file", "supplier", "invoice_number", "date", "subtotal", "tax", "amount"]] + rows)
    with open(out / "set_aside.csv", "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows([["file", "outcome", "reason"]] + set_aside)
    print(f"\n>>> {len(rows)} in the spreadsheet, {len(set_aside)} set aside for a human, "
          f"{len(files) - seen} not attempted | {total_calls} model calls, {total_tokens} tokens")
    print(f">>> wrote {out / 'invoices.csv'} and {out / 'set_aside.csv'}")


# ---------------------------------------------------------------- demo 3: function vs model
BOX = re.compile(
    r"\|\s*(?P<supplier>.+?)\s{2,}INVOICE NO:\s*(?P<number>\S+)\s*\|.*?"
    r"INVOICE DATE:\s*(?P<date>\d{4}-\d{2}-\d{2}).*?"
    r"TAXABLE VALUE:\s*(?P<subtotal>[\d.]+).*?GST 18%:\s*(?P<tax>[\d.]+).*?TOTAL PAYABLE:\s*(?P<amount>[\d.]+)",
    re.S)


def read_box(text):
    """The function. The layout never changes, so no judgement is needed."""
    m = BOX.search(text)
    return Invoice(supplier=m["supplier"], invoice_number=m["number"], date=m["date"],
                   subtotal=m["subtotal"], tax=m["tax"], amount=m["amount"])


def cmd_function_vs_model(args):
    files = sorted(Path(args.dir).glob("*.txt"))
    f_secs = m_secs = 0.0
    m_tokens = 0
    for f in files:
        text = f.read_text(encoding="utf-8")
        t0 = time.perf_counter()
        by_function = read_box(text)
        f_t = time.perf_counter() - t0
        content, finish, _, usage, m_t = call_model(ask_for_invoice(text), Invoice.model_json_schema())
        by_model = Invoice.model_validate_json(content)
        f_secs += f_t
        m_secs += m_t
        m_tokens += usage.get("total_tokens", 0)
        same = by_function == by_model
        print(f"[{f.name}]")
        print(f"  function : {f_t * 1000:8.3f} ms   0 tokens  {by_function.invoice_number} {by_function.date} {by_function.amount}")
        print(f"  model    : {m_t * 1000:8.0f} ms {usage.get('total_tokens', 0):>3} tokens  {by_model.invoice_number} {by_model.date} {by_model.amount}")
        if same:
            print("  same answer: True")
        else:
            diff = {k: (getattr(by_function, k), getattr(by_model, k))
                    for k in Invoice.model_fields if getattr(by_function, k) != getattr(by_model, k)}
            print(f"  same answer: False  (function, model) -> {diff}")
    print(f"\n>>> function total {f_secs * 1000:.3f} ms, 0 tokens | model total {m_secs:.1f} s, {m_tokens} tokens")
    if f_secs > 0:
        print(f">>> the model was about {m_secs / f_secs:,.0f} times slower")


# ---------------------------------------------------------------- demo 4: one bounded model call
class Triage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: Literal["complaint", "question", "order"]


def route(message):
    """A plain function. The order is fixed: receive, classify, route.
    Only the middle step needs judgement, so only the middle step calls the model."""
    content, finish, _, usage, secs = call_model(
        [{"role": "system", "content": "Classify the customer's WhatsApp message."},
         {"role": "user", "content": message}],
        Triage.model_json_schema())
    label = Triage.model_validate_json(content).label
    queue = {"complaint": "support-team", "question": "faq-bot", "order": "sales-desk"}[label]
    return label, queue, usage, secs, content


def cmd_classify(args):
    print("schema sent:", json.dumps(Triage.model_json_schema()), "\n")
    for line in Path(args.file).read_text(encoding="utf-8").splitlines():
        if line.strip():
            label, queue, usage, secs, raw = route(line.strip())
            print(f"{label:<10} -> {queue:<13} ({secs:.1f}s, in {usage.get('prompt_tokens')} out {usage.get('completion_tokens')} tokens, raw reply {len(raw)} chars)  {line.strip()}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("prose"); s.add_argument("file"); s.set_defaults(fn=cmd_prose)
    s = sub.add_parser("extract"); s.add_argument("file"); s.set_defaults(fn=cmd_extract)
    s = sub.add_parser("batch"); s.add_argument("dir")
    s.add_argument("--max-tokens", type=int, default=None)
    s.add_argument("--retries", type=int, default=1)
    s.add_argument("--stop-rate", type=float, default=0.5)
    s.add_argument("--min-seen", type=int, default=3)
    s.set_defaults(fn=cmd_batch)
    s = sub.add_parser("function-vs-model"); s.add_argument("dir"); s.set_defaults(fn=cmd_function_vs_model)
    s = sub.add_parser("classify"); s.add_argument("file"); s.set_defaults(fn=cmd_classify)
    args = p.parse_args()
    # Windows consoles default to cp1252, which cannot print the rupee sign the model likes to use.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        args.fn(args)
    except urllib.error.URLError as e:
        sys.exit(f"MODEL_ERROR: cannot reach {BASE_URL}: {e}. Is the model server running?")


if __name__ == "__main__":
    main()
