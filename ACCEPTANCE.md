# UC1 — Grounded Answer Service: acceptance criteria

Written live, in front of the room, in session 2. The wording is the work: if
you cannot write it as a checkbox, you cannot claim it in a status meeting.

`tests/test_uc1_acceptance.py` is these five lines executed. If the two files
ever disagree, this file is wrong and the test file is right, because that one
runs.

The boxes are unticked on purpose. They get ticked when `pytest` goes green,
not before — session 3 builds retrieval, session 4 turns these green.

- [ ] **AC1 — Answers a question from the corpus with at least one citation.**

- [ ] **AC2 — Every citation resolves to a real passage in a real document.**

- [ ] **AC3 — A tenant never receives another tenant's content.**

- [ ] **AC4 — Says "not in the documents" when it is not in the documents.**

- [ ] **AC5 — Answers within the agreed latency ceiling.**

---

**Deliberately not criteria.** Nothing here says "gives good answers" — nobody
can test that. Answer quality as a *score* is RAGAS in session 4, and it is
measured rather than asserted. Latency percentiles, cost per answer, streaming
and concurrency are session 4's too.

**Provisional, and named as provisional.** The latency ceiling is 10 seconds
(`uc1_service.LATENCY_CEILING_SECONDS`). It is a "the thing is alive" number
chosen tonight so the criterion is testable at all, not a service level anybody
has agreed. Session 4 argues it properly.
