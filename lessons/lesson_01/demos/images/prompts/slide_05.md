Full Speech: That was the story. Here is the same turn, for real, on this laptop. One file on the screen, `invoice_agent.py`. No framework, no library to install, nothing but the Python standard library and a small model running on this machine. The invoice data is a file of 12 invoices sitting beside it.

I am going to type one command and then stop talking for a moment, because the model is small and this is a plain CPU. The trace that comes out is long, and I want you to watch the labels on the left rather than the words on the right.

So, `python invoice_agent.py trace`. Watch the first line that appears: the model name, the endpoint, the step cap of 10, and the budget of 20000 tokens. Those two limits were already in the program before the first call. They are not something I added after a bad bill.

Now look at `=== step 1`, and under it the line that says `sent : 2 messages, roles ['system', 'user']`. That is who decided. My program picked the model, wrote the instructions and offered the tools. The model has said nothing at all yet, and it has already cost 214 input tokens.

The next line is the whole lesson in one place. `model asked : lookup_invoice({"invoice_number":4471})`. Look at the comment next to it: the model decided, and nothing has run. That is a request sitting in a reply. It is the single moment where the model is in charge, and all it did was ask.

Then the line below it, `--- our code runs lookup_invoice(...)`. That is my function, in my process. Under it, `credentials : OS user`, with the account name and the process id. That is whose rights the query ran with. Nowhere on this screen does the model have a credential of any kind.

And the line I care about most on this run is `reach`. It says this account can read all 12 invoices in the file, and the model named 1. That is the hard question from earlier, printed by the program itself. The model's reach was my reach. It chose to use a small part of it.

Now `=== step 2`. Look at the roles on the `sent` line: `['system', 'user', 'assistant', 'tool']`. 4 messages, where there were 2. The whole conversation, including the invoice record, went back over the network. Watch the input number on that line: 317, where step 1 sent 214.

And there, `model said`, with no tool request beside it. That is the stop condition firing. The loop did not read those words or judge them. It checked whether a tool request was present, found none, and returned.

Let me show you the one line that makes all of this safe. I am opening the file at line 27. `body = {"model": MODEL, "messages": messages, "tools": tools, **options}`. That dictionary is everything the model ever receives on this run. No password. No file. No database connection. A list of messages and a list of tool descriptions.

Now the bottom of the output, and this is where I expect you to be surprised. `outcome: ANSWERED, steps: 2, tokens this run: 612`. The sentence on the screen cost about 57 output tokens. The run cost 612. So most of what you paid for was input that we sent twice. That whole turn took 17 seconds here.

This model is local, so no money moved. The token counts are the real ones the endpoint reported, and on a hosted model you multiply them by the price list. The shape does not change. The second trip is always the bigger one.

Right. If that is one turn, here is the loop that produced it. I am scrolling to line 41, where the comment says `THE LOOP`. From there to `END OF THE LOOP` is 29 lines. Add the model call above it and you have about 40. That is the whole agent.

Read down it with me. Line 45, the `for` statement, with `LIMIT 2: the step cap` written on it. Line 47, `LIMIT 3: budget, checked BEFORE`. And line 57, `if not reply.get("tool_calls")`, marked `LIMIT 1: the stop condition`. Three limits, three lines, all of them inside the first version.

Now I want to break it on purpose. I am opening line 84, a tool called `check_settlement`. It is a polling API that never settles. Every call is real and every call says `IN_PROGRESS`. Like the runaway in my opening story, the model can keep asking this forever and the stop condition will never fire, because the stop condition only fires on success.

So I am setting the cap to 3 so we are not sitting here all afternoon. The question I am sending asks for the date the bank settled invoice 4471, and tells it to keep checking until the settlement is final. `python invoice_agent.py runaway --max-steps 3`.

Watch the input numbers as the steps come out. 216. Then 286. Then 397. That is the conversation growing, and you are paying for the whole of it again on every trip. The output column barely moves: 25, then 66, then 66.

And the last lines: `outcome: STEP_CAP, steps: 3, tokens this run: 1056`, and then `agent did not finish within 3 steps`. No traceback, no crash, no alarm. A readable failure that tells the operations team what happened in one sentence.

There is an honest thing to say about that run. The model does not always keep polling. On one test it polled 3 times and then wrote in plain words that the settlement was still in progress, and the loop stopped on its own at step 4. If that happens now, nothing is broken. That is the stop condition working, and it is the same point we come to in a moment: the path through the loop changes between runs.

Also notice what people usually reach for here, because I reached for it too. The instinct is to write a better stop condition. The stop condition on line 57 is perfect. It cannot help you, because the model simply never meets it. Only the counter can end this run.

But a counter on steps is not a cap on money, and this next one is the demo I would keep if I had to throw away the other three. I am opening line 90, `read_server_log`. It builds a 40000 line log right here in the file, the way a careless log tool would, so we all know exactly what is inside it.

Watch the step cap on the first line: 10, the default. And watch how many steps this run uses. `python invoice_agent.py budget`.

Step 1 goes out at 202 input tokens. The model asks for the server log. Our code runs it. Now look at the end of the `result` line, where the output is cut off: `[3,268,884 characters]`. That is in the conversation now, and it is about to be sent.

And it is not sent. The last line reads `refused step 2: 227 spent + ~827421 about to send > budget 20000`. So 827421 estimated tokens never left this machine. The step cap of 10 would never have caught this, because the run used 1 step. Count and size are different limits, and that is why both are in the loop.

Look at lines 46 to 49 to see why it refused instead of regretting. The estimate is taken, compared against the budget, and the function returns — all before `call_model` is ever reached. Checking before means the worst run you can have is the budget you chose.

Two honest notes while that is on the screen. The estimate on line 36 is rough: about 4 characters to a token. A provider's own counter is more exact, and for a gate, rough is enough. And this local server would not have billed me anything. A hosted model bills every input token it accepts. Either way, my budget decided, not the server.

Now the last one, and I want your guess before I press Enter. Same code, same question, same model, 3 times in a row. What do you expect to see? `python invoice_agent.py repeat 3`.

Scrolling to the block that says `the three sentences`. Read them with me. All 3 say invoice 4471 was paid on 12 March 2026 by Calder Engineering. One stops there. One adds the amount and the payment reference. One gives the date as 2026-03-12 instead of writing the month. And underneath, `identical strings: False`.

Nothing in the code changed between those 3 runs. Not one character. So if you are about to open a debugger, there is nothing in there to find. This is the one part of your system that will not promise you the same answer twice.

Now the sensible question: can I turn it off. `python invoice_agent.py repeat 3 --temperature 0 --seed 42`. Watch the three sentences this time. Identical, word for word, and `identical strings: True`.

And now let me take that win away, because it is smaller than it looks. This is 1 laptop, serving 1 user, with 1 copy of a model file that will not change under me. It cannot show you the effect of shared hardware serving other people next to you, and it cannot show you the same model name being updated next month. Those are the reasons this is not a promise on a hosted service.

So back to the first run, the one with 3 different sentences. Look at it again and tell me what stayed the same. Not the wording. Scroll down to the block called `the facts and the path`, and look at the column of PASS lines under each run.

Called `lookup_invoice` with 4471. Touched no other tool. Finished inside 10 steps. Inside 20000 tokens. Says it was paid. Gives the date 12 March. 6 PASS lines, 3 times over, under 3 sentences that do not match each other. The 3 runs spent 599, 612 and 600 tokens.

Here is the code doing the asserting, at line 149, `check_facts`. Read the checks with me. The tool name and its argument. No other tool. The outcome and the step count. The token total. The fact, and the date in any of the formats a model might write it. Not one of those checks compares the sentence.

One more run, and this is the check I would put in first on a real system. Invoice 4480 in that file is unpaid. `python invoice_agent.py repeat 3 --invoice 4480`. Three different sentences again, and the check that matters now reads `never says it was paid`.

It passed on all 3. And if it ever fails, that is not a flaky test to be retried until it goes green. That is the agent being wrong, and I would far rather learn it here than from a customer in accounts. Across those runs you just watched, 15 fact checks passed and the command exited with code 0.

So that is 1 file, about 40 lines of loop, and 4 runs. One turn traced end to end. A run that never finishes, stopped by the counter. A run that would have cost more than 40 times its budget, refused before it spent. And 3 runs that agreed on every fact and on no sentence.

What I could not do with any of it was make the model give me something I could put straight into a database. Every answer on that screen was a sentence written for a human to read, and `check_facts` had to go hunting through it with a regular expression to find the date. That is the question I take into next time, along with a harder one: for a lookup this plain, did I need an agent at all?


Use this for context understanding.

Generate infographic for this. Use minimal text — label the main parts with two or three words each, and no sentences or paragraphs. Do label them: a picture with no words at all is harder to follow, not easier. More images, better it is for comprehension. I want this infographic to be in resolution 2560 × 1440 (16:9) The background is plain and flat — one light colour, or a very simple soft gradient. No landscape, no scenery, no sky, no mountains, no water, no roads, no buildings and no photographic setting behind the diagram. Every picture in it earns its place by explaining something; nothing is drawn for decoration.

Title for the infographic: What the model ever receives. Draw it as a short heading on the picture.

Speech content for infographic: Let me show you the one line that makes all of this safe. I am opening the file at line 27. `body = {"model": MODEL, "messages": messages, "tools": tools, **options}`. That dictionary is everything the model ever receives on this run. No password. No file. No database connection. A list of messages and a list of tool descriptions.

This is a NEW picture for this part only. Draw it from a blank canvas. Do not copy, rename, reuse, edit or redraw any picture that already exists — not the slide_*.png files already in this folder, and not any picture made earlier in this conversation. Do not modify, move or delete any existing file in this folder.

Once the file is generated, move it to appropriate location