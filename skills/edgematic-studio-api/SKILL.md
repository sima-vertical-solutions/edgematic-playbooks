---
name: edgematic-studio-api
description: Use when developing against the Edgematic Studio HTTP API — creating or managing projects, applying pipeline graph descriptors, triggering builds or deployments, starting and stopping runs, invoking agentic tools via /agent/invoke or /agent/chat WebSocket, querying devices or models, configuring LLM settings, or writing Playwright integration tests in the tests/ directory. Do not use for Neat Library C++/Python application development, device-side model compilation, or web-ui React component work.
---

# Edgematic Studio API

## Overview

Edgematic Studio is a REST + WebSocket server (Rust/Axum backend) that manages AI vision pipeline projects for SiMa.ai edge devices. Clients create projects, compose pipeline graphs, build and deploy to devices, and invoke an agentic coding assistant.

Default local base URL: `http://localhost:8080`. Set `STUDIO_BASE_URL` to override.

## Workflow

1. Verify the server is reachable.
   - `GET /api-doc/openapi.json` should return 200 and parse as JSON. Do NOT probe
     `/openapi.json` — it is not a route, and the SPA fallback answers it with `index.html`
     and a 200, so the check passes on a page of HTML.
2. Understand the endpoint contract before writing code.
   - Read `references/api-surface-map.md` for the full endpoint list with request/response shapes.
   - For graph operations, read `references/graph-model.md`.
   - For the agentic API (invoke/chat/history), read `references/agent-api.md`.
3. Choose the right resource for the task.
   - New AI vision pipeline → create project, apply graph, build, deploy to device.
   - Interact with the AI assistant → use `/agent/invoke` (stateless tool call) or `/agent/chat` (WebSocket stream).
   - Manage edge devices → use `/devices` endpoints.
   - Download pre-built applications → use `/applications` endpoints.
   - Browse the SiMa Model Zoo catalog → use `GET /modelzoo/models` (server fetches it via sima-cli's Developer-Portal sign-in).
4. Before claiming success on integration tests, run the Playwright suite.
   - `pnpm test:integration` from the `tests/` directory.
   - All tests must pass with zero failures against a live server.

## Defaults

- All JSON endpoints use `Content-Type: application/json`.
- File content endpoints (`/projects/:id/files/content`) use `Content-Type: text/plain`.
- Project IDs are UUIDs (v4).
- The `ir_version` field in graph payloads is always `"v1"`.
- Builds are async — poll `GET /projects/:id/build` until `build.status` is `"ok"` or
  `"failed"`. `"pending"` and `"building"` are BOTH non-terminal; treating `!= "pending"` as
  done deploys mid-build and fails with `project_not_built`.
- Deployments require a device registered first via `POST /devices`.
- Error envelopes have the shape `{"error": {"code": "snake_case_code", "message": "human-readable"}}`.

## Key Patterns

### Create a project and apply a graph

```http
POST /projects
{"name": "my_pipeline", "type": "PYTHON"}
# `type` is REQUIRED ("PYTHON" | "CPP"); the body is deny_unknown_fields,
# so any extra key (there is no `description`) is a 400.

POST /projects/{id}/graph/apply
{"ir_version": "v1", "nodes": [...], "edges": [...]}
```

### Build and deploy

```http
POST /projects/{id}/build
{}

# Poll until build.status is "ok" or "failed"
GET /projects/{id}/build

POST /projects/{id}/deploy
{"device_id": "<device-uuid>"}
```

### Invoke an agentic tool

```http
# Discover available tools
GET /agent/tools

# Invoke a tool
POST /agent/invoke
{"name": "tool_name", "params": {"key": "value"}}

# OpenAI-compatible catalog (for external LLM tool-use)
GET /agent/tools/catalog.json
```

### Configure LLM backend

```http
GET  /settings/llm/providers      -- list supported providers and their models
GET  /settings/llm                -- get current config
PUT  /settings/llm
{"provider": "anthropic", "model": "claude-sonnet-4-6",
 "auth_mode": "api_key", "api_key": "sk-..."}
```

## API Selection

- **`/projects/:id/graph/apply`** — replace the project's entire graph.
- **`/projects/:id/graph/diff`** — preview graph changes before applying (dry run).
- **`/reverse/python`** or **`/reverse/cpp`** — parse existing source code back into a graph descriptor.
- **`/agent/invoke`** — single synchronous tool invocation; returns JSON immediately.
- **`/agent/chat[?project_id=<uuid>]`** — WebSocket; streams a live turn (`token` / `tool_call` / `tool_result` / `clarification_request` / `code_preview` / `done` / `error`). Bind with `project_id` to persist + replay. `code_preview` fires only under a tool-emitting provider, not `claude-code`.
- **`/projects/:id/agent/transcript`** — persisted conversation as ordered turns (replay/seed counterpart of the WS).
- **`/projects/:id/agent/history`** — paginated conversation history per project.

## Boundaries

- Do not edit `backend/` (Rust) or `web-ui/` (React) source. Only `tests/` and `playbooks/` are in scope for QA work.
- Do not hardcode `localhost:8080` — use `process.env.STUDIO_BASE_URL ?? 'http://localhost:8080'`.
- Do not commit integration tests without running the full suite against a live server.
- Do not guess endpoint behavior — use the `describe_endpoint` tool (it reads the in-process
  OpenAPI document; no HTTP call needed), or verify against `/api-doc/openapi.json`.

## References

- `references/api-surface-map.md`
- `references/graph-model.md`
- `references/agent-api.md`
