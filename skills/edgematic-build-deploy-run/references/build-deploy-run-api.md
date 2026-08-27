# Build & Deploy API reference

The agent build/deploy tools call these backend surfaces in-process (never over
HTTP).

## Build lifecycle

A build moves linearly through `pending → building → (ok | failed)`. It runs in
the background, so tools return promptly and you poll for the terminal state.

### `build_project`
- Backing: `POST /projects/{id}/build` → `BuildOrchestrator::begin`. Params:
  `project_id`. Starts a build and returns the initial `Build` record.
- `Build` shape: `{ id, project_id, status, started_at, finished_at?,
  last_error?, log_tail, warnings[], created_at }`. `status` is one of
  `pending` / `building` / `ok` / `failed`.
- Errors: `project_not_found` (404), `build_already_running` (409 — one build
  per project at a time).

### `get_build_status`
- Backing: `GET /projects/{id}/build` → `BuildOrchestrator::latest`. Params:
  `project_id`. Returns the latest `Build` (same shape as above) or `null` if no
  build has ever been started for the project.
- Read-only; poll until `status` is `ok` or `failed`. A `failed` build carries a
  non-null `last_error` and a `log_tail` (recent build output).
- Errors: unexpected storage failures only; a *failed build* is NOT an error
  here — it is a normal `Build` with `status: failed`.

## Deploy

### `deploy_to_device`
- Backing: `POST /projects/{id}/deploy`. Params: `project_id`, `device` (name or
  id). Transport is auto-selected from the device's `transport_kind`:
  - **NFS**: no copy — the project already lives under the shared exported
    workspace the DevKit mounts; records the remote dir after a reachability probe.
  - **SSH**: tar the workspace → scp → remote extract under
    `/data/simaai/applications/<project-id>/`.
- Preconditions: project exists, device exists + `paired`, **latest build is
  green** (`ensure_latest_ok`).
- Errors: `project_not_found` / `device_not_found` (404),
  `project_not_built` / `device_not_paired` (409), `deploy_failed` (502),
  `device_unreachable` (503), `nfs_unavailable` (503 — NFS device left the LAN;
  offers a switch-to-SSH fix).

## Run

A run moves `running → (exited_ok | exited_error | killed)`. Like builds, it is
asynchronous — poll for the terminal state.

### `run_pipeline`
- Backing: `POST /projects/{id}/run`. Params: `project_id`, `device` (name or
  id), optional `entry_point`. Starts a run of the deployed project on the
  device and returns the initial `Run` record.
- **`entry_point`: omit it; never pass `model/main.py`.** The backend resolves
  it against `active_view` and, for a Model-View project, re-anchors to `model/`
  — so on the device the model pipeline is just `main.py` (the re-anchored root
  *is* `model/`) and it writes `output/raw.bin`. The returned `Run.entry_point`
  reads `"main.py"`; that is the re-anchored model pipeline, NOT the empty root
  stub. Passing `entry_point: "model/main.py"` fails with `No such file or
  directory` (there is no `model/` subdir under the re-anchored root).
- **Output rendering is the UI's job.** A successful run's output is shown in the
  chat result card (rendered image for a single-image pipeline, live stream for
  RTSP). Don't fetch + decode `output/raw.bin` yourself.
- `Run` shape: `{ id, project_id, device_id, entry_point, status, local_pid?,
  started_at, finished_at?, exit_code?, log_tail?, created_at }`.
- Preconditions: project + device exist, device `paired`, at least one prior
  deployment, no run already active for the project.
- Errors: `project_not_found` / `device_not_found` (404),
  `device_not_paired` / `no_deployment_for_project` / `run_already_active`
  (409), `nfs_unavailable` (503), plus entry-point resolution errors (400).

### `get_pipeline_status`
- Backing: latest of `GET /projects/{id}/runs`. Params: `project_id`. Returns
  the newest `Run` (with `log_tail`) or `null` if it has never run. Read-only;
  poll until `status` is terminal. `exited_error` carries a non-zero
  `exit_code`; read `log_tail` for on-device output.

### `stop_pipeline`
- Backing: `DELETE /projects/{id}/runs/{run_id}` on the active run. Params:
  `project_id`. Signals SIGKILL to the local ssh child (PTY-propagated to the
  board). Idempotent — a no-op when nothing is running. Confirm-gated.

## Fetch (pull results back)

### `fetch_from_device`
- Backing: `POST /projects/{id}/fetch`. Params: `project_id`, `device` (name or
  id), `remote_path`, optional `destination`. Copies a file/dir from the
  device back into the project workspace via `scp -r`.
- `remote_path` is relative to the project's own device directory
  (`/data/simaai/applications/<project-id>/`) — e.g. `output`,
  `output/stream_0`; absolute paths must resolve inside it. No `..`, safe
  charset only.
- Lands at `<project>/<board_name>/<basename>` by default, or
  `<project>/<destination>/<basename>` when `destination` is given. Returns
  `{ board_name, remote_path, local_path, relative_path }` — surface
  `relative_path` (what the file explorer shows).
- Errors: `project_not_found` / `device_not_found` (404),
  `device_not_paired` (409), `bad_request` (400 — path outside project /
  unsafe), `device_unreachable` (503), `fetch_failed` (502).

## Streaming runs — stability verification

A **single-shot** run reaches a terminal status. A **streaming** run (RTSP,
camera, multi-stream, anything continuous) does not: `running` is its steady
state, and `get_pipeline_status` will report it forever. So run status cannot
tell you whether video works, and a streaming deploy needs its own evidence.

The two legs are independent, and only the first is visible from here:

| Leg | Measured by | What it proves |
| --- | --- | --- |
| device → insight (**ingest**) | `count_streams` (insight `GET /api/ingest/stats`) | The board is pushing annotated frames. This is what a deploy affects. |
| insight → browser (**egress/render**) | `list_output_streams` (`egress`), then the browser | Whether a tile actually shows anything. Not a deploy concern. |

### The ladder

| # | Call | Pass condition |
| --- | --- | --- |
| 1 | `get_pipeline_status` | `status: running` (not `exited_error`). |
| 2 | `count_streams` | `count > 0`. Poll ~10 s apart for up to ~2 min first — channels only exist after the first annotated frame (model load + first inference). |
| 3 | `count_streams` again, **10 s** later | Channel set is the **same or larger**. 10 s of held video is the bar; a shrinking set = the pipeline is dying. |
| 4 | `get_pipeline_status` → `log_tail` | `[profile stream=N] output_fps=… avg_detection_pull_ms=… avg_boxes=…` with non-zero `output_fps` on every expected stream (and `avg_boxes > 0` for a detection pipeline). |
| 5 | `list_output_streams` | `egress.channels[].active == true` for each channel to be shown (~10 s TTL flag on the SENDER only). |

Expect **one output channel per input stream**. A shortfall (4 cameras → 1
channel) is a demux / per-stream-output config fault and must be reported as
such, with expected-vs-seen counts.

### What each failure means

| Observation | Reading | Do NOT |
| --- | --- | --- |
| `count: 0` seconds after the run started | Not yet — first frame hasn't landed | Conclude "no streams"; start an input stream |
| `count: 0` after ~2 min of polling | The pipeline never emitted an output frame — model / source / config | Redeploy blindly |
| Channel set shrinks between samples | Pipeline dying mid-run | Treat as a viewing problem |
| `output_fps` present then collapses to 0 | Source ended or the pipeline stalled | Assume the board is fine |
| Ladder green, user sees blank tiles | insight→browser leg (WebRTC/decode) | Restart / rebuild / redeploy — it fixes nothing |

Input slots (`start_stream`, 1–16) and output channels (`count_streams`, 0–79)
are **different namespaces**: no `start_stream` call can create an output
channel, so it is never the remedy for a zero stream count after a run.

Once the ladder passes, the run is reported *with numbers* (channels, fps,
observation window) and the `edgematic-streams` grid is emitted via
`edgematic-view-streams` as the last element of the reply.

## Typical flow

```
build_project(project_id)                → { status: "pending", ... }
get_build_status(project_id)  (poll)     → { status: "ok", ... }
deploy_to_device(project_id, device)     → Deployment record
run_pipeline(project_id, device)         → { status: "running", ... }
get_pipeline_status(project_id) (poll)   → { status: "exited_ok", ... }
fetch_from_device(project_id, device, "output")  → { relative_path: "<board>/output", ... }
```

Streaming variant — the run never settles, so **stability is the exit
criterion**: 10 s of held video, then show the grid.

```
run_pipeline(project_id, device)         → { status: "running", ... }
get_pipeline_status(project_id)          → { status: "running", log_tail: ... }
count_streams()              (poll ≤2m)  → { count: 4, channels: [0,1,2,3] }
count_streams()                 (+10 s)  → { count: 4, channels: [0,1,2,3] }  # held
get_pipeline_status(project_id)          → log_tail: "[profile stream=0] output_fps=27.9 … avg_boxes=3.4"
list_output_streams()                    → egress.channels[].active == true
→ emit the `edgematic-streams` block (edgematic-view-streams) LAST in the reply
```

The two waits are different things and only one of them is bounded by video:
the **≤2 min** poll waits for a channel to come into EXISTENCE (model load +
first inference); the **10 s** second sample is the stability observation, and
10 s of held video is enough to conclude.

If a build/run ends failed, surface `last_error` / `exit_code` + `log_tail` and
do not proceed to the next step.

## Error envelope

All errors follow `{ "error": { "code": "snake_case_code", "message": "…" } }`.
Relay the `code`/`message`; for a failed build, read the `Build.last_error` /
`Build.log_tail` fields instead (a failed build is a normal result, not an error).
