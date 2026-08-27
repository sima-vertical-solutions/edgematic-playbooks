# Graph Model

Edgematic pipeline graphs use a JSON descriptor with `ir_version`, `nodes`, and `edges`.

## Minimal Valid Graph

```json
{
  "ir_version": "v1",
  "nodes": [],
  "edges": []
}
```

A new project is initialized with a default empty graph. `GET /projects/:id/graph` returns 200 immediately after project creation — no need to apply an empty graph first.

## Graph Shape

```typescript
interface Graph {
  ir_version: "v1";
  nodes: Node[];
  edges: Edge[];
}
```

Node and Edge shapes are defined by the pipeline node catalog. Query `GET /nodes` and `GET /nodes/:id` for the current registered types, parameters, and connection contracts.

## Apply vs Diff

- **`POST /projects/:id/graph/diff`** — dry run. Returns what would change without modifying state. Use before destructive applies.
- **`POST /projects/:id/graph/apply`** — replaces the entire current graph. The backend validates the graph before committing.

## Reverse Parsing

If you have existing Python or C++ Neat application source code, use `/reverse/python` or `/reverse/cpp` to recover the graph descriptor:

```http
POST /reverse/python
{"source": "<python source>"}
```

Response: `{"graph": Graph}`.

The optional `graph_meta` opaque token (produced by the editor when exporting source) preserves NodeIds and lossy metadata that plain source generation loses. Pass it when available to get a byte-identical graph round-trip.

## Build from Graph

Once a graph is applied:

1. `POST /projects/:id/build {}` → starts compilation. Returns `Build`.
2. Poll `GET /projects/:id/build` until `build.status` is `"ok"` or `"failed"`.
3. On success, `POST /projects/:id/deploy {"device_id": "<uuid>"}`.

Build logs stream in real time via the build-log WebSocket/SSE endpoint (see `BuildLogsApi`).
