# Run log — 04_function_call_round_trip.py

## 2026-09-06 — first run from PyCharm

**Step** — Run `04_function_call_round_trip.py` from PyCharm.

**Command**

```
D:\rtc\trainings\training_agentic_ai_2026_batch_demo\.venv\Scripts\python.exe D:\rtc\trainings\training_agentic_ai_2026_batch_demo\use_case_01\concepts\04_function_call_round_trip.py
```

**Output**

```
MODEL REQUESTS TOOL > search_knowledge_base({'question': 'is escape of water from a neighbouring flat covered?'})
RUNTIME RETURNS     > {'passages': [{'source_file': '01_escape_of_water.md', 'clause': '4', 'content': 'Escape of water from a neighbouring flat is covered. Excess GBP 350.'}]}
MODEL ANSWERS       > Yes, escape of water from a neighbouring flat is covered, subject to an excess of £350.

Process finished with exit code 0
```

**Analysis**

The full round trip completed: text -> function_call -> function_response -> text.
The model did not answer from memory; it emitted a `function_call` for
`search_knowledge_base` with the question as argument. The local Python function
ran in our process and returned one passage. Only after that passage was appended
to `history` as a `function_response` did the model produce the final answer, and
the answer carries the excess figure that only the passage contained.

Environment notes for repeats:
- Interpreter used: `D:\rtc\trainings\training_agentic_ai_2026_batch_demo\.venv\Scripts\python.exe`
  (the repository-root venv, not `use_case_01\demo\.venv`). Both carry
  `google-genai` and `python-dotenv`.
- Credentials: `GENAI_BACKEND=vertex` in `use_case_01\demo\.env`, so the run uses
  Application Default Credentials. `gcloud auth application-default login` must be
  current or the run fails at `generate_content`.
- `GOOGLE_CLOUD_LOCATION=global` is required for `gemini-3.7-flash` on the Vertex
  path; a regional value returns 404 NOT_FOUND for that model.
- No working-directory dependency: the script resolves `.env` relative to its own
  file, so it runs correctly from any directory.

**Decides next** — nothing to fix. Ready to move on to
`05_the_docstring_is_the_interface.py`, which changes the tool description and
shows the model choosing differently.
