# run_logs

Run logs for the numbered concept scripts in `use_case_01/concepts/`.

Each runnable script has its own log file, named after the script with a
`_RUN_LOG.md` suffix — running `04_function_call_round_trip.py` appends to
`04_function_call_round_trip_RUN_LOG.md` here.

Every entry is dated and records three things: the step (its title and the exact
command), the output that command produced, and a short analysis of what the
output means and what it decides next. Entries are appended, never overwritten,
so a file is the full history of that script across sessions.

These logs are handwritten records of real runs. Nothing here is generated, and
nothing regenerates them.
