---
name: edgematic-model-compile
description: Use when the user wants to compile or quantize their OWN model (an ONNX file) into a SiMa MPK package through the Edgematic Studio user-models HTTP API — upload the ONNX, attach a calibration dataset for post-training quantization, run the compile (standard, or with a user-supplied Python compile script), poll it to completion, and read the resulting .tar.gz artifact. Covers input-name/shape overrides, calibration methods, live compile logs, and the custom compile-script variant. For deploying or running the compiled model on a device, use edgematic-build-deploy-run. Do not use for catalogue (pre-built) models, Neat Library C++/Python app development, or canvas/graph editing.
---

# Edgematic Model Compile (bring-your-own ONNX → SiMa MPK)

## Overview

Turn a user's own **ONNX** model into a **SiMa MPK** (`.tar.gz`) that runs on the
SiMa MLA accelerator — quantized (float32 → int8) and compiled for a target
platform. You drive this through the Edgematic Studio **user-models** HTTP API.

There are **no agent tools for compilation** (the agent catalog has
build/deploy/run/devices but nothing for user-models) — so this flow is
**REST-only**: call the endpoints directly (curl/HTTP).

The flow is a **3-call async pipeline**: upload the ONNX, (optionally) attach a
calibration dataset, then start the compile — which returns immediately (`202`)
and runs in the background. You **poll** `GET /user-models` until the model
reaches `compiled` or `failed`.

Base URL: `BASE="${STUDIO_BASE_URL:-http://localhost:8080}"` — no auth. The
provisioned SiMa SDK container commonly publishes the API on **`8022`**; confirm
with `curl -s -o /dev/null -w '%{http_code}' $BASE/api-doc/openapi.json` (200 = ready).

## Endpoints

| Step | Endpoint | Notes |
| --- | --- | --- |
| Upload ONNX | `POST /user-models` | multipart `name`, `file` (`.onnx`). Returns the model `{id, …}`. |
| Attach calibration | `POST /user-models/{id}/calibration` | multipart `file` (`.tar.gz` of images). Returns `{image_count}`. Optional. |
| Compile (standard) | `POST /user-models/{id}/compile` | JSON params. **202** + async. |
| Compile (custom script) | `POST /user-models/{id}/compile/custom` | multipart `file` (a `.py` compile script). **202** + async. *Requires VP-14371.* |
| Poll | `GET /user-models` | Read this model's `compile_status`. |
| Live log | `GET /user-models/{id}/compile/logs` | **WebSocket** (not curl). |

Full request/response shapes, all params, calibration methods, the custom-script
contract, and error codes: `references/compile-api.md`.

## Workflow

1. **Upload the ONNX.** `POST /user-models` with `name` + `file`; capture the
   returned `id`.
2. **Inspect the input shape.** If the ONNX has a symbolic (named) **non-batch**
   dim — e.g. a channels dim named `sequence` — you MUST override it at compile
   time; otherwise auto-detect pins every symbolic dim to 1 and produces a
   wrong-shaped model (e.g. `(1,1,224,224)` instead of `(1,3,224,224)`). Quick
   check:
   `python3 -c "import onnx;i=onnx.load('m.onnx').graph.input[0];print(i.name,[d.dim_value or d.dim_param for d in i.type.tensor_type.shape.dim])"`
3. **Attach a calibration dataset** (recommended). `POST …/calibration` with a
   `.tar.gz` of representative images. Required before a `dataset` compile; skip
   only for random-input PTQ (lower accuracy).
4. **Start the compile.**
   - **Standard:** `POST …/compile` with params (platform/layout/quantization,
     optional `input_name`+`input_shape`, `calibration`, `calibration_method`).
   - **Custom script:** `POST …/compile/custom` with `file=@your_compile.py` —
     your script replaces the auto-generated one (ONNX auto-detect + `generate.py`
     are skipped). Use this for full control over calibration/quantization/compile.
5. **Poll to completion.** `GET /user-models`; read this model's `compile_status`
   until `compiled` or `failed` (parse with `strict=False`). Don't spam polls —
   a real compile takes minutes.
6. **Read the result.** On `compiled`, `compiled_artifact` gives
   `{filename, sha1, size_bytes, location}` (the MPK `.tar.gz`). On `failed`,
   report `compile_error` (and the compile log).
7. **Hand off to deploy.** To run the MPK on a board, switch to
   **edgematic-build-deploy-run**.

## Key rules

- **Compile is async — always poll.** The POST returns `202` with
  `compile_status: compiling`; the artifact does not exist until the poll shows
  `compiled`. Never treat 202 as done.
- **Calibrate before compiling with `"calibration":"dataset"`.** The dataset
  upload must precede the compile call, or it 422s (no images found).
- **Symbolic non-batch dim → pass `input_name` + `input_shape` together** (step 2).
  Both or neither — supplying one alone is ignored.
- **Custom script replaces auto-detection.** With `/compile/custom`,
  `input_name`/`input_shape`/`generate.py` are ignored — your `.py` owns the
  whole compile. Filename must end in `.py`, ≤ 1 MB, UTF-8.
- **`503 model_compile_unavailable`** = the SiMa ModelSDK (`afe`) is not
  installed on the host. It ships with the **Model SDK Extension**; on newer SDK
  images the venv lives at `/sdk-extensions/model-compiler`.
- **One compile at a time per model** — a second returns `409`.
- **Parse responses with `strict=False`** — `compile_error` may contain newlines
  (Python's `json.load` rejects control chars by default).

## Error handling

Relay the typed `{code, message}` and the next step. A *failed compile* is a
normal terminal state (`compile_status: failed` + `compile_error`), not a
transport error.

| Error / state | Meaning | What to tell the user |
| --- | --- | --- |
| `compile_status: failed` | Compile errored | Show `compile_error` (+ compile log); fix params/model and retry. |
| `409` compile in progress | A compile is already running | Wait and poll; one compile per model. |
| `422` no `.onnx` / not compile-safe / invalid ONNX | Model can't be compiled | Re-upload a valid `.onnx`; ensure a compile-safe name. |
| `422` `calibration='dataset'` but no images | Dataset step skipped | Upload a calibration `.tar.gz` first. |
| `503 model_compile_unavailable` | ModelSDK `afe` missing | Install the Model SDK Extension in the SDK container, then retry. |
| `400` (custom) non-`.py` / empty / non-UTF-8 script | Bad custom script | Upload a valid UTF-8 `.py` compile script (filename ends `.py`). |

## Boundaries

- Compiles a user's ONNX into an MPK and reports the artifact. Does **not**
  deploy or run it, create projects, or edit graphs.
- Deploy/run the compiled MPK → **edgematic-build-deploy-run**. Device pairing →
  **edgematic-device-ops**.
- Catalogue (pre-built) models are out of scope — this is bring-your-own-ONNX only.

## References

- `references/compile-api.md` — endpoint request/response shapes, all compile
  params, calibration methods, the custom compile-script contract, and error codes.
