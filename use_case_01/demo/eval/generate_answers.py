"""EVALUATION, step 1 of 2 -- answer the golden set.

Run FROM demo/, in the MAIN environment:

    uv run python eval/generate_answers.py
    uv run python eval/generate_answers.py --rerank off      (the 'before' run)

Generation and scoring are two scripts because they are two jobs that need two
different Python environments -- RAGAS pins an older LangChain stack than ADK
does, and forcing them into one virtualenv breaks ADK outright. That is an
ordinary, boring dependency fact, and it is much better said now than discovered
during the evaluation step with a room watching. See eval/README.md.

Output: eval/answers_rerank_on.json or eval/answers_rerank_off.json --
questions, answers, and the passages the agent was actually given. run_ragas.py
scores whichever file you point it at, and the two files are the before-and-after
of the reranker.
"""

import argparse
import asyncio
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import agent as agent_module  # noqa: E402
import config  # noqa: E402
import retrieval  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
GOLDEN_SET = HERE / "golden_set.json"


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rerank", choices=("on", "off"), default="on" if config.RERANK else "off")
    args = parser.parse_args()
    use_rerank = args.rerank == "on"

    config.banner(f"EVALUATION step 1 -- answering the golden set, reranker {args.rerank.upper()}")
    config.check_credentials()

    spec = json.loads(GOLDEN_SET.read_text(encoding="utf-8"))
    questions = spec["questions"]
    rows = []

    for index, item in enumerate(questions, start=1):
        tenant = item["tenant_id"]
        question = item["question"]
        print(f"[{index:>2}/{len(questions)}] [{tenant}] {question}")

        # The same retriever the tool uses, called again so we can record WHAT
        # the agent was given. Two searches instead of one: a small honest cost
        # for being able to score context precision at all.
        contexts = [
            hit["content"]
            for hit in retrieval.search(tenant, question, use_rerank=use_rerank)
        ]

        # The agent itself must answer under the same setting, or the two halves
        # of the row disagree about which system produced them.
        previous, config.RERANK = config.RERANK, use_rerank
        try:
            answer = await agent_module.answer(question, tenant_id=tenant, verbose=False)
        finally:
            config.RERANK = previous

        rows.append({
            "tenant_id": tenant,
            "question": question,
            "answer": answer.blocked or answer.text,
            "contexts": contexts,
            "reference": item["reference"],
            "expected_source_file": item["source_file"],
            "expected_clause": item["clause"],
            "cited": [{"source_file": f, "clause": c} for f, c in answer.citations],
            "blocked": answer.blocked,
        })

    out = HERE / f"answers_rerank_{args.rerank}.json"
    out.write_text(json.dumps({"rerank": args.rerank, "model": config.CHAT_MODEL, "rows": rows},
                              indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[eval] wrote {out}")

    exact = sum(
        1 for row in rows
        if any(c["source_file"] == row["expected_source_file"]
               and c["clause"] == row["expected_clause"] for c in row["cited"])
    )
    right_file = sum(
        1 for row in rows
        if any(c["source_file"] == row["expected_source_file"] for c in row["cited"])
    )
    print(f"[eval] {right_file}/{len(rows)} answers cite the right document.")
    print(f"[eval] {exact}/{len(rows)} cite the right CLAUSE of the right document.")
    print("[eval] That is a cheap sanity check, not a score. The score is step 2:")
    print("         .venv-eval/Scripts/python eval/run_ragas.py      (Windows)")
    print("         .venv-eval/bin/python eval/run_ragas.py          (macOS / Linux)")


if __name__ == "__main__":
    asyncio.run(main())
