"""STEP 5 -- put the service behind HTTP.

Run:  uv run python 05_serve.py            (leave it running)

Then, in a second terminal:

    uv run python 06_stream_client.py
    uv run python 06_stream_client.py --team broker_support "what commission do we pay"

Or with curl, which is the version to show the room, because the tenant is
visibly a header and visibly not part of the question:

    curl -N -X POST http://localhost:8080/ask/stream \
      -H "Content-Type: application/json" \
      -H "X-Northwind-Team: claims" \
      -d '{"question":"Does our cover include an escape of water from a neighbouring flat?"}'
"""

import uvicorn

import config

PORT = int(config.optional("PORT", "8080"))

if __name__ == "__main__":
    config.banner("STEP 5 -- the Grounded Answer Service, on HTTP, streaming")
    config.check_credentials()
    print(f"  http://localhost:{PORT}/health")
    print(f"  http://localhost:{PORT}/docs        <- FastAPI's own page, useful on stage")
    print(f"  POST http://localhost:{PORT}/ask          JSON, guardrails run before you see it")
    print(f"  POST http://localhost:{PORT}/ask/stream   server-sent events, as they happen")
    print("\n  The team is the X-Northwind-Team header. It is never in the body.")
    print("  Ctrl-C to stop.\n")
    # reload=False on purpose: a reloader in a live demo restarts the process
    # mid-answer the moment anybody touches a file.
    uvicorn.run("service:app", host="0.0.0.0", port=PORT, reload=False)
