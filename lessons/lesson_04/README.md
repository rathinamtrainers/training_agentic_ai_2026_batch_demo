# Lesson 4 — The same loop inside a framework
What this folder holds, and what it does not.
- `demos/` — the demonstrations shown in this lesson: 5 files,
  programs and the data they read. `demos.md` says what each one shows and in what order.
- The slides are **not here**. Every slide is a full-bleed picture, so one lesson's PDF
  runs to tens of megabytes and a course of them would be most of a gigabyte in a
  repository everybody clones. They are published to `020-Presentations` on the course
  site instead.
## Running the demos
One environment at the root of this repository serves every lesson. Use `uv`, never
bare `pip`:
```
uv venv --python 3.13
uv pip install -r requirements.txt
```
The slides are published in `020-Presentations` on the course site as `lesson-04-slides.pdf`.
_Copied from the course's research repository. Edits here are overwritten the next
time the lesson is delivered._