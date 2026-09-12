# Google ADK — Concepts Reference

A teaching checklist of the concepts in the Google Agent Development Kit (ADK).

## Core building blocks

- **`Agent` / `LlmAgent`** — the basic unit that thinks and acts.
- **`instruction`** — the system prompt that shapes agent behaviour.
- **`model`** — picks the LLM behind the agent (Gemini, or others via LiteLLM).
- **`description`** — tells other agents what this agent is good for.
- **`Runner`** — executes an agent and drives its event loop.
- **`Event`** — one step in the run, such as a message or a tool call.

## Tools

- **Function tools** — turn a plain Python function into a tool.
- **Schema inference** — docstrings and type hints become the tool schema.
- **`ToolContext`** — gives a tool access to state and actions.
- **Built-in tools** — Google Search, Code Execution, Vertex AI Search.
- **Third-party tools** — wrap LangChain and CrewAI tools.
- **MCP tools** — connect to any Model Context Protocol server.
- **OpenAPI tools** — generate tools from an OpenAPI spec.
- **`AgentTool`** — lets one agent be called as a tool by another.
- **Long-running tools** — support human-in-the-loop approval.

## Multi-agent systems

- **`sub_agents`** — build a parent-child agent hierarchy.
- **LLM-driven delegation** — the model transfers control to a sub-agent.
- **`SequentialAgent`** — runs sub-agents one after another.
- **`ParallelAgent`** — runs sub-agents at the same time.
- **`LoopAgent`** — repeats sub-agents until an exit condition.
- **Workflow agents** — the three above; their control flow is deterministic.
- **`output_key`** — passes one agent's result into shared state.

## State, memory and sessions

- **`Session`** — holds one conversation and its history.
- **`State`** — the key-value scratchpad for a session.
- **State prefixes** — control scope: none, `user:`, `app:`, `temp:`.
- **`SessionService`** — stores sessions in memory, a database, or Vertex AI.
- **`MemoryService`** — gives long-term recall across sessions.
- **`Artifacts`** — store files and binary data such as images or PDFs.

## Control and safety

- **Callbacks** — hook into before/after agent, model, and tool steps.
- **Uses** — logging, guardrails, and caching.
- **Plugins** — apply callbacks globally across the whole app.
- **Short-circuiting** — returning a value from a callback skips the real call.

## Streaming and input

- **Bidirectional streaming** — supports live voice and video.
- **Text streaming** — sends partial responses token by token.

## Evaluation and quality

- **`adk eval`** — runs test cases against your agent.
- **Evalsets** — check both the final response and the tool trajectory.

## Developer experience

- **`adk web`** — a local UI to chat with and debug agents.
- **`adk run`** — drives the agent from the terminal.
- **`adk api_server`** — exposes the agent over HTTP.
- **Trace view** — shows every event, tool call, and token cost.

## Deployment

- **Vertex AI Agent Engine** — a managed runtime for agents.
- **Cloud Run / GKE** — deploy the agent as a container.
- **A2A protocol** — lets separate ADK agents talk to each other.

## Suggested teaching order

1. Agent and tools
2. Runner and sessions
3. State
4. Multi-agent systems
5. Callbacks
6. Evaluation and deployment
