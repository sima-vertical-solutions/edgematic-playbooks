# Run-metrics API reference

Benchmark a compiled model on a paired DevKit and collect KPI numbers. This
reference documents the underlying REST contract so you know exactly what each
call needs and how it can fail. All paths are at the server root (no `/api`
prefix); errors use the ADR-002 envelope `{"error":{"code","message"}}`.

## The job model

A run-metrics job carries: `id` (UUID), `kind` (`model` | `pipeline`),
`user_model_id` / `source_project_id` (whichever flavor), `project_id` (the
ephemeral host project that holds the harness), `device_id`, `language`
(`python`), `status`, `started_at`, `finished_at`, `created_at`. When
`succeeded`, a `metrics` object and a `log_tail` are attached.

**Status lifecycle** (`status` field):

```
queued → building → deploying → running → collecting → succeeded
                                                     └→ failed   (last_error set)
```

`queued`/`building`/`deploying`/`running`/`collecting` are transient; `succeeded`
and `failed` are terminal. Poll `GET /run-metrics/{job_id}` until terminal.

## Endpoints

### Start (BYOM) — `POST /user-models/{id}/run-metrics`
Benchmark an uploaded user model. `{id}` is the user-model UUID.

Request body (`config` knobs are flattened alongside `device_id`):

```jsonc
{
  "device_id": "<uuid>",          // required
  "frames": 1000,                 // optional, default 1000
  "include_plugin_latency": false,// optional, default false
  "kill_running": false,          // optional, default false
  "reset_mla": false              // optional, default false (implies kill_running)
}
```

- Success: `202 Accepted` + the job, `Location: /run-metrics/{job_id}`.
- Errors: `bad_request` (400 — malformed id/body, or the model has no artifact),
  `user_model_not_found` / `device_not_found` (404), `device_not_paired` /
  `run_metrics_device_busy` (409), `nfs_unavailable` (503).

### Start (pipeline) — `POST /projects/{id}/run-metrics`
Benchmark the first inference-model node in a project's graph. Same body shape.

- Success: `202` + job.
- Errors: `bad_request` (400), `project_not_found` / `device_not_found` (404),
  `device_not_paired` / `run_metrics_device_busy` (409), `run_metrics_failed`
  (502 — the project has no pipeline graph / no model to profile),
  `nfs_unavailable` (503).

### Poll — `GET /run-metrics/{job_id}`
Returns the full job. While running, `metrics` is absent and `log_tail` shows the
latest device output. Once `succeeded`, `metrics` holds the report (see below).
Errors: `bad_request` (400), `run_metrics_not_found` (404).

### Results — `GET /run-metrics/{job_id}/results`
Returns just the KPI report. `409 run_metrics_not_complete` until the job is
terminal; `404 run_metrics_not_found` for an unknown id.

### List — `GET /user-models/{id}/run-metrics` · `GET /projects/{id}/run-metrics`
`{ "runs": [ job, … ] }`, newest-first. `404` if the model/project is unknown.

### Stop — `DELETE /run-metrics/{job_id}`
Stops an active job. Idempotent — `204` even if already terminal / unknown-active.

## The KPI report

Shape of `metrics` on a succeeded job, and the whole body of `GET …/results`:

```json
{
  "benchmark": { "type": "model.synthetic", "frames": 200, "timestamp_utc": "…" },
  "model": { "path": "assets/models/resnet_50_mpk.tar.gz", "file": "resnet_50_mpk.tar.gz" },
  "metrics": { "latency_ms": 2.108, "fps": 961.8 }
}
```

- `latency_ms` — mean end-to-end latency (includes plugin latency only if
  `include_plugin_latency` was set).
- `fps` — throughput (frames per second).
- `avg_power_watts` / `energy_joules` — **omitted** unless the board reports real
  (nonzero) power; DevKit/pyneat builds without power rails emit throughput-only,
  so these keys are simply absent (not an error).
- `input_specs` / `output_specs` — **omitted when empty** (pyneat builds that do
  not expose model specs). A throughput-only run therefore has just `latency_ms`
  + `fps` under `metrics`.

## Full error table

| Code | HTTP | Meaning |
| --- | --- | --- |
| `bad_request` | 400 | Malformed id/body, or the BYOM model has no artifact. |
| `user_model_not_found` | 404 | No user model with that id. |
| `project_not_found` | 404 | No project with that id. |
| `device_not_found` | 404 | No device with that id. |
| `run_metrics_not_found` | 404 | No run-metrics job with that id. |
| `device_not_paired` | 409 | The device exists but is not paired. |
| `run_metrics_device_busy` | 409 | The device is already running a benchmark. |
| `run_metrics_not_complete` | 409 | `/results` requested before the job finished. |
| `run_metrics_failed` | 502 | On-device benchmark/collect failed, or (pipeline) no model to profile. |
| `nfs_unavailable` | 503 | NFS-paired device left the shared LAN at deploy time. |

## Prerequisites (owned by sibling skills)

- **A paired, reachable device.** Pair / list via `edgematic-device-ops`
  (`POST /devices`, `GET /devices`). Transport (SCP/NFS) is a device property.
- **A model to benchmark.** BYOM: upload with `POST /user-models` (multipart
  `file=@<compiled>.tar.gz`, optional `name`) → `201` + `{id, artifact, …}`.
  Pipeline: the project's graph must contain a compiled model node.

## Relevant environment

- `STUDIO_BASE_URL` — client-side base URL override (default
  `http://localhost:8080`; the Neat SDK container often maps `:8022`).
- `EDGEMATIC_USER_MODELS_DIR` — server-side artifact store root for user models
  (default `./data/user-models`).
- `EDGEMATIC_BUILD_TOOLCHAIN_FILE` / `EDGEMATIC_BUILD_CROSS_COMPILE` — only for
  the pipeline flavor when it cross-builds C++ (aarch64 Modalix); defaults ship
  in the Neat SDK image.

## How it runs (for context)

The server materialises a fresh ephemeral host project per job, generates a
`main.py` harness (`pyneat.Model(<pkg>).benchmark(frames, include_plugin_latency)`
→ `report.json`), ships it to the device (SSH tar+scp, or NFS shared mount),
runs it on the SoC over `ssh -tt`, then reads `report.json` back. The harness is
Python-only; the model is benchmarked standalone (both flavors).
