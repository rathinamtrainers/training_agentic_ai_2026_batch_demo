"""DEPLOY, second half -- call the DEPLOYED agent and open its citation.

Run FROM demo/:   uv run python deployment/call_remote.py
                  uv run python deployment/call_remote.py "your own question"

Nothing on this laptop answers here. The question goes to Agent Runtime, the
deployed agent queries the database from inside Google's network, and the answer
comes back with a clause reference. The trainer then opens that clause, on
screen, from the corpus. That check is the protected moment: it is the whole
promise of the use case, demonstrated on the other side of a wire.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import config  # noqa: E402
import corpus  # noqa: E402
import guardrails  # noqa: E402

QUESTION = "Does our cover include an escape of water from a neighbouring flat?"


def main() -> None:
    config.banner("THE DEPLOYED SERVICE ANSWERS")

    if config.BACKEND != "vertex":
        print("[remote] GENAI_BACKEND must be 'vertex' to reach Agent Runtime.")
        sys.exit(1)

    question = " ".join(sys.argv[1:]) or QUESTION
    resource_name = config.agent_engine_id()

    import vertexai
    from vertexai import agent_engines

    vertexai.init(project=config.project(), location=config.LOCATION)
    remote = agent_engines.get(resource_name)

    print(f"[remote] {resource_name}")
    print(f"[remote] nothing on this laptop is answering.\n")
    print(f"Q: {question}\n")

    answer = ""
    for event in remote.stream_query(user_id="uc1_demo", message=question):
        for part in (event.get("content") or {}).get("parts", []):
            if part.get("function_call"):
                print(f"  [tool call, in the cloud] {part['function_call'].get('name')}")
            if part.get("text"):
                answer += part["text"]

    print(f"\nA: {answer.strip()}\n")

    tenant = config.DEFAULT_TENANT
    cited = guardrails.citations_in(answer)
    if not cited:
        print("[check] no citation in that answer. Say so out loud; do not move on quietly.")
    for source_file, clause in cited:
        passage = corpus.resolve(tenant, source_file, clause)
        status = "opens" if passage else "DOES NOT RESOLVE"
        print(f"[check] {source_file} §{clause} -> {status}"
              f"   corpus/{tenant}/{source_file}")
        if passage:
            print(f"        {passage.strip().splitlines()[0]}")

    print("\n[remote] Telemetry: the deployed agent was created with tracing enabled and")
    print("         GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY set, so this call is in")
    print("         Cloud Trace and its gen_ai metrics are in Cloud Monitoring. Open them")
    print("         next to this terminal -- reading a trace back off the cloud is the")
    print("         point of having deployed at all.")


if __name__ == "__main__":
    main()
