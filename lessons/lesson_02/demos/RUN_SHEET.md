# Lesson 02 — demo run sheet

Everything below was run end to end on 2026-11-22 against a real local
`qwen3:4b-instruct`. Nothing needed fixing. Full output is in
`structured_RUN_LOG.md`.

## Before the session

Run these two once, in this order. Both must pass.

| Check | Command | Expect |
|---|---|---|
| Model is up | `ollama list` | a row for `qwen3:4b-instruct` |
| Dependency | `python -c "import pydantic; print(pydantic.VERSION)"` | `2.11.x` |

If the model is missing: `ollama pull qwen3:4b-instruct`.
If pydantic is missing: `pip install -r requirements.txt`.

Start in this folder and stay there. All commands below are relative:

```
cd D:\rtc\trainings\training_agentic_ai_2026_batch_research\012_curriculum\lessons\lesson_02\demos
```

## The six commands, in teaching order

| # | Command | Time | The one point to make |
|---|---|---|---|
| 1 | `python structured.py prose invoices\inv_4471_sharma.txt` | ~8s | The reply is a `str`. `reply.amount` raises `AttributeError`. |
| 2 | `python structured.py extract invoices\inv_4472_sharma.txt` | ~4s | Same ask plus a schema. One line parses it. `date` is a real date. Cheaper and faster than prose. |
| 3 | `python structured.py batch invoices` | ~15s | 5 pass, 1 set aside. A retry fixes a typo (2062 to 2022) but cannot fix a wrong total. |
| 4 | `python structured.py batch invoices --max-tokens 40` | ~5s | `finish_reason=length`. Valid JSON prefix, no closing brace. The run stops itself at 3 of 3 failed. |
| 5 | `python structured.py function-vs-model system_invoices` | ~8s | Same answers. The model is ~32,000 times slower at 921 tokens. If I can write the function, I write the function. |
| 6 | `python structured.py classify messages.txt` | ~16s | Five Hinglish messages routed right, including the GST one that says "order". Judgement where a regex cannot go. |

## Two things to say honestly on the night

Run 4 overwrites `out\invoices.csv` with an empty file. The good CSV from run 3
is gone after it. Either show run 4 last, or rerun run 3 afterwards. The CSV in
`out\` right now holds the five good rows.

Run 5 shows one mismatch: the model returns tax `4320.000000000001` where the
function reads `4320.0`. It is a float artifact of the model recomputing a figure
the paper already states. Money belongs in `Decimal`.

## If something breaks live

| Symptom | Cause | Fix |
|---|---|---|
| `URLError` / connection refused | Ollama not running | start Ollama, then rerun |
| Every file `SET_ASIDE` on a shape error | wrong model picked up | `$env:AGENT_MODEL="qwen3:4b-instruct"` |
| First call takes 30s+ | model loading into memory | run command 2 once before the session to warm it |
| Wildly different token counts in run 6 | qwen3 thinks before it answers | expected; the schema bounds the answer, not the work |

## Knobs, if the room asks

`AGENT_BASE_URL`, `AGENT_MODEL`, `AGENT_API_KEY` as environment variables.
`batch` also takes `--retries`, `--stop-rate` and `--min-seen`.
