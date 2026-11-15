# Parts — Lesson 1 demo talk, "The agent loop, written by hand"

| Part | Starts at | Title | Picture |
|------|-----------|-------|---------|
| 1 | 1 | One file, one laptop | A plain laptop on a desk showing a single Python file beside a small data file of 12 invoices, with a tag reading "standard library only, model running on this machine". |
| 2 | 4 | Who decided | A trace panel: a system and a user message leaving the program on the left, and a reply on the right holding only a request to look up an invoice, with the reply marked "asked, not run". |
| 3 | 6 | Whose rights it ran with | Our own function running inside the program's box, labelled with the OS user account and process id, and a separate empty slot beside the model marked "no credential"; a reach bar showing all 12 invoices readable, 1 named. |
| 4 | 8 | The second trip, and the stop | Two side-by-side message stacks, one of 2 messages and one of 4 including the invoice record, with the growing input count; beside them a reply with no tool request and a switch flipping the loop to "return". |
| 5 | 10 | What the model ever receives | A single opened envelope labelled with the request body, holding only a list of messages and a list of tool descriptions, with a password, a file and a database connection shown outside it, uncollected. |
| 6 | 11 | Where the tokens went | A simple bar for one run: a tall input bar sent twice and a short output bar, with the run total beside it and a note that a hosted model multiplies the same shape by a price list. |
| 7 | 13 | Forty lines, three limits | A stylised code block from "THE LOOP" to "END OF THE LOOP" with three lines highlighted and labelled: the step cap, the budget checked before, and the stop condition. |
| 8 | 15 | Breaking it on purpose | A polling tool drawn as a loop that keeps returning "IN_PROGRESS", the model asking again and again, and the stop condition shown greyed out because it only fires on success. |
| 9 | 17 | A readable failure | Three steps in a row with the input count climbing and the output count flat, ending in a calm one-line outcome card reading step cap reached, with no crash or alarm icon. |
| 10 | 19 | The instinct that cannot help | A trainer's hand reaching to edit the stop condition line, which is stamped "already perfect", while a separate counter dial is the only thing shown able to end the run. |
| 11 | 21 | The log that was never sent | A tool in the file building a very long server log, with the default step cap of 10 shown on the first line of the run and a single step about to start. |
| 12 | 23 | Refused before it spent | A huge block of log text held at a closed gate marked with the budget, the estimated token count written on it, and an arrow turned back so nothing leaves the laptop; beside it two separate dials, count and size. |
| 13 | 25 | Checked before, not regretted | A small flow: take the estimate, compare it to the budget, return — all before the box labelled "call the model"; two margin notes, one saying the estimate is about four characters to a token, one saying a hosted model bills every input token it accepts. |
| 14 | 27 | Three runs, three sentences | Three speech bubbles about the same invoice, same facts, different wording and date format, under a banner reading "same code, nothing changed", with a footer line "identical strings: False". |
| 15 | 30 | Turning it off, and the small print | The same three bubbles now identical, marked "identical strings: True", beside a fenced-off area showing one laptop, one user, one unchanging model file, with shared hardware and a future model update drawn outside the fence. |
| 16 | 32 | The facts and the path | Three columns, one per run, each with the same set of PASS lines beneath a different sentence, and a code panel for the fact checker showing the tool name, the outcome, the step and token totals and the date in any format — none of it comparing the sentence. |
| 17 | 35 | The check I would put in first | A run on an unpaid invoice with three different sentences above a single check reading "never says it was paid", passing on all three, and a note that a failure here is the agent being wrong, not a flaky test. |
| 18 | 37 | What it could not give me | A closing summary of one file, one loop and four runs — a traced turn, a run stopped by the counter, a run refused before it spent, three runs agreeing on facts — beside a human-readable sentence being searched by a pattern for a date and an empty database row with a question mark. |

## Notes for the trainer

The talk has 38 paragraphs and I cut it into 18 parts.

Two places were genuinely hard. Paragraph 3 carries both the "one file on a laptop" setting and the first trace line with the two limits; I kept it with the opening, because the limits come back properly in part 7. Paragraph 19 and 20 are two honest asides at once — that the model does not always keep polling, and that a better stop condition cannot save you — and they share a picture only loosely. If you want a cleaner cut, 19 can move up into part 9.

Paragraph 36 closes the unpaid-invoice run and also makes the wider point about failing checks, so part 17 carries a little more than one beat. The close (37 and 38) is its own part.
