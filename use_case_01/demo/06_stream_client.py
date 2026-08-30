"""STEP 5, second half -- a client that watches the stream arrive.

Run (with 05_serve.py running in another terminal):

    uv run python 06_stream_client.py
    uv run python 06_stream_client.py --team complaints "how long do we have to send a final response"

Standard library only -- no HTTP client dependency, because the point is the
wire, not the library. Each server-sent event is printed the instant it lands,
so the room sees the tool call arrive before the first word of the answer does.
"""

import argparse
import json
import urllib.request

import config

DEFAULT_QUESTION = "Does our cover include an escape of water from a neighbouring flat?"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--team", choices=config.TENANTS, default="claims")
    parser.add_argument("--url", default=f"http://localhost:{config.optional('PORT', '8080')}")
    parser.add_argument("question", nargs="*")
    args = parser.parse_args()

    question = " ".join(args.question) or DEFAULT_QUESTION
    body = json.dumps({"question": question}).encode()

    request = urllib.request.Request(
        f"{args.url}/ask/stream",
        data=body,
        headers={
            "Content-Type": "application/json",
            # The tenant. In the header, where identity lives.
            "X-Northwind-Team": args.team,
        },
    )

    config.banner(f"streaming from {args.url}/ask/stream as {config.TENANT_LABELS[args.team]}")
    print(f"Q: {question}\n")

    kind = None
    with urllib.request.urlopen(request) as response:
        for raw in response:
            line = raw.decode("utf-8").rstrip("\n")
            if line.startswith("event: "):
                kind = line.removeprefix("event: ")
            elif line.startswith("data: "):
                payload = json.loads(line.removeprefix("data: "))
                if kind == "text":
                    print(payload["text"], end="", flush=True)
                elif kind == "tool_call":
                    print(f"[tool call: {payload['name']}({payload['args']})]")
                elif kind == "tool_result":
                    print(f"[{payload['passages']} passages came back]\n")
                elif kind == "usage":
                    pass  # printed once at the end, in the done event
                elif kind == "done":
                    print(f"\n\n[done] {payload}")
                else:
                    print(f"\n[{kind}] {payload}")


if __name__ == "__main__":
    main()
