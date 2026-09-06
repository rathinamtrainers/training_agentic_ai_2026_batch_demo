# 11 — pgvector is the store

`../11_pgvector_is_the_store.py`

## Summary

Script 10 did cosine similarity in Python over four passages. This script puts
the same vectors in PostgreSQL and lets the database do it, in one `SELECT`.

It creates the `vector` extension, drops and rebuilds a `concept_chunks` table,
embeds four rows, inserts them, embeds the question, and runs an ordinary SQL
query with an `ORDER BY` on the `<=>` distance operator. The answer comes back as
rows.

The message is deliberately unexciting: **there is no vector database here.**
There is Postgres, the same Postgres that already holds your application data,
with an extension that adds a column type and a distance operator. Transactions,
joins, backups, `WHERE` clauses and the rest of SQL all keep working — including
the `WHERE tenant_id = %s` that script 14 turns into the security boundary.

It closes on the same limitation as script 10, now demonstrated in SQL:
`LIMIT 3` returns three rows whether or not any of them are relevant.

> LIMIT always returns LIMIT: a vector search has no way to say 'nothing here'.

## Prerequisite

This is the first script needing the database. Start it first:

```
docker compose -f ../demo/docker-compose.yml up -d
```

`POSTGRES_PASSWORD` is read as `os.environ['POSTGRES_PASSWORD']` — subscript, not
`.get()` — so a missing password raises `KeyError` immediately rather than
failing later with an authentication error. The compose file reads the same
variable, which is what keeps the container and the client in agreement.

---

## Aspect by aspect

### 1. Connecting

```python
conn = psycopg.connect(f"host={...} dbname={...} user={...} password={...} port={...}", autocommit=True)
```

`psycopg` 3, a plain libpq connection string built from the `.env`. Every
component has a sensible default except the password.

`autocommit=True` because this script is a demonstration, not a transaction. Each
statement lands as it runs, so a failure halfway leaves the table in a state you
can inspect.

### 2. Extension before registration — and the order matters

```python
conn.execute("CREATE EXTENSION IF NOT EXISTS vector")     # the type has to exist before psycopg is told about it
register_vector(conn)
```

Two different jobs that are easy to confuse.

`CREATE EXTENSION vector` is server-side: it teaches *Postgres* about the
`vector` type and the distance operators. `IF NOT EXISTS` makes it idempotent.

`register_vector(conn)` is client-side: it teaches *psycopg* how to adapt a
Python list into that type on the way in, and back on the way out. It does this
by looking the type up in the connected database — so if the extension does not
exist yet, this raises. Hence the comment, and hence the order.

The payoff is that a plain Python `list[float]` can be passed as a parameter with
no serialisation code anywhere in the script.

### 3. The schema

```python
conn.execute(f"""CREATE TABLE concept_chunks (id bigserial PRIMARY KEY, tenant_id text NOT NULL,
                 source_file text NOT NULL, clause text NOT NULL, content text NOT NULL,
                 embedding vector({DIMS}) NOT NULL)""")    # tenant_id and clause are here from row one
```

An ordinary table. `bigserial` id, four text columns, one `vector` column.

Two of those columns are the point of the comment. `tenant_id` is in the very
first schema anyone writes in this course, before there is any multi-tenancy to
speak of — because retrofitting a tenant column onto a populated table is a
migration, and forgetting it is a data breach (script 14). `clause`, with
`source_file`, is what makes a citation resolvable (scripts 09 and 16).

`vector({DIMS})` fixes the width at 768. Postgres enforces it: an insert of a
differently-sized vector is rejected. That is the third place `EMBEDDING_DIMS`
has to agree, and the only one that will tell you when it does not.

Note there is **no index**. With four rows, a sequential scan is correct and an
HNSW index would only add build time. Real corpora need one — and an approximate
index changes the results, which is a trade to make deliberately rather than by
default.

### 4. Ingest, batched and zipped

```python
for (tenant, file, clause, text), vector in zip(ROWS, embed([r[3] for r in ROWS], "RETRIEVAL_DOCUMENT")):
    conn.execute("INSERT INTO concept_chunks (tenant_id, source_file, clause, content, embedding)"
                 " VALUES (%s, %s, %s, %s, %s)", (tenant, file, clause, text, vector))
```

One embedding call for all four texts, then `zip` pairs each row with its vector
by position. The API returns embeddings in input order; that ordering is the only
thing joining a vector to its text, so nothing may be re-sorted in between.

`RETRIEVAL_DOCUMENT` on the way in, `RETRIEVAL_QUERY` on the way out — script 10.

The vector is passed as `%s` like any other parameter. That is `register_vector`
earning its keep.

### 5. The search

```python
hits = conn.execute(
    "SELECT source_file, clause, content, 1 - (embedding <=> %s::vector) FROM concept_chunks"
    " WHERE tenant_id = %s ORDER BY embedding <=> %s::vector ASC LIMIT 3",
    (query, "claims", query)).fetchall()
```

One statement, and every piece of it is ordinary SQL except one operator.

**`<=>` is cosine distance.** Small means similar. pgvector also offers `<->`
(L2) and `<#>` (negative inner product); the operator chosen must match the
index's operator class, when there is an index.

**`1 - (embedding <=> ...)` converts distance to similarity**, so the printed
number reads the same way as script 10's cosine: bigger is better. Distance
sorts ascending, similarity reads descending, and mixing the two up is the
classic pgvector bug.

**`ORDER BY ... ASC LIMIT 3`** is the entire search. No special API, no separate
query language.

**`WHERE tenant_id = %s`** sits in the same statement, and this is the structural
argument the whole use case rests on: the tenant filter is not a post-filter
applied to results, it is part of the query the ranking runs against. Script 14
shows what its absence looks like.

`%s::vector` casts the parameter explicitly. `register_vector` handles the
adaptation, and the cast removes any ambiguity for the planner.

The query vector is passed twice — once for the `SELECT` list, once for the
`ORDER BY` — because they are two separate placeholders. Postgres computes the
distance twice; on a real corpus you would compute it once in a subquery.

### 6. The closing demonstration

```python
total = conn.execute("SELECT count(*) FROM concept_chunks").fetchone()[0]
print(f"\n{total} rows in the table and 3 came back, the last of them scoring {hits[-1][3]:.3f}:")
print(f"  {hits[-1][2]}")
print("LIMIT always returns LIMIT: a vector search has no way to say 'nothing here'.")
```

Four rows in, three out — and the third is about complaint timescales or the
standard buildings excess, with a real similarity score, in response to a
question about water through the ceiling.

The database did nothing wrong. It was asked for the three nearest and it
returned the three nearest. Relevance is not a concept it has. That gap is filled
by the reranker floor in script 13.

(The `SELECT count(*)` line appears twice in the source — the second call
overwrites the first with the same value. Harmless duplication.)

---

## What to take away

- pgvector is a column type and a distance operator inside a database you already
  run. It is not a separate system.
- `CREATE EXTENSION` first, then `register_vector` — server side before client
  side.
- Put `tenant_id`, `source_file` and `clause` in the schema from the first
  migration. Two of them make citation possible; one of them is the security
  boundary.
- `<=>` is distance: smaller is closer. Convert to similarity for display, and
  keep the two straight.
- The tenant filter belongs in the same `WHERE` clause the ranking runs against.
- `LIMIT 3` returns 3. Always.

## Related

- `10_embeddings_and_the_task_type.py` — the same cosine, done in Python.
- `12_hybrid_search_and_rrf.py` — adding lexical search to the same table.
- `14_the_tenant_filter_lives_in_the_query.py` — what the `WHERE` clause is for.
- `demo/db.py`, `demo/db/`, `demo/01_ingest.py` — the shipping schema and ingest.
- `../run_logs/11_pgvector_is_the_store_RUN_LOG.md` — recorded runs.
