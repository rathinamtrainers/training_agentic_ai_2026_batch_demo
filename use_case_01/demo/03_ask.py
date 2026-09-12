"""STEP 3 -- the agent answers, with the clause reference attached.

Run:  uv run python 03_ask.py
      uv run python 03_ask.py --tenant underwriting "will we write a 19 year old on a GTI"
      uv run python 03_ask.py --tier pro           (the same question, bigger model)

Three things happen on screen and the middle one is the point:

  1. the model does not answer -- it REQUESTS the tool;
  2. the runtime runs our Python, queries this tenant's rows and hands back
     passages;
  3. only then does the model write a sentence, and every claim in it carries
     [source_file §clause].

The citation is then opened, from the file on disk, and read out. A citation
nobody checks is decoration.

TOOL_DESCRIPTION=vague uv run python 03_ask.py  is the same demo with the tool's
docstring ruined on purpose. The agent stops calling the tool. The description
is not documentation -- it is the prompt.
"""

import argparse
import asyncio

import agent as agent_module
import config
import usage

DEFAULT_QUESTION = "Does our cover include an escape of water from a neighbouring flat?"


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant", choices=config.TENANTS, default=config.DEFAULT_TENANT)
    parser.add_argument("--tier", choices=("flash", "pro"), default="flash")
    parser.add_argument("question", nargs="*")
    args = parser.parse_args()

    question = " ".join(args.question) or DEFAULT_QUESTION
    config.check_credentials()

    config.banner(
        f"STEP 3 -- {config.TENANT_LABELS[args.tenant]} asks"
        f"   (model {config.model_for_tier(args.tier)}, tier {args.tier})"
    )

    answer = await agent_module.answer(question, tenant_id=args.tenant, tier=args.tier)

    if answer.blocked:
        print(f"\n  BLOCKED: {answer.blocked}")
        print("  Nothing reached the user. That is the guardrail doing its job.")
        return

    print(f"\nA: {answer.text}\n")

    print("Now open every citation, because that is the whole promise:")
    if not answer.citations:
        print("  (none -- and the answer got through, so read the refusal above)")
    for source_file, clause in answer.citations:
        passage = agent_module.open_citation(args.tenant, source_file, clause)
        first_line = (passage or "").strip().splitlines()[0] if passage else "DOES NOT RESOLVE"
        print(f"  {source_file} §{clause}  ->  corpus/{args.tenant}/{source_file}")
        print(f"      {first_line}")

    print(f"\n  {answer.tool_calls} tool call(s), {answer.elapsed_seconds:.1f}s")
    print(f"  {usage.report(answer.model, answer.prompt_tokens, answer.output_tokens)}")
    print(f"  {usage.budget_note()}")
    print("\nNext:  uv run python 04_cross_tenant.py")


if __name__ == "__main__":
    asyncio.run(main())
