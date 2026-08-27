# API Surface Map

Complete endpoint reference for Edgematic Studio. All paths are relative to `STUDIO_BASE_URL` (default `http://localhost:8080`). All request/response bodies are JSON unless noted otherwise.

## Contents

- Projects
- Agent
- Devices
- Models
- Applications
- Nodes
- Reverse (Source → Graph)
- Settings
- Infrastructure

---

## Projects

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/projects` | List all projects. Returns `{"projects": Project[]}`. |
| `POST` | `/projects` | Create a project. Body: `{"type": "PYTHON"\|"CPP" (required), "name"?: string, "from_application"?: {category, name}}`. Unknown keys are rejected (400). Returns `Project`. |
| `GET` | `/projects/:id` | Get one project by UUID. Returns `Project`. |
| `PUT` | `/projects/:id` | Update name or description. Body: `UpdateProjectRequest`. |
| `DELETE` | `/projects/:id` | Delete project and all its resources. |

### Files

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/projects/:id/files` | List files in the project workspace. |
| `GET` | `/projects/:id/files/content?path=<name>` | Read file content (`text/plain` response). |
| `PUT` | `/projects/:id/files/content?path=<name>` | Write file content (body: `text/plain`, no JSON). |

### Graph

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/projects/:id/graph` | Get current graph. Returns `{"ir_version": "v1", "nodes": [], "edges": []}`. |
| `POST` | `/projects/:id/graph/diff` | Preview changes. Body: `Graph`. Returns diff summary. |
| `POST` | `/projects/:id/graph/apply` | Replace the graph. Body: `Graph`. |

A new project has a default empty graph — `GET /graph` returns 200 immediately after project creation.

### Build

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/projects/:id/build` | Start a build. Body: `{}`. Returns `Build`. |
| `GET` | `/projects/:id/build` | Get the latest build. Poll until `build.status` is `"ok"` or `"failed"` (`"building"` is NOT terminal). |

Build logs are available as SSE via `BuildLogsApi` (separate from this endpoint).

### Deploy

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/projects/:id/deploy` | Deploy built artifact to a device. Body: `{"device_id": string}`. |
| `GET` | `/projects/:id/deployments` | List all deployments for the project. |

### Runs

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/projects/:id/run` | Start a run. Body: `StartRunRequest`. Returns `Run`. |
| `GET` | `/projects/:id/runs` | List runs. Returns `{"runs": Run[]}`. |
| `GET` | `/projects/:id/runs/:runId` | Get run by ID. |
| `DELETE` | `/projects/:id/runs/:runId` | Stop a run. |

### Agent History (per project)

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/projects/:id/agent/transcript` | Persisted conversation as ordered turns (oldest-first). Returns `{"turns": TranscriptTurn[]}`. Replay/seed counterpart of the `/agent/chat` WS. `200 {"turns": []}` when empty; `404 project_not_found`. |
| `GET` | `/projects/:id/agent/history` | Paginated agent conversation history. Query params: `cursor`, `limit`. Returns `{"entries": [], "next_cursor": string \| null}`. |
| `POST` | `/projects/:id/agent/history/clear` | Clear history. Returns `{"cleared": N}`. |

### Misc per-project

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/projects/:id/fetch` | Fetch project state from a connected device. |

---

## Agent

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/agent/tools` | List all registered tools. Returns `{"tools": ToolDefinition[]}`. |
| `GET` | `/agent/tools/catalog.json` | OpenAI-compatible tools catalog (MCP format). |
| `GET` | `/agent/tools/:name` | Get one tool definition by name. |
| `POST` | `/agent/invoke` | Invoke a tool. Body: `{"name": string, "params": {}}`. Returns `InvokeResponse`. |
| `WS` | `/agent/chat[?project_id=<uuid>]` | Live streaming chat. Server events: `token`, `tool_call`, `tool_result`, `clarification_request`, `code_preview`, `done`, `error`. Bind `project_id` to persist/replay. `code_preview` only under a tool-emitting provider (not `claude-code`). |

**ToolDefinition** shape:
```json
{
  "name": "string",
  "description": "string",
  "category": "string",
  "params": {},
  "side_effects": "none | read | write | network | process",
  "requires_confirm": false,
  "examples": [],
  "dsl_shape": "string | null",
  "applicable_fixes": []
}
```

---

## Devices

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/devices` | List registered devices. |
| `POST` | `/devices` | Register a device. |
| `GET` | `/devices/:id` | Get device by ID. |
| `PUT` | `/devices/:id` | Update device. |
| `DELETE` | `/devices/:id` | Delete device. |
| `POST` | `/devices/discover` | Discover devices on the local network. |
| `POST` | `/devices/:id/probe` | Probe device connectivity. |
| `GET` | `/devices/:id/status` | Get runtime device status. |
| `GET` | `/devices/:id/logs` | Stream device logs (SSE). |
| `GET` | `/devices/:id/logs/download` | Download log archive with optional byte-range. |
| `PATCH` | `/devices/:id` | Switch transport in place. Body: `{"transport_kind": "ssh"\|"nfs"}`. No-op when already on it; re-pairing is NOT required. |

---

## Models (Built-in Catalog)

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/models` | List available models in the catalog. |
| `GET` | `/models/:category/:name` | Get model metadata. |
| `POST` | `/models/:category/:name/download` | Download a model to the local workspace. |
| `GET` | `/models/:category/:name/parsers` | List supported model parser types. |

## Model Zoo (sima-cli catalog)

Browse the SiMa Model Zoo (the same catalog `sima-cli modelzoo list` offers),
returned as JSON. Fetched server-side via `sima-cli download`, reusing the
bundle's Developer-Portal sign-in — so a `502 model_zoo_fetch_failed` usually
means sima-cli is not signed in (run `sima-cli login`), not a bug.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/modelzoo/models` | List the Model Zoo catalog. |

Query params (both optional):

- `version` — SDK version (e.g. `2.1.2`) or a release tag (`ga`/`beta`/`alpha`/`qa`). Omitted → resolves `ga`.
- `boardtype` — `modalix` (gen2, default) or `mlsoc` (gen1).

```http
GET /modelzoo/models?boardtype=modalix
-->
{"version": "2.1.2", "boardtype": "modalix",
 "models": [{"name": "fastflow_demo", "category": "anomaly_detection",
             "yaml_file": "gen2/anomaly_detection/fastflow_demo/fastflow_demo.yaml",
             "assets": ["gen2/anomaly_detection/fastflow_demo/fastflow_demo_mpk.tar.gz"]}]}
```

## User Models (BYOM)

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/user-models` | List user-uploaded models. |
| `POST` | `/user-models/:id/compile` | Compile a user model (async). |

---

## Applications

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/applications` | List pre-built catalog applications. |
| `GET` | `/applications/:category/:name` | Get application metadata. |
| `GET` | `/applications/:category/:name/download` | Download application artifact. |

---

## Nodes

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/nodes` | List all registered pipeline node types. |
| `GET` | `/nodes/:id` | Get node type definition. |

---

## Reverse (Source → Graph)

Parse existing application source code back into an Edgematic graph descriptor.

| Method | Path | Body | Purpose |
| --- | --- | --- | --- |
| `POST` | `/reverse/python` | `{"source": string, "graph_meta"?: string}` | Parse Python source. |
| `POST` | `/reverse/cpp` | `{"source": string, "graph_meta"?: string}` | Parse C++ source. |

Both return `{"graph": Graph}` on success with HTTP 200.

**`graph_meta` token behavior:**
- Absent or `null` → backward-compatible source-body dispatch (REQ-F-006).
- Malformed token → graceful fallthrough to source-body dispatch, still 200 (REQ-F-005).
- Unknown extra fields in the request body are silently ignored.
- `graph_meta` is an opaque round-trip token that preserves NodeIds and lossy-zone attrs lost during source generation.

---

## Settings

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/settings/llm` | Get current LLM configuration. Returns `LlmConfigView`. |
| `PUT` | `/settings/llm` | Update LLM config. Body: `UpdateLlmConfigRequest`. |
| `GET` | `/settings/llm/providers` | List supported providers and models. Returns `{"providers": ProviderMetadata[]}`. |

**LlmConfigView:**
```json
{"provider": "anthropic", "model": "claude-sonnet-4-6", "auth_mode": "api_key",
 "has_key": true, "key_last4": "Ab3x", "base_url": null}
```

**UpdateLlmConfigRequest:**
```json
{"provider": "anthropic", "model": "claude-sonnet-4-6",
 "auth_mode": "api_key", "api_key": "sk-...", "base_url": null}
```

---

## Infrastructure

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api-doc/openapi.json` | OpenAPI 3.x spec. (`/openapi.json` is NOT a route — the SPA fallback answers it with `index.html` and a 200.) |
| `WS` | `/live/ws/run-status` | Real-time run status events stream. |
| `GET/WS` | `/terminal` | Terminal session (WebSocket/SSE). |
| `GET` | `/video` | Video proxy. |
| `GET` | `/videos` | Videos API (list/manage video assets). |

---

## Error Envelope

All error responses use:
```json
{"error": {"code": "snake_case_code", "message": "human-readable description"}}
```

Common error codes:

| Code | Status | Context |
| --- | --- | --- |
| `project_not_found` | 404 | `GET/PUT/DELETE /projects/:id` with non-existent ID |
| `invalid_project_id` | 400 | Malformed UUID in any `/projects/:id` path |
| `bad_request` | 400 | Schema validation failure |
| `device_not_found` | 404 | `/devices/:id` with non-existent ID |
| `model_not_found` | 404 | `/models/:category/:name` with an unknown model |
| `model_zoo_fetch_failed` | 502 | `GET /modelzoo/models` — sima-cli not signed in / catalog fetch failed |
