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

0. **Preflight the compiler before registering or compiling.** Three things have
   to hold, and the compile 503s if any one of them does not: the compile wrapper
   `./tools/model-compile/compile_user_model.sh` exists in the Studio install;
   a ModelSDK venv was found; and that venv can import `afe`. A present venv is
   therefore not proof — a broken one fails the same way a missing one does, so
   do not report the compiler healthy because the folder is there.

   **Do not carry a list of ModelSDK locations in your head, and do not check one
   path and conclude it is missing.** The venv is searched for in several places
   and two environment variables can move it, and the 503 names every one of them
   when it fires. Read the paths out of that message; it is current by
   construction, where any list repeated here would drift the first time the
   search order changes.

   If the wrapper is missing, tell the user in the FIRST reply, before any
   compile call. Offer the fallback of uploading a pre-compiled `.tar.gz`, which
   goes under `assets/models/` with `model.path` set in `common/config.yaml`.
   Do not recreate the wrapper or run the compiler by hand: both write outside
   the project.
1. **Upload the ONNX.** Locate the file first: when the model lives in the
   project's working directory, find it with `find_project_files` (`extension`
   `onnx`, plus the name the user typed as `pattern`) rather than asking the
   user to type a filesystem path — a path they dictate is a path that can be
   wrong. Then `POST /user-models` with `name` + `file`; capture the returned
   `id`.
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
6b. **Check the decoder before wiring the model.** Open the source ONNX in
    Netron (`netron` pill) and read the output tensor shape(s). Compare them
    with the project's `BoxDecodeType` (for example `YoloV26` in the shipped
    detection example). YOLO families differ in output layout:
    - End-to-end or top-k style outputs fit the YOLO26 decoder.
    - Raw head outputs such as `[1, 4+nc, N]` (typical of YOLO11/v8) need a
      different decoder.
    If the layouts don't match, tell the user before wiring. Changing the
    decoder means editing the entry file, which is a deliberate departure from
    the "only change `common/config.yaml`" rule for examples, so ask first.
    Never wire a model to a decoder you haven't checked.
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
- **Always offer Netron for an ONNX.** Whenever the user attaches or uploads an
  ONNX, the same reply MUST include a `netron` quick-action pill for it, even if
  the compile later fails or never starts. Take the reference from the
  attachment message (`modelPath`, copied character for character) or from an
  `open_netron_viewer` result (`userModelId` + `filename`). Never guess a path.
  If the path is unconfirmed, say so and offer to look it up instead of emitting
  a pill. Do not offer Netron for a compiled `.tar.gz` (Netron reads graphs, not
  MPK packages).
- **`503 model_compile_unavailable`** has three causes; the message says which.
  The compile wrapper `compile_user_model.sh` is missing from the Studio install;
  or no ModelSDK venv was found (it ships with the **Model SDK Extension**, and
  the message lists every path searched — quote that list rather than naming one
  path); or a venv was found and cannot import `afe`, which is a broken install
  rather than an absent one. Installing the extension again only helps the
  second. Relay the paths the message lists rather than any from memory.
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
| `503 model_compile_unavailable` (ModelSDK / `afe` missing) | ModelSDK `afe` missing | Install the Model SDK Extension in the SDK container, then retry. |
| `503 model_compile_unavailable` with "compile wrapper … not found" | The Studio install lacks the wrapper script (the ModelSDK may be present) | Restore the wrapper in the Studio install, or upload a compiled `.tar.gz`. Don't retry the compile. |
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
