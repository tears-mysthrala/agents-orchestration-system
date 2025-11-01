# Agent Orchestration — Target Architecture

This document captures the recommended target architecture, API contract, lifecycle semantics, telemetry and migration checklist for running the existing agents under a managed environment (AI Toolkit / Agent Boulder style).

## High-level recommendation

- Keep the current adapter model: run a small per-agent HTTP service (MCP-style adapter) for each agent process. This aligns with the existing PoC, gives process isolation (resource/permissions), and allows individual lifecycle management, scaling and upgrades.
- Use the central Web Manager as the control plane: discovery (registration + heartbeat), lifecycle operations (pause/resume/stop/restart), forwarding of execution requests, and UI/telemetry aggregation.

Rationale: the repository already implements a stable per-agent adapter + manager. Moving to one MCP per agent minimizes migration risk and keeps the system modular.

## Communication

- Protocol: HTTP/JSON for agent ↔ manager (REST endpoints). This is simple, language-agnostic and already implemented.
- Consider adding an optional gRPC path for high-throughput or binary payloads in a follow-up.
- Default endpoints to implement on every agent service:
  - GET /health — basic liveness
  - GET /info — id/name/defaultModel/metadata
  - POST /execute — main request: JSON body {"parameters": {...}}
  - GET /status — lifecycle state {status, current_task}
  - POST /action — lifecycle actions {"action": "pause|resume|stop|restart"}
  - GET /logs?lines=N — tail of logs

API contract: handlers should return JSON bodies, use standard HTTP status codes (200, 400, 409 for paused/stopping, 503 for unavailable, 500 for server errors). The manager forwards requests and proxies status codes.

## Discovery and configuration

- Primary discovery: explicit registration to manager (POST /api/agent-services/register) with payload {id, serviceUrl, metadata}. Agent performs heartbeat to `/api/agent-services/heartbeat`.
- Fallback discovery: deterministic ports defined in `config/agents.config.json` (per-agent `port`) so manager or operators can contact agents even when registration fails.
- Recommendation: keep deterministic ports for local development and ephemeral discovery for dynamic deployments.

## Lifecycle model

- States: running, paused, stopping (draining), stopped.
- Actions accepted: pause, resume, stop, restart.
- Stopping semantics:
  - On `stop`/`restart`, agent should mark itself as stopping, reject new /execute requests with 409, drain any current in-flight work (configurable timeout, default 30s) and then exit (or execv for restart).
  - Manager should surface `stopping` state in listings and avoid treating the agent as absent until `unregister` or timeout.

Implementation notes (already applied in PoC): `app.state._shutdown_requested` and `current_task` must be observed by `/execute` and `/action` to coordinate drain.

## Authentication & Authorization

- For internal deployments within trusted networks, start with bearer API keys (Manager has a key the agents verify) or mutual TLS.
- Production recommendation: mTLS between manager and agents + short-lived JWT for UI clients, or an API gateway that adds auth and rate-limiting.
- Minimum viable step: add an optional token header `X-Manager-Token` that agents check for registration/heartbeat/action endpoints. Document key rotation.

## Logging and Telemetry

- Structured logs (JSON) written to stdout and to per-agent log files (configurable `runtime.logDirectory`). This enables container platforms to capture logs while preserving file trails.
- Metrics: expose a small `/metrics` endpoint in manager aggregated from agents and coordinator; agents should emit simple metrics (task_running 0/1, tasks_total counter). Use Prometheus exposition for scraping.
- Tracing: instrument critical paths with OpenTelemetry (optional follow-up). Add trace-context propagation between manager and agents to correlate requests.

## Observability & Manager behavior

- Manager responsibilities:
  - Keep `REGISTERED_SERVICES` with `registered_at` timestamps.
  - Host a registry cleaner that purges services not heartbeating within TTL (configurable; default 30s).
  - When sending lifecycle `stop`/`restart`, wait briefly to see `status` become `stopping` (or expose `/api/.../status`) and show it in UI.
  - Aggregate logs and metrics for UI and export.

## Security considerations

- Do not allow unauthenticated `action` endpoints in production. Add required auth/mTLS before enabling on public networks.
- Limit what agents can do when restarted by manager (avoid privilege escalation).

## Config format

- Reuse `config/agents.config.json` with the following per-agent keys: id, name, description, entryPoint, port (optional), metadata. Add top-level runtime config: managerUrl, logDirectory, drainTimeout.

Example:

{
  "runtime": { "logDirectory": "logs", "drainTimeoutSeconds": 30 },
  "agents": [
    { "id": "planner", "name": "PlannerAgent", "port": 8100 },
    { "id": "executor", "name": "ExecutorAgent", "port": 8101 }
  ]
}

## Acceptance criteria

- Manager can list agents and forward /execute to a running dummy agent (existing tests cover this).
- Stop action performs graceful drain: agent rejects new requests and exits after current task completes (or timeout).
- Restart action performs execv after drain (or fails cleanly and exits non-zero).
- Tests: unit tests and E2E tests for pause/resume/stop/restart/drain behaviors. Fast test profile must not require heavy ML dependencies (keep `--dummy` mode and test-time retriever mocks).

## Edge cases

- Agent crash during drain: manager should detect liveness missing and mark as unregistered.
- Very long-running tasks: allow override of drain timeout per agent in config.
- Network partitions: registration/heartbeat retries and fallback to deterministic ports.

## Migration checklist (remaining work)

1. Add configurable `drainTimeoutSeconds` to `config/agents.config.json` and use it in `mcp_service` when draining.
2. Add optional `MANAGER_TOKEN` header validation at agents for `/register`/`heartbeat`/`action` endpoints.
3. Update manager to mark `stopping` state in listing and optionally wait before purge.
4. Add metrics exposure on agents (Prometheus format) and manager aggregation.
5. Add a small `docs/README-migration.md` with run instructions and CI profiles (fast vs full).
6. Harden restart path on Windows (execv semantics differ) — provide fallback to spawn new process and exit.

## Tests to add

- Unit test for `mcp_service` action `stop`/`restart` to assert that new requests return 409 and that the agent exits after draining.
- Manager integration test to confirm `stopping` state is visible in `/api/agent-services` listings.
- CI job grouping: `fast` (no native ML deps) vs `full` (requires FAISS / sentence-transformers). Use environment variable `TEST_PROFILE=fast` in CI to skip heavy tests.

## Next steps

- I will implement the following in order (unless you prefer a different priority):
  1. Make drain timeout configurable from `config/agents.config.json` and environment vars. (small code change to `agents/mcp_service.py` and config update)
  2. Add manager-side visibility of `stopping` state (update `web/routers/manager.py` to surface it from `/status`) and use it in registry cleaner so it doesn't purge `stopping` services immediately.
  3. Add optional manager token validation on agents (config-driven). This will be a small opt-in security improvement.

If you'd like, I can start with (1) now and run the test suite.
