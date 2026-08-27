# Agent API

Edgematic Studio exposes an agentic coding assistant surface that external AI systems (Claude Code, Codex, custom agents) can integrate with.

## Endpoints

### Tool Discovery

```http
GET /agent/tools
```
Returns `{"tools": ToolDefinition[]}`. Each tool has a `name`, `description`, `category`, `params` schema, `side_effects` level, and a `requires_confirm` flag.

```http
GET /agent/tools/catalog.json
```
Same tool list in OpenAI-compatible format for direct LLM tool-use injection.

```http
GET /agent/tools/:name
```
Get a single tool definition by exact name.

### Tool Invocation

```http
POST /agent/invoke
Content-Type: application/json

{"name": "tool_name", "params": {"param_key": "value"}}
```

Synchronous, stateless. Returns the tool's `InvokeResponse` (shape depends on the tool). Use for single-shot operations.

### WebSocket Chat

```http
WS /agent/chat[?project_id=<uuid>]
```

Bidirectional streaming conversation with the configured LLM backend.

- **`project_id` (optional):** binds the socket to a project so its turns are persisted and replayable (see Conversation Replay). Absent → an unbound, ephemeral conversation (no transcript row). Malformed UUID → upgrade refused with HTTP `400` (`invalid_project_id`); unknown id → `404` (`project_not_found`). The WS route is intentionally **not** in the OpenAPI document, so the query param is hand-wired in the client.
- **Client → server** (3 message types): `user_message`, `clarification_answer`, `cancel`.
- **Server → client** (7 event types, discriminated on `type`): `token`, `tool_call`, `tool_result`, `clarification_request`, `code_preview`, `done`, `error`.

Server event shapes (key fields):

| Event | Shape |
| --- | --- |
| `token` | `{ "type": "token", "text": string }` — incremental assistant text. |
| `tool_call` | `{ "type": "tool_call", "call_id": string, "tool": string, "params": object }`. E.g. `write_file` params are `{ project_id, name, content }`. |
| `tool_result` | `{ "type": "tool_result", "call_id": string, "tool": string, "result": object }` — failure is carried inside the `result` envelope. |
| `clarification_request` | `{ "type": "clarification_request", "prompt": string }` — reply with `clarification_answer`. |
| `code_preview` | `{ "type": "code_preview", "turn_id": string, "python"?: string, "cpp"?: string, "valid": boolean, "issues": [...] }` — the full current generated source after a graph-affecting change, coalesced **once at end of turn**. |
| `done` | `{ "type": "done", "turn_id": string }` — turn finished. |
| `error` | `{ "type": "error", "code": string, "message": string }`. |

> **Provider caveat (important).** `code_preview` — and in-process `write_file` tool steps — are emitted **only by the in-process tool loop**, i.e. providers with `supports_tools: true` (the Anthropic-key provider). The **`claude-code`** provider is chat-only (`supports_tools: false`): its edits run inside the Claude Code CLI subprocess and surface as display-only tool frames, so **no `code_preview` is ever emitted** under it. Check `GET /settings/llm` before expecting code previews (or diffs derived from them).

### Conversation Replay (Transcript)

```http
GET /projects/:id/agent/transcript
```

The durable counterpart of the live WS: the project's persisted conversation as **ordered turns, oldest-first**. Seed a thread from this when opening a project, then fold live WS events on top (the wire shapes are designed to match).

```jsonc
{ "turns": [ TranscriptTurn, … ] }   // [] when the project has never had a turn
```
- `200 {"turns": []}` — exists but empty (never 404 for "empty").
- `400 invalid_project_id` — malformed path id · `404 project_not_found` — no such project.

Each `TranscriptTurn`: `{ seq, turn_id, at, user_text, assistant_text, steps: TranscriptStep[], status, clarification_prompt?, error? }`, where `status` ∈ `done | error | awaiting_clarification | awaiting_confirmation` (terminal — the live-only `streaming` never appears). A `TranscriptStep` is `kind`-discriminated:
- `{ "kind": "tool", "call_id", "tool", "params", "result"?, "error"?: {code,message}, "status": "ok"|"error" }`
- `{ "kind": "code_preview", "turn_id", "python"?, "cpp"?, "valid", "issue_count" }` (only the issue **count** is persisted)

`TranscriptResponse` / `TranscriptTurn` / the step + enum types are on the OpenAPI doc and generated client — prefer them over hand-rolling.

### Displaying code diffs

There is **no server-computed diff event** — a code diff is derived **client-side** from the events above:

- **Generated code (`code_preview`):** diff a turn's `python`/`cpp` against the *previous same-language `code_preview`* in the thread. The **first** preview of a session has no prior — diff it against the file's current on-disk content read at bind time (`GET /projects/:id/files/content?path=main.py`), or render it plain.
- **`write_file`:** the new content is the tool_call `params.content`; there is no before-image on the wire, so render additions-only (or diff against a pre-write `files/content` read if you snapshot before the write lands).

This is what the Studio UI does (`web-ui/.../lib/derive-diff.ts` + `<DiffBlock>`). Because it depends on `code_preview` / `write_file`, **it only produces diffs under a tool-emitting provider** — see the provider caveat above.

### Project History

```http
GET /projects/:id/agent/history?cursor=<token>&limit=<n>
```
Paginated conversation history for a specific project. Returns:
```json
{"entries": [...], "next_cursor": "opaque-string | null"}
```

Iterate by passing the returned `next_cursor` as `cursor` in the next request. When `next_cursor` is `null`, you have reached the end.

```http
POST /projects/:id/agent/history/clear
{}
```
Clears all history entries for the project. Returns `{"cleared": N}`.

## Side Effects Levels

Tools declare their side-effects scope, which controls confirmation requirements:

| Level | Meaning |
| --- | --- |
| `none` | Pure read with no observable side effects |
| `read` | Reads filesystem or internal state |
| `write` | Mutates project files or internal state |
| `network` | Makes outbound network calls |
| `process` | Spawns or manages external processes |

Tools with `requires_confirm: true` are gated by the **runtime**, not by the caller: the approval
policy (`/settings/approval-policy`) and agent mode (`/settings/agent-mode`) decide per category
whether a call is allowed outright, prompts the user, or is rejected. Do not add your own permission
question on top — the system prompt states the active posture each turn, and asking when the posture
already grants the call only stalls the run.

## LLM Configuration

The agent's LLM backend is configured via `/settings/llm`. The agent uses whatever provider is currently configured. Check the active config before diagnosing unexpected tool behavior:

```http
GET /settings/llm
```

Providers are enumerable via `GET /settings/llm/providers`. Each provider lists supported `auth_modes` (e.g. `api_key`, `env_var`) and available `models`.

## Integration Pattern for External Agents

To wire Claude Code or Codex to Edgematic's tool surface:

1. Fetch `GET /agent/tools/catalog.json` — inject as the tool list into the LLM context.
2. When the LLM emits a tool call, forward it to `POST /agent/invoke` with the `name` and `params`.
3. Return the `InvokeResponse` back to the LLM as a tool result.
4. Optionally store conversation turns in `/projects/:id/agent/history` for context continuity.
