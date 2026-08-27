---
name: edgematic-run-metrics
description: Use when the user wants to benchmark a model's KPIs — latency, FPS, power, or energy — on a paired SiMa DevKit through the Edgematic Studio run-metrics endpoints. Covers both flavors (an uploaded BYOM model and a project's pipeline model), the async start-then-poll flow, benchmark knobs (frame count, device prep), reading the KPI report, and reporting run-metrics errors clearly. For pairing or picking the device, use edgematic-device-ops; for building/deploying/running the full pipeline, use edgematic-build-deploy-run. Do not use for Neat Library C++/Python application development, model compilation, canvas/graph editing, or web-ui React work.
---

# Edgematic Run Metrics

## Overview

Benchmark one compiled model on a paired SiMa DevKit and report its KPIs
(latency / FPS / power / energy), from chat. Studio generates a Python harness
that calls `pyneat.Model.benchmark(frames)`, ships it to the device, runs it on
the SoC, and collects a JSON report.

**Drive this with the `collect_run_metrics` and `get_run_metrics` tools** (below)
— not raw HTTP. `collect_run_metrics` runs the whole on-device benchmark
(deploy → run → collect) and usually returns the finished `metrics` in one call.
When it does, **you MUST render the KPIs as a chart in chat** by emitting an
` ```edgematic-metrics ` fenced block (see *Displaying KPIs as a chart*). That
block is what turns the numbers into the bar chart the user sees.

Two flavors share one engine:

- **BYOM** — benchmark a model artifact already uploaded as a *user model*
  (`POST /user-models`). `POST /user-models/{id}/run-metrics`.
- **Pipeline** — benchmark the model node taken from a project's graph (the
  model is still benchmarked standalone). `POST /projects/{id}/run-metrics`.

Runs are **asynchronous**: the start call returns `202` with a job whose
`status` is `queued`; you then poll the job until it reaches a terminal state
(`succeeded` / `failed`) and read the report.

Default base URL: `http://localhost:8080` (set `STUDIO_BASE_URL` to override; the
Neat SDK container commonly maps it to `:8022`). Errors follow the ADR-002
envelope `{"error":{"code":"...","message":"..."}}`.

Device pairing/selection lives in **`edgematic-device-ops`**; project builds and
runs live in **`edgematic-build-deploy-run`**. Read those when you need to pick a
device or prepare a project.

## Tools (use these)

| Tool | Purpose | Args |
| --- | --- | --- |
| `collect_run_metrics` | Run the on-device benchmark and return the metrics. Blocks briefly; usually returns the finished job in one call. | `device` (name/id, required); `user_model_id` OR `project_id`; `frames?` |
| `get_run_metrics` | Poll a benchmark job by id (fallback when `collect_run_metrics` returned before it finished). | `job_id` |

Both are non-destructive and don't prompt for confirmation. The returned job's
`status` reaches `succeeded` (then `metrics` is populated) or `failed` (then
`last_error` / `log_tail` explain why). The underlying HTTP API below is the
same engine — reach for it only in a non-agent context.

## Underlying HTTP API (reference)

| Method & path | Purpose | Notes |
| --- | --- | --- |
| `POST /user-models/{id}/run-metrics` | Start a **BYOM** benchmark | Body: `device_id` (required) + knobs. → `202` + job. |
| `POST /projects/{id}/run-metrics` | Start a **pipeline-model** benchmark | Body: `device_id` (required) + knobs. → `202` + job. |
| `GET /run-metrics/{job_id}` | Poll one job | `{status, metrics?, log_tail, …}`. `metrics` populated once `succeeded`. |
| `GET /run-metrics/{job_id}/results` | KPI report only | `409 run_metrics_not_complete` while still running. |
| `GET /user-models/{id}/run-metrics` | List a model's jobs | `{runs:[…]}`, newest-first. |
| `GET /projects/{id}/run-metrics` | List a project's jobs | `{runs:[…]}`, newest-first. |
| `DELETE /run-metrics/{job_id}` | Stop an active job | Idempotent (`204` even on a terminal job). |

Full request/response, DTO, and error detail: `references/run-metrics-api.md`.

## Request knobs (both start endpoints)

```jsonc
{
  "device_id": "<uuid>",         // required — a paired, reachable device
  "frames": 1000,                // optional, default 1000 synthetic samples (use e.g. 200 for a quick check)
  "include_plugin_latency": false, // optional — fold pre/post-process latency into the measured latency
  "kill_running": false,         // optional — kill stray Neat/GStreamer apps holding the accelerator first
  "reset_mla": false             // optional — run fix_devkit_runtime.sh on the device first (implies kill_running)
}
```

## Workflow

1. **Decide what to benchmark** — an uploaded model (BYOM) or a project's
   pipeline model. Ask if unclear; never guess the target.
2. **Get a paired device.** You need a `device_id` (resolve a name → id via
   `GET /devices`, or pair one — see `edgematic-device-ops`). Confirm its
   `status` is `paired` before starting.
3. **Make sure the model is present.**
   - BYOM: it must already be a *user model* with an artifact — upload via
     `POST /user-models` (multipart `file=@model.tar.gz`) if needed. The artifact
     must be a **compiled SiMa package (`.tar.gz` mpk), not an ONNX file**.
   - Pipeline: the project's graph must contain a model node with a compiled
     model path, or the start returns `502` (nothing to profile).
4. **Start the benchmark** with `collect_run_metrics`, passing `device` (the
   device name or id) and EITHER `model` (the uploaded model's NAME or id) OR
   `project_id` (pipeline), plus an optional `frames` (use `200` for a quick
   check). It returns a job with `status: queued`.
5. **Poll** `get_run_metrics` with the returned job `id` every few seconds until
   `status` is `succeeded` or `failed`. Tell the user the phase as it advances
   (`building` → `deploying` → `running` → `collecting`); poll at a sane cadence,
   don't spam.
6. **Report + chart.** On `succeeded`:
   - **Emit the KPIs as an ` ```edgematic-metrics ` block** so they render as a
     chart in chat (see *Displaying KPIs as a chart* — this is required, not
     optional).
   - Then add one sentence summarising `latency_ms` + `fps` (and power/energy
     when present). On `failed`, surface `last_error` and the `log_tail` instead.

## Displaying KPIs as a chart

After a benchmark **succeeds**, render its KPIs to the user as a fenced
` ```edgematic-metrics ` block whose body is a flat JSON object of
`label → number`. The Studio chat turns that block into a bar chart. Take the
numbers straight from the succeeded job's `metrics.metrics` map (drop the
`benchmark`/`model` metadata; include power/energy only when they are present):

```edgematic-metrics
{ "fps": 877.0, "latency_ms": 2.08 }
```

Rules:
- The fence tag must be exactly `edgematic-metrics` (not `metrics`/`json`).
- Values must be numbers (not strings with units). Keep the SDK's own keys
  (`fps`, `latency_ms`, `avg_power_watts`, `energy_joules`).
- Emit at most one such block per reply, and only for real, succeeded metrics —
  never fabricate numbers. If the job failed, emit no block.
- Put the block in the assistant reply text (it is parsed at render time), then
  add your one-sentence summary after it.
- After the summary, simply **end your reply** — do not call a `done` /
  `finish` tool (there is none) and do not start another benchmark.

7. **Stop when asked** — `DELETE /run-metrics/{job_id}` (or tell the user it has
   already finished).

## Key rules

- **Name a model → use the model path.** When the user refers to an uploaded
  model by name (e.g. "benchmark resnet_50_mpk"), call `collect_run_metrics` with
  `model: "<that name>"`. Do **not** use the pipeline (`project_id`) flavor and
  do **not** edit the project graph / run codegen to create a model node — the
  BYOM model is benchmarked directly. Only use the pipeline flavor when the user
  explicitly asks to benchmark the current project's pipeline model.
- **One tool run is enough.** After `collect_run_metrics` starts a job, just poll
  `get_run_metrics` for THAT job — don't start a second benchmark or switch
  flavors mid-way. When it succeeds, emit the chart and stop.
- **Async — start, then poll.** Don't read `/results` right after starting; it
  returns `409 run_metrics_not_complete` until the job finishes. Poll the job.
- **`frames` defaults to 1000.** A zero or absent value falls back to the
  default; use a small count (e.g. 200) for a fast sanity check.
- **Device prep for a busy accelerator.** If a start returns
  `run_metrics_device_busy`, a prior app is holding the MLA — retry with
  `kill_running: true`, or `reset_mla: true` to run the device recovery script
  first. `reset_mla` implies `kill_running`.
- **One benchmark per device at a time.** A second concurrent job on the same
  device returns `409 run_metrics_device_busy`.
- **Compiled model only.** The harness runs `pyneat.Model(<pkg>).benchmark()` on
  the device — the artifact/graph model path must be a compiled `.tar.gz`
  package. An ONNX won't benchmark.
- **Power/energy are omitted, not zeroed.** On pyneat / DevKit builds without
  power rails, `avg_power_watts` / `energy_joules` are **absent** from the
  response (they appear only for a real nonzero reading); likewise `input_specs`
  / `output_specs` are omitted when empty. Latency and FPS are always real — the
  absence is a device-telemetry limitation, not an error; say so.
- **Feature availability.** These endpoints exist only in a backend built with
  the run-metrics feature. If they 404, the running Studio binary predates it —
  confirm `GET /api-doc/openapi.json` lists `/run-metrics` paths.

## Error handling

Every failure is a typed `{code, message}`. Relay it clearly and suggest the
next step; don't paraphrase away the actionable detail.

| Error code | HTTP | Meaning | What to tell the user |
| --- | --- | --- | --- |
| `user_model_not_found` / `project_not_found` / `device_not_found` | 404 | An id doesn't resolve | Check the id — list models/projects/devices first. |
| `bad_request` | 400 | Malformed id/body, or the BYOM model has no artifact | Fix the request; upload the model artifact if missing. |
| `device_not_paired` | 409 | Device known but not paired | Pair it first — see `edgematic-device-ops`. |
| `run_metrics_device_busy` | 409 | The device is already running a benchmark | Wait for it, or retry with `reset_mla: true` to clear the MLA. |
| `run_metrics_not_complete` | 409 | Results fetched before the job finished | Keep polling `GET /run-metrics/{job_id}`. |
| `run_metrics_not_found` | 404 | Unknown job id | Check the job id. |
| `run_metrics_failed` | 502 | On-device benchmark / collect failed, or (pipeline) no model to profile | Surface `last_error` + `log_tail`; for pipeline, add a compiled model to the graph. |
| `nfs_unavailable` | 503 | NFS-paired device left the shared LAN | Reconnect the device or re-pair over SCP, then retry. |

## Boundaries

- This skill **benchmarks** a model's KPIs. It does not build/deploy/run the full
  pipeline (`edgematic-build-deploy-run`), pair or manage devices
  (`edgematic-device-ops`), compile models, or edit the graph.
- One job per device at a time — no bulk/parallel benchmarking.
- Never handle a device password here — pairing (and its secure form) is
  entirely `edgematic-device-ops`.

## References

- `references/run-metrics-api.md` — endpoints, request/response + DTO shapes,
  job lifecycle, the KPI report shape, the full error table, and relevant env
  vars.
