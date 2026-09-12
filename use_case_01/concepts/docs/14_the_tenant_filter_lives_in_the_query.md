# 14 — The tenant filter lives in the query

`../14_the_tenant_filter_lives_in_the_query.py`

## Summary

One table holds two teams' documents. The script embeds a Claims question and
runs the same vector search three times: once scoped to `claims`, once scoped to
`broker_support`, and once with the `WHERE` clause simply left out.

The two scoped searches return each team's own rows. The unscoped search returns
Claims' wording — to a query that, in the real service, would have been running
inside a Broker Support session.

```
  cross-tenant rows in that result: 2 -- no error, no log line, just Claims'
  wording in a Broker Support session.
```

That is the entire lesson, and it is about failure mode rather than mechanism.
The `WHERE` clause is trivial. What is not trivial is that omitting it produces
**no error, no warning and no log line** — just a plausible answer built from
another team's documents. The bug is invisible from the outside and it is a data
breach.

Hence: the filter belongs inside the SQL, in the same statement that does the
ranking, because that is the place nobody can forget to call.

## Prerequisite

```
docker compose -f ../demo/docker-compose.yml up -d
```

---

## Aspect by aspect

### 1. Two tenants, one table

```python
ROWS = [("claims", "01_escape_of_water.md", "4", "Escape of water from a neighbouring flat is covered. Excess GBP 350."),
        ("claims", "03_gradual_seepage.md", "1", "Damage from gradual seepage over weeks or months is excluded."),
        ("broker_support", "21_portal_errors.md", "2", "A pending mid-term adjustment blocks the quote; the portal shows NW-4471."),
        ("broker_support", "22_commission.md", "6", "Broker commission is settled monthly in arrears.")]
```

Shared-table multi-tenancy: one table, a `tenant_id` column, every row labelled.
It is the cheapest model to run and the one with the sharpest edge — the
isolation exists only in the queries, so it is only ever as good as the last
query somebody wrote. A table per tenant, or a schema per tenant, moves the
enforcement into the database at the cost of operational weight. Choosing shared
tables means accepting this script as the thing that can go wrong.

Note the corpora are genuinely different in subject. Claims rows are about water
damage; Broker Support rows are about portal errors and commission. So the
question is answerable for one team and not the other, and the correct behaviour
for Broker Support is to find nothing useful.

### 2. The question is legitimate

```python
QUESTION = "is water damage from the flat upstairs covered?"
```

Nothing adversarial. No prompt injection, no jailbreak, no attempt to escape a
sandbox. Someone in Broker Support asks an ordinary question, and the leak
happens because the query was written wrong — not because anyone attacked it.

That framing matters when teaching. The interesting multi-tenancy failures are
not attacks. They are ordinary queries against a missing predicate.

### 3. The two statements, side by side

```python
SCOPED = ("SELECT tenant_id, source_file, clause FROM concept_chunks WHERE tenant_id = %s"
          " ORDER BY embedding <=> %s::vector LIMIT 2")
FORGOTTEN = ("SELECT tenant_id, source_file, clause FROM concept_chunks"        # no WHERE clause at all
             " ORDER BY embedding <=> %s::vector LIMIT 2")
```

They are written adjacently on purpose. The difference is eleven characters.

`tenant_id` is included in the `SELECT` list so the printed output can be
audited — you can see which tenant every returned row belongs to. In a real
retrieval function you would not select it, and that is part of why the failure
is invisible: the leaked rows come back looking exactly like your own.

Crucially, the filter is in the **same statement** as the `ORDER BY`. That is not
a stylistic preference. Filtering after the fact — fetching the top 5 and then
discarding foreign rows in Python — gives a different and worse result: the
ranking ran over everybody's corpus, so your own best passages may have been
pushed out of the top 5 by another tenant's rows before you ever saw them. A
post-filter degrades relevance *and* leaves the leak one forgotten line away.

### 4. The demonstration

```python
for tenant in ("claims", "broker_support"):
    hits = conn.execute(SCOPED, (tenant, query)).fetchall()
    print(f"  asked as {tenant:<15} -> {[f'{t}:{f} §{c}' for t, f, c in hits]}")
```

Same question, same vector, same table, two different identities, two different
result sets. The identity is a *parameter to the query*, which is the whole
design: it cannot be defaulted, and there is no code path that runs the search
without supplying it.

```python
leak = conn.execute(FORGOTTEN, (query,)).fetchall()
print(f"  filter left to the caller -> {[f'{t}:{f} §{c}' for t, f, c in leak]}")
print(f"  cross-tenant rows in that result: {sum(1 for t, _, _ in leak if t != 'broker_support')}"
      " -- no error, no log line, just Claims' wording in a Broker Support session.")
```

"Filter left to the caller" is the phrase to dwell on. The unscoped query is not
*wrong* on its own terms — it is a general-purpose search that assumes somebody
downstream will scope it. Every such assumption is one refactor away from being
false, and there is no test that fails when it becomes false, because the query
still returns rows and the answer still reads well.

The count is computed against `broker_support`, the session that was notionally
asking. It comes out as 2 — both returned rows belong to Claims, because Claims
holds the rows that best match a water-damage question.

### 5. Where the identity comes from

The tenant is never inferred from the question, and never asked of the model. In
the shipping service it arrives on the `X-Northwind-Team` header, is validated
against the four known teams, and is bound into the search tool when the tool is
built — which is script 15, and is the same argument moved one layer up: if the
tenant is a parameter the model can fill in, the model can be talked into filling
it in wrongly.

So the chain is: HTTP header → validated tenant id → bound into the tool closure
→ `WHERE tenant_id = %s` in the SQL. At no point is it in the prompt, and at no
point can it be omitted.

---

## What to take away

- With shared-table multi-tenancy, the tenant filter is the isolation. There is
  nothing else.
- Put it in the same statement as the ranking. A post-filter both leaks and
  degrades relevance.
- The failure is silent — no exception, no log, a plausible answer. Assume it
  will not be caught by testing the happy path; test it directly, as
  `demo/04_cross_tenant.py` does.
- Identity comes from the transport layer, not from the question and not from the
  model.
- Never write a "search everything" helper and rely on callers to scope it.

## Related

- `11_pgvector_is_the_store.py` — where `tenant_id` entered the schema, on row
  one.
- `15_no_argument_in_which_to_ask.py` — the same boundary, at the tool signature.
- `demo/retrieval.py` — the scoped query in the service.
- `demo/04_cross_tenant.py`, `demo/test_acceptance.py` — the test that this
  cannot happen.
- `../run_logs/14_the_tenant_filter_lives_in_the_query_RUN_LOG.md` — recorded
  runs.
