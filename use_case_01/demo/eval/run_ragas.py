"""EVALUATION, step 2 of 2 -- retrieval quality becomes a number.

Run FROM demo/, in the EVAL virtualenv:

    .venv-eval/Scripts/python eval/run_ragas.py                     (Windows)
    .venv-eval/bin/python eval/run_ragas.py                         (macOS / Linux)
    .venv-eval/bin/python eval/run_ragas.py --answers eval/answers_rerank_off.json

Three metrics, and each one asks a different question:

  faithfulness        is the answer supported by the passages it was given?
                      This is the anti-hallucination number.
  answer relevancy    does the answer address the question that was asked?
  context precision   did the retriever put the useful passage near the top?
                      This one grades RETRIEVAL, not the model. It is the number
                      that moves when the reranker goes on.

Say the caveat out loud before the number lands: **an LLM is scoring an LLM.**
The judge has its own biases -- it prefers fluent answers, it prefers longer
ones, and it shares the family and the failure modes of the thing it is
grading. Twelve questions cannot see past that. This is a smoke alarm, not a
grade.

**This step needs a Google Cloud project.** RAGAS 0.2.15's judge here is
`langchain-google-vertexai`, which authenticates with Application Default
Credentials and has no API-key path. Everything else in this demo runs on a free
AI Studio key; this one does not, and eval/README.md says so plainly.
"""

import argparse
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import config  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--answers", default=str(HERE / "answers_rerank_on.json"))
    args = parser.parse_args()

    config.banner("EVALUATION step 2 -- RAGAS scores the golden set")

    answers_path = pathlib.Path(args.answers)
    if not answers_path.is_file():
        print(f"[ragas] {answers_path} is not there.")
        print("[ragas] Run step 1 first, in the MAIN environment:")
        print("          uv run python eval/generate_answers.py")
        sys.exit(1)

    if config.BACKEND != "vertex":
        print("[ragas] GENAI_BACKEND is 'api_key', and the RAGAS judge here cannot use one.")
        print("[ragas] Set GENAI_BACKEND=vertex and GOOGLE_CLOUD_PROJECT in .env, and run")
        print("[ragas]   gcloud auth application-default login")
        print("[ragas] See eval/README.md -- this is the one step that needs a cloud account.")
        sys.exit(1)

    from langchain_google_vertexai import ChatVertexAI, VertexAIEmbeddings
    from ragas import EvaluationDataset, SingleTurnSample, evaluate
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import (
        Faithfulness,
        LLMContextPrecisionWithReference,
        ResponseRelevancy,
    )

    data = json.loads(answers_path.read_text(encoding="utf-8"))
    rows = data["rows"]
    print(f"[ragas] scoring {len(rows)} answers from {answers_path.name}")
    print(f"[ragas] reranker was {data.get('rerank', 'unknown').upper()} when these were generated")
    print(f"[ragas] judge model: {config.CHAT_MODEL}   (an LLM grading an LLM)\n")

    dataset = EvaluationDataset(samples=[
        SingleTurnSample(
            user_input=row["question"],
            response=row["answer"],
            retrieved_contexts=row["contexts"],
            reference=row["reference"],
        )
        for row in rows
    ])

    project = config.project()
    judge = LangchainLLMWrapper(ChatVertexAI(
        model_name=config.CHAT_MODEL, project=project, location=config.LOCATION,
    ))
    judge_embeddings = LangchainEmbeddingsWrapper(VertexAIEmbeddings(
        model_name=config.EMBEDDING_MODEL, project=project, location=config.LOCATION,
    ))

    metrics = [
        Faithfulness(llm=judge),
        ResponseRelevancy(llm=judge, embeddings=judge_embeddings),
        LLMContextPrecisionWithReference(llm=judge),
    ]
    result = evaluate(dataset=dataset, metrics=metrics)

    # Averaged off the per-question frame rather than the summary object, so the
    # per-question numbers are there to talk about when one of them is odd.
    frame = result.to_pandas()
    scores = {
        metric.name: round(float(frame[metric.name].mean(skipna=True)), 4)
        for metric in metrics
        if metric.name in frame.columns
    }

    print("\n" + "=" * 72)
    for name, value in scores.items():
        print(f"  {name:<30} {value:.3f}")
    print("=" * 72)

    out = HERE / f"score_rerank_{data.get('rerank', 'unknown')}.json"
    out.write_text(json.dumps({
        "answers_file": answers_path.name,
        "rerank": data.get("rerank"),
        "questions": len(rows),
        "judge_model": config.CHAT_MODEL,
        "scores": scores,
    }, indent=2), encoding="utf-8")
    print(f"\n[ragas] wrote {out}")
    print("[ragas] Run it once with the reranker on and once with it off, and put the")
    print("        two score files side by side. That comparison is the whole point.")

    print("\n[ragas] Now the caveat, and do not skip it:")
    print("        An LLM scored an LLM, over twelve questions, on a corpus we wrote.")
    print("        It prefers fluent answers and it shares the failure modes of the")
    print("        thing it is grading. This is a smoke alarm, not a grade.")


if __name__ == "__main__":
    main()
