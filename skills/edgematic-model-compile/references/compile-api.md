# Model Compile API reference

The bring-your-own-model compile flow uses the Edgematic Studio **user-models**
HTTP endpoints directly (there are no agent tools for compilation). All calls are
plain HTTP, no auth. Error envelopes are ADR-002:
`{"error":{"code":"snake_case","message":"…"}}`.

```
BASE="${STUDIO_BASE_URL:-http://localhost:8080}"   # SDK container commonly publishes 8022
```

Compilation is **asynchronous**: the compile endpoints return `202` immediately
with the row in `compiling`; poll `GET /user-models` for the terminal state.

---

## `POST /user-models` — upload the ONNX

- Multipart form fields:
  - `name` (required) — model name; must be compile-safe (used for the output
    filename and the on-disk dir).
  - `file` (required) — the `.onnx` file.
- Response `200`: the `UserModel` row —
  `{ id, name, location, metadata, created_by, created_at, artifact:{filename, sha1, size_bytes}, compile_status:"none", compiled_artifact:null }`.
- Errors: `400` (missing/invalid fields), `413` (over the upload body limit).

```bash
UP=$(curl -s -F 'name=resnet50' -F 'file=@/path/model.onnx' $BASE/user-models)
MID=$(echo "$UP" | python3 -c 'import json,sys;print(json.load(sys.stdin)["id"])')
```

---

## `POST /user-models/{id}/calibration` — attach a calibration dataset

- Multipart form field `file` (required) — a `.tar.gz` archive of representative
  images (`.jpg` / `.jpeg` / `.png`). Extracted into the model's `.calibration/`
  subdir.
- Response `200`: `{ "image_count": <n> }` (number of images extracted).
- Optional — only needed for `"calibration":"dataset"` compiles. Must be uploaded
  **before** the compile call.
- Errors: `400` (no `file` part / empty archive → `image_count` 0 is rejected),
  `404` (model not found), `413` (over the calibration body limit).

```bash
curl -s -F 'file=@/path/calib.tar.gz' $BASE/user-models/$MID/calibration
```

---

## `POST /user-models/{id}/compile` — standard compile

- JSON body (`CompileRequest`, all fields optional; defaults shown):

  | Field | Default | Values |
  | --- | --- | --- |
  | `platform` | `gen2_target` | `gen2_target`, `gen1_target` |
  | `layout` | `NCHW` | `NCHW`, `NHWC` |
  | `quantization` | `default` | `default` |
  | `input_name` | (auto) | override the ONNX input tensor name — **supply with `input_shape`** |
  | `input_shape` | (auto) | parenthesised tuple, e.g. `(1,3,224,224)` — **supply with `input_name`** |
  | `calibration` | `default` | `default` (random-input PTQ) or `dataset` (use uploaded images) |
  | `calibration_method` | `min_max` | `min_max`, `mse`, `moving_average`, `entropy`, `percentile` |

- Response `202`: the `UserModel` row with `compile_status:"compiling"` and a
  `compile_params` block echoing the resolved parameters (incl. calibration
  provenance: `{type, method, dataset_path, image_count}`).
- `input_name`+`input_shape`: when **both** are present the ONNX auto-detection
  step is skipped and they are used verbatim. Supplying only one is ignored.
- Errors: `400` (malformed id/body), `404` (model not found),
  `409` (a compile is already in progress), `422` (no `.onnx` artifact / name not
  compile-safe / not a valid ONNX / `calibration='dataset'` with no images),
  `503 model_compile_unavailable` (ModelSDK `afe` not installed).

```bash
curl -s -X POST -H 'content-type: application/json' -d '{
  "platform":"gen2_target","layout":"NCHW","quantization":"default",
  "input_name":"pixel_values","input_shape":"(1,3,224,224)",
  "calibration":"dataset","calibration_method":"min_max"
}' $BASE/user-models/$MID/compile
```

---

## `POST /user-models/{id}/compile/custom` — compile with a user-supplied script

> **Availability:** ships with **VP-14371** (custom compile-script endpoint).
> Not present on builds predating it — check the OpenAPI spec
> (`curl -s $BASE/api-doc/openapi.json | grep compile/custom`) before relying on it.

- Multipart form field `file` (required) — a **Python compile script**; filename
  must end in `.py`, ≤ **1 MB**, valid UTF-8.
- The uploaded script **replaces** the auto-generated compile program: the ONNX
  input auto-detection and the `generate.py` step are **skipped**, and your
  script is run as the whole compile. This gives full control over
  quantization/calibration/compile. The script is stored as
  `.compile-custom-script.py` under the model's location.
- Calibration env (dataset dir + method) is still exported to the process, so a
  custom script can honour an uploaded calibration set if it reads them.
- Same async `202` + status lifecycle as the standard compile.
- Response `202`: the `UserModel` row (`compile_status:"compiling"`).
- Errors: `400` (missing `file` part, non-`.py` filename, empty or non-UTF-8
  script), `404` (model not found), `409` (compile already in progress),
  `413` (script over 1 MB), `503 model_compile_unavailable`.

```bash
curl -s -X POST -F 'file=@/path/my_compile.py' $BASE/user-models/$MID/compile/custom
```

---

## `GET /user-models` — poll compile status

- Response `200`: `{ "models": [ UserModel, … ] }`. Find your model by `id` and
  read `compile_status`: `none` → `compiling` → (`compiled` | `failed`).
- On `compiled`: `compiled_artifact` = `{ filename, sha1, size_bytes, location }`
  — `location` is the MPK `.tar.gz` path (inside the server/container).
- On `failed`: `compile_error` holds the message (may contain newlines — parse
  with `strict=False`).

```bash
# poll until terminal
while :; do
  st=$(curl -s $BASE/user-models | python3 -c "import json,sys
for m in json.loads(sys.stdin.read(),strict=False)['models']:
    if m['id']=='$MID': print(m['compile_status'])")
  echo "$st"; { [ "$st" = compiled ] || [ "$st" = failed ]; } && break
  sleep 10
done
```

---

## `GET /user-models/{id}/compile/logs` — live compile log

- A **WebSocket** upgrade (NOT SSE / plain curl — a bare `curl` is rejected with
  "Connection header did not include 'upgrade'"). Streams the wrapper's combined
  stdout+stderr, replaying the log so far then tailing live.
- The server also tees the same output to `<model.location>/compile.log`.

---

## What the compile produces (the MPK)

The `.tar.gz` is a complete SiMa **Model Package**, e.g. for a resnet50 compile:
`<name>_stage1_mla.elf` (the compiled model for the MLA), `0_preproc.json` /
`0_postproc.json`, `pipeline_sequence.json`, `<name>_mpk.json`,
`<name>_stage1_mla_stats.yaml`, `compile_model.py`. The compiler partitions ops
across the board's units (MLA / EV74 vision-DSP / A65 ARM) and reports the
distribution in the compile log's "Compilation summary".

## Notes / gotchas

- **Async, always poll** — `202` ≠ done.
- **Calibrate before `dataset` compile** — else `422`.
- **Symbolic non-batch input dim** (e.g. channels named `sequence`) → auto-detect
  pins it to 1; pass `input_name`+`input_shape` explicitly.
- **`afe` (ModelSDK) required** — absent → `503 model_compile_unavailable`;
  on newer SDK images it is at `/sdk-extensions/model-compiler`.
- Placing a compiled user-model **into a project** for deploy has no dedicated
  API (`PUT /projects/{id}/files/content` is UTF-8-only, so it rejects a binary
  tar) — that bridge is out of scope here; see the deploy skill.
