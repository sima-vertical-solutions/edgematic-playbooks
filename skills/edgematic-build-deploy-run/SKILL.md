---
name: edgematic-build-deploy-run
description: Use when the user wants to build an Edgematic project, deploy it to a device, run it on the board, pull results back, or DISPLAY/SHOW a pipeline's output image in chat. Covers starting/polling an async build, deploying over SCP or NFS, starting/polling/stopping a run on a paired SiMa DevKit, copying device files into the project, and rendering an output image inline via an `edgematic-image` block. For a VIDEO/streaming pipeline this skill also owns what "deploy it" actually means — deploy AND run AND verify the streams are live and STABLE AND show them in chat via edgematic-view-streams, none of which the user has to ask for separately. A deployed-but-not-running pipeline produces no video, and a run reporting `running` is not evidence that video works. For device pairing/listing/removal use edgematic-device-ops. Do not use for Neat Library C++/Python application development, model compilation, canvas/graph editing, or web-ui React work.
---

# Edgematic Build, Deploy & Run

## Overview

Take a project all the way to running on a device, from chat: **build** it, wait
for the build to go green, **deploy** it to a paired DevKit, **run** it on the
board, watch its status, and **fetch** the results back into the project so they
show up in the workspace. You do this through the agent's build/deploy/run/fetch
tools, which call the Edgematic Studio backend in-process.

Builds and runs are **asynchronous**: the start tool returns immediately with a
`pending`/`building` (or `running`) record; you then poll the matching status
tool until it reaches a terminal state. Deploy is gated on a green build, and
run is gated on a prior deploy — so respect the order.

**The Studio UI renders the run's output for you.** When a run starts, a publish
result card appears in the chat; once the run lands its output the card shows the
labeled result **image** (for a single-image/Model-View pipeline) or the live
video stream (for an RTSP pipeline). For a **Model-View** run you do **not**
fetch, decode, or draw the output yourself — the card fetches `output/raw.bin`
and renders it; your job ends at "the run succeeded — the output is in the result card".
Manually re-running the parser in a shell for those duplicates the card's work.

**A video pipeline is not delivered until you have SEEN the video.** For any
pipeline that produces live output channels (RTSP, a camera, a multi-stream or
otherwise continuous pipeline), three steps are MANDATORY, in this order, every
time — the user does not have to ask for any of them:

1. **Run it.** A deployed-but-not-running video pipeline produces no video. See
   *"Deploy" means deploy AND run* below — this is not an extra the user must
   request separately.
2. **Verify stream stability** — confirm the device is actually pushing frames
   and is *still* pushing them a moment later. See *Verifying video stability*.
3. **Show the streams** — invoke `edgematic-view-streams` and emit the
   `edgematic-streams` block as the LAST element of your reply, so the user sees
   the live grid of what they just deployed.

**Never substitute a quick-action pill for these steps.** Offering "click here to
run it" instead of running it hands the work back to the user and ends the turn
with a dark device. A Run pill is a fine *addition* to a completed video deploy;
it is never a replacement for one.

**"The run is `running`" is not evidence that video works.** A pipeline that
opens no output channel, opens one and stalls after two frames, or demuxes four
cameras into a single output reports exactly the same run status as a healthy
one. Never close a video deploy on run status alone, and never make the user ask
"can I see it?" — a deploy report with no stream evidence and no grid is an
incomplete answer.

Don't hand-craft stream addresses here — `edgematic-view-streams` counts the
active streams and emits the block the UI renders. Starting/stopping *input*
streams and managing the video library is `edgematic-media-streams`.

**Showing an output image the card won't auto-render.** Some pipelines (notably
`from_application` examples) don't write the Model-View `output/raw.bin` — they
draw their own annotated image into their configured output dir (e.g.
`sandbox/<app-name>/<name>.png`, `io.output_dir`, `output.save_dir`). The card
won't find those. To display such an image in chat, return its **project-relative
path** in a fenced `edgematic-image` block:

    ```edgematic-image
    sandbox/yolo26-object-detector/cat.png
    ```

The UI renders that image inline (with a load-error fallback — it never breaks
the chat). Rules: the path is relative to the **project workspace** and the file
**must exist there** — if it's only on the device, `fetch_from_device` it into
the workspace first and return the path it landed at (`relative_path`). One path
per block; add a short prose summary around it. Don't use this for Model-View
`output/raw.bin` runs — the card already renders those.

Device management (list / add / remove / status) lives in the
**`edgematic-device-ops`** skill — read it when you need to pick or pair a device.

**Offering clickable next-step actions.** When a reply ends by offering the user
discrete next steps to click (not free-form input), append a single fenced
`quick-actions` block holding a JSON array of **self-describing** action objects.
Each object carries a `type` and the UI dispatches on it — there is no id-to-handler
registry. Pick the most specific type:

- `{ "type": "http", "label": "...", "method": "POST", "endpoint": "/projects/3f2a91c7-5d84-4c19-9c11-6b0e1f7a2c30/build", "body": {} }`
  — fires the HTTP call directly (a dedicated handler exists).

  **The `endpoint` must be a fully-substituted concrete path — no `{`, `}`, `<`
  or `>`.** A pill whose endpoint still carries a placeholder is rejected by the
  UI before the call is made, so the click silently does nothing. Path templates
  (`/projects/{id}/build`) are for looking an endpoint up with
  `describe_endpoint`; never emit one as a pill endpoint.

  **Required body fields are not optional.** Read the endpoint inventory's
  `{body: field*, other?}` hint — `*` means REQUIRED. If the hint lists any
  `field*`, the pill's `body` must carry every one of them with a real value;
  `"body": {}` is correct only when the endpoint has no hint or no `*` fields.
  Never guess a field name, and never copy an agent-tool parameter name (the
  tools take `device`; the REST body wants `device_id`). If you cannot fill a
  required field, offer a `navigate` or `prompt` pill instead.

  Verified recipes (path templates shown for lookup — substitute real ids):

  | Action | Method + path | Required body |
  | --- | --- | --- |
  | Build | `POST /projects/{id}/build` | none |
  | Run | `POST /projects/{id}/run` | `device_id` (opt. `entry_point`) |
  | Stop | `DELETE /projects/{id}/runs/{run_id}` | none |
  | Deploy | `POST /projects/{id}/deploy` | `device_id` |
  | Fetch | `POST /projects/{id}/fetch` | `device_id`, `remote_path` (opt. `destination`) |
  | Compatibility | `GET /devices/{id}/neat` | none |
  | Neat update / install | `POST /devices/{id}/neat/update` or `/install` | none (opt. `sudo_password`) |

- `{ "type": "navigate", "label": "...", "route": "/devices" }` — SPA navigation.
- `{ "type": "file-upload", "label": "...", "endpoint": "/user-models", "field": "file", "accept": ".onnx" }`
  — native file picker → multipart POST.
- `{ "type": "prompt", "label": "...", "prompt": "..." }` — sends the prompt back
  to the agent. This is the FALLBACK when no dedicated endpoint exists for the
  action (e.g. "run inference end-to-end", "show accuracy report"): the agent then
  carries out the flow with its tools.

**Check compatibility with device.** When a device is paired (`paired_device_count
> 0`), offer `{ "type": "http", "method": "GET", "label": "Check compatibility
with device", "endpoint": "/devices/8b41d0e5-7a62-4f30-b58d-2c9e4a1b7f56/neat" }`
— GET on the `/devices/{id}/neat` template with the real device UUID pasted in.
Take that UUID from the **per-turn** `[context: device_id=…]` prompt prefix — not
`session_context.device_id` (always `None`) — and never leave a placeholder in
the path. With no device paired, do not offer
this pill; offer `{ "type": "navigate", "route": "/devices" }` instead. After the
call, call the `get_compatibility_doc` tool (no arguments) to fetch the official
compatibility matrix, then apply it to both sides' **platform** versions
(`device_platform` vs `bundle_platform`) and, advisory, their **library/pyneat**
versions (`version`/`bundle_version`, `device_pyneat`/`bundle_pyneat`). Explain
the outcome with nuance — compatible / different-but-works / incompatible —
rather than just echoing `verdict` (e.g. matching platforms but differing
library versions is still compatible, and should be said explicitly). Cite the
doc using the `doc_url` field from the response (or the tool result) — never a
hardcoded URL. If `get_compatibility_doc` fails (offline/unreachable), degrade
gracefully: explain using the raw probed versions and note the matrix could not
be reached. If `verdict` is `update_recommended`, you may then also offer the
existing Update pill — `POST` on the `/devices/{id}/neat/update` template with
the same device UUID pasted in.

Example (note the endpoint carries the REAL project UUID, not a template):

    ```quick-actions
    [
      { "type": "http", "label": "Build", "method": "POST", "endpoint": "/projects/3f2a91c7-5d84-4c19-9c11-6b0e1f7a2c30/build", "body": {} },
      { "type": "navigate", "label": "Pair a device", "route": "/devices" }
    ]
    ```

The UI renders each entry as a pill under the message. Rules: emit **at most one**
such block, only as the **final element** of a reply, and only when genuinely
offering discrete next-step actions — never on an ordinary answer. Keep the array
small (up to ~4 actions) and give each a short, imperative `label`. Do NOT use the
legacy `{ label, id, prompt }` shape — it is no longer supported.

## Tools

| Tool | Purpose | Notes |
| --- | --- | --- |
| `build_project` | Start a build (async) | `project_id`. Returns the initial build record. |
| `get_build_status` | Poll the latest build | `project_id`. `{status, last_error, log_tail, …}` or null. |
| `deploy_to_device` | Deploy the built project to a device | `project_id` + `device` (name or id). Transport auto-selected (SCP/NFS). |
| `run_pipeline` | Start a run on the board (async) | `project_id` + `device` (name or id); optional `entry_point`. Returns the run record. |
| `get_pipeline_status` | Poll the latest run | `project_id`. `{status, exit_code, log_tail, …}` or null. |
| `stop_pipeline` | Stop the running pipeline | `project_id`. Requires confirmation (kills the on-device process). |
| `fetch_from_device` | Copy device files back into the project | `project_id` + `device` + `remote_path`; optional `destination`. Shows results in the workspace. |

Full request/response and error-code detail: `references/build-deploy-run-api.md`.

## Workflow

1. **Identify the project + device.** You need the `project_id`; deploy/run/fetch
   also need a `device` (name or id — see `edgematic-device-ops` to pick/pair one).
2. **Build.** `build_project`, then poll `get_build_status` until `ok` or `failed`.
   On `failed`, report `last_error` + `log_tail` and stop — do not deploy.
3. **Deploy.** On a green build, `deploy_to_device`. If a run of this project is
   already live it holds the device slot and the build/deploy is refused with
   `device_busy_by_session` — stop it, say so, and **note that you now owe the
   user a restart** (see *"Deploy" means deploy AND run*).
4. **Run** — for a video pipeline this is part of the deploy, not a separate
   request, and it is also how you repay a run you stopped in step 3. Call
   `run_pipeline`, then branch on what the pipeline produces:
   - **Single-shot** (one image, Model-View): poll `get_pipeline_status` until it
     settles (running → exited_ok / exited_error / killed), then go to step 7.
   - **Streaming** (RTSP, camera, multi-stream, anything continuous): it will
     **never** settle — `running` IS the steady state, and polling for a terminal
     status is how a healthy video run gets mistaken for a hang. Go to step 5.

   Tell the user you're waiting; don't spam polls. For a **Model-View project**
   (`active_view: "model"`) omit `entry_point` — it auto-resolves to the model
   pipeline (`model/main.py`); see the entry-point rule below.
5. **Streaming — verify video stability (MANDATORY).** Work the ladder in
   *Verifying video stability* below: run alive → channels up → channel set holds
   across a second sample → `output_fps` flowing → sender `active`. Do this
   unprompted, before you report anything, and report what you measured.
6. **Streaming — show the streams (MANDATORY).** Invoke `edgematic-view-streams`
   and emit its `edgematic-streams` block as the last element of your reply. Tell
   the user the grid idles when they reply and how to bring it back. Only show
   channels the step-5 ladder found live.
7. **Report.** For a **single-shot** run reaching `exited_ok`: the card shows the
   output — tell the user it renders the image / stream immediately (there is no
   "view results" step to click), and summarise the run: exit code and a one-line
   read of `log_tail` (e.g. "produced the detection tensors"). For a **streaming**
   run there is no exit code to report — report the stability evidence instead:
   how many channels came up against how many you expected, their `output_fps`,
   and the window you observed them over. Either way do **not**
   `fetch_from_device` + parse the primary output yourself — the card renders it.
   Use `fetch_from_device` only if the user asks for a *raw file or log* in the
   workspace.
8. **Stop only when asked.** `stop_pipeline` halts a running pipeline. Whether it
   prompts first is up to the user's approval posture, so do NOT treat a prompt as
   your safety net — under a pre-authorised posture the kill goes through
   silently. Don't reach for it to "restart" a run that is merely still
   running — see the no-stop rule below.

## "Deploy" means deploy AND run — for a video pipeline

A user who asks you to "build and deploy" a **video** pipeline is asking to see
video. "Deployed, not running" is a state that produces nothing, looks identical
to a broken pipeline from the user's seat, and is almost never what they meant.
So for a streaming pipeline, treat *deploy* as **deploy → run → verify → show**,
and say that you are doing it. Stopping at deploy is the single most common way
this flow fails.

The narrow exception is when the user explicitly says not to start it ("deploy
but don't run", "just stage it"). Silence is not that instruction.

### If you STOP a running pipeline to free the device, you OWN restarting it

Build, deploy and run serialize on one per-project device slot, so a live run
blocks a build of the same project (`device_busy_by_session`, 409). Stopping the
run is therefore a legitimate step towards a build the user asked for — but it
creates a debt:

- **Say it before you do it**, naming what is being torn down ("a healthy
  4-camera run at ~28 fps is live; I'll stop it to build, then bring it back").
- **Restart it after the deploy**, then verify and show. Restoring the state you
  destroyed is part of the job, not a follow-up task for the user.
- **Never end a turn having stopped working video and started nothing.** That
  leaves the user strictly worse off than before they asked — the pipeline was
  producing frames, and now the board is dark. This is the one outcome the whole
  flow exists to prevent.

If the run you stopped was healthy and the new deploy fails, restart the previous
deployment rather than leaving the device idle, and say why.

## Verifying video stability

Run this ladder after `run_pipeline` on any streaming pipeline, **before** you
report and before you show the grid. It answers one question: *is the device
pushing frames, and is it still pushing them a moment later?*

1. **The run is alive.** `get_pipeline_status` → `status: running`. If it already
   went `exited_error`, stop here: report `exit_code` + `log_tail`. A live
   pipeline that stays `running` is success, not a hang — don't stop it.
2. **Channels came up.** `count_streams` → `{count, channels}`. An output channel
   exists only once the device has pushed its first annotated frame, which takes
   **seconds to ~2 minutes** after the run starts (model load + first inference).
   So `count: 0` immediately after a run means *not yet*, **not** "no streams":
   poll every ~10 s for up to ~2 minutes before calling it a failure. Never
   "fix" a zero count by starting an input stream — `start_stream` fills input
   slots (1–16) on the way IN and cannot create an output channel (0–79).
3. **They are STABLE, not merely present.** One reading proves a frame arrived
   once; it does not prove video. Sample `count_streams` again after **10 s** and
   require the channel set to be the **same or larger**. Ten seconds of held
   video is the bar — it is long enough to catch the failures that matter (a
   pipeline that emits a frame and dies, a source that ends immediately, a
   channel that drops), and waiting longer buys nothing. A set that shrinks is a
   pipeline dying mid-run — report it with `log_tail`; it is a run fault, not a
   viewing one.
4. **Frames keep flowing.** `get_pipeline_status.log_tail` carries per-stream
   profile lines of the form
   `[profile stream=0] output_fps=… avg_detection_pull_ms=… avg_boxes=…`.
   A non-zero, non-collapsing `output_fps` on **every** expected stream is the
   strongest evidence available without a browser; `avg_boxes` > 0 additionally
   shows detection is producing results. If the pipeline emits no profile lines,
   say so — never invent an fps figure.
5. **The sender is publishing.** `list_output_streams` → for each channel you are
   about to show, `egress.channels[].active` should be `true`. This is a ~10 s TTL
   flag on the SENDER: it confirms insight received something recently, and says
   nothing about the browser.

**Expect one output channel per input stream, and treat a shortfall as a
finding.** A 4-camera pipeline showing 1 channel is a demux/config fault, not a
rounding error — state how many you expected against how many you saw.

Then show the grid (step 6) and report concretely: how many channels, at what
fps, observed over what window. "Deployed and running" is not a report.

**The browser leg is out of scope here.** If this whole ladder is green and the
user still sees a blank or frozen tile, the fault is on the insight→browser leg:
work `edgematic-view-streams`'s triage, then `sima-use-neat-insight`. Never
rebuild, redeploy, restart or stop a healthy run to fix a viewing problem.

## Key rules

- **For a video pipeline the order is build (green) → deploy → run → VERIFY →
  SHOW, and "deploy it" means all five.** Running, verifying stability and
  emitting the streams grid are steps OF the deploy, not extras the user requests
  afterwards — a request that names only "build and deploy" still ends with live
  streams on screen. Stopping at "deployed" leaves a dark device; stopping at
  "it's running" ships an unverified pipeline with nothing to look at.
- **`count_streams: 0` right after a run means "not yet", not "none".** Output
  channels appear only after the first annotated frame (up to ~2 min). Poll
  before concluding — and never answer a zero count by starting an input stream:
  slots 1–16 (in) and channels 0–79 (out) are different namespaces, and
  `start_stream` cannot create the latter.
- **One sample is not stability, and 10 s of held video is enough.** Two
  `count_streams` readings **10 s** apart with a non-shrinking channel set,
  backed by `output_fps` from `log_tail`, is the bar — meet it, then move on.
  Don't sit on a healthy stream longer "to be sure"; report the numbers you
  measured, never "it looks fine".
- **Never rebuild, redeploy, restart or stop a run to fix a VIEWING problem.**
  A blank tile on a green ladder is a browser/WebRTC symptom; restarting
  destroys a healthy run and fixes nothing. Triage via `edgematic-view-streams`,
  then `sima-use-neat-insight`.
- **Respect the order: build (green) → deploy → run.** Deploy fails with
  `project_not_built` if the latest build isn't `ok`; run fails with
  `no_deployment_for_project` if nothing was deployed, and `device_not_paired`
  if the device isn't paired.
- **Deploy also refuses an unfinished config.** If `common/config.yaml` still
  holds a `<...>` placeholder in a VALUE, deploy fails with
  `config_placeholders_unresolved` and names the offending tokens. Fill them
  first: the Insight host comes from `list_output_streams` (`server_ip`) and
  stream URLs from `list_input_streams` (`rtsp`), or from what the user gave you.
  Instructional comments may keep their example tokens — only values are checked.
- **The run command is composed from what the project CONTAINS.** If
  `common/config.yaml` exists the runner appends `--config common/config.yaml`,
  so the entry file must accept that option or the run dies instantly with
  `unrecognized arguments`. If `requirements.txt` exists it is `pip install -r`'d
  ON THE DEVICE before the script — list only packages available on the board,
  and never `pyneat` (the board's venv already provides it).
- **Builds and runs are async — always poll before the next step.** Don't deploy
  right after `build_project`, and don't fetch results right after `run_pipeline`;
  poll the status tool first.
- **One build and one run at a time per project.** Starting a second returns
  `build_already_running` / `run_already_active` — wait and poll instead.
- **Deploy transport (SCP vs NFS) is a property of the device, not an option.**
  `deploy_to_device` auto-selects it; "deploy via NFS" means the device is
  NFS-paired.
- **`fetch_from_device` is confined to the project's own device directory** —
  `remote_path` is relative to it (e.g. `output`, `output/stream_0`); it cannot
  pull another project's or a system path.
- **Model-View entry point: omit `entry_point` — NEVER pass `model/main.py`.**
  A Model-View project (`active_view: "model"`) has an empty placeholder
  `main.py` at the repo root and the real pipeline under `model/`. Deploy and run
  **re-anchor to `model/`**, so on the device the model pipeline is simply
  `main.py` (the re-anchored root *is* `model/`). Call `run_pipeline` with **no
  `entry_point`** and it runs correctly, writing `output/raw.bin`. Do **not** pass
  `entry_point: "model/main.py"` — after the re-anchor there is no `model/`
  subdir on the device, so it fails with `No such file or directory`. And a
  status showing `entry_point: "main.py"` is already that re-anchored model
  pipeline, **not** the empty stub — don't "fix" it by re-running.
- **Don't stop a healthy run — and if you must, put it back.** Single-image
  inference finishes in seconds and a live pipeline runs until stopped — both are
  normal. Only `stop_pipeline` when the user asks, when the run is genuinely
  stuck, or when it holds the device slot a build/deploy the user requested
  needs. That last case is legitimate but incurs a debt: announce the stop, and
  **restart the pipeline after the deploy, then verify and show it**. Ending a
  turn with working video torn down and nothing running is a regression, not a
  completed task. Under a pre-authorised posture nothing prompts you first — the
  judgement is yours to get right.
- **The build installs a model only when it recognises one; otherwise acquiring
  it is your job.** If `get_build_status.log_tail` says the model installer was
  skipped ("no model references" / source unavailable), or a run fails with a
  model-pack error (e.g. `unsupported_extension`/missing `.tar.gz`), acquire the
  model yourself with `sima-cli download <url> -d <dest>` or
  `sima-cli modelzoo --boardtype modalix get <model> -d <dest>`, into
  `<location>/assets/models`, then wire `model.path` in `common/config.yaml`.
  These commands need SiMa Developer Portal auth: if one stalls on an auth
  redirect (HTTP 302 to `auth.sima.ai`) or fails unauthenticated, stop and tell
  the user to run `sima-cli login` first — do not hang waiting, and never claim
  a model was acquired without confirming the file is on disk.

## Error handling

Relay the typed `{code, message}` clearly and suggest the next step. A *failed
build/run* is a normal result (status `failed` / `exited_error`), not a transport
error — read `last_error` / `log_tail` from the record.

| Error / state | Meaning | What to tell the user |
| --- | --- | --- |
| build `status: failed` | Build errored | Show `last_error` + `log_tail`; fix and rebuild. |
| `build_already_running` | A build is in flight | Wait — a build is already running; I'll poll it. |
| `project_not_built` | Deploy/run before a green build | Build the project first. |
| `config_placeholders_unresolved` | `common/config.yaml` still has `<...>` in a value | Name the tokens; fill them (`list_output_streams` → `server_ip`, `list_input_streams` → `rtsp`) and redeploy. |
| `no_deployment_for_project` | Run before a deploy | Deploy the project to the device first. |
| `device_not_paired` | Target device not paired | Pair the device first (see device management). |
| `run_already_active` | A run is already active | Wait or stop the current run before starting another. |
| `device_busy_by_session` | Another action (a live run) holds the project's device slot | Name what holds it. If it is a run and the user asked to build/deploy, say you're stopping it, then **restart it after the deploy** and show the streams. |
| run `status: exited_error` | The run failed on-device | Show `exit_code` + `log_tail`; suggest fixing and re-running. |
| run `log_tail` shows a model-pack error (`unsupported_extension`, missing `.tar.gz`, `<model-path>`) | No usable model was installed | Report that the model isn't provisioned / the catalogue is unavailable; don't retry blindly or call auth-gated download CLIs. |
| `device_unreachable` | Device offline | Check power/network and retry. |
| `nfs_unavailable` | NFS device left the LAN | Offer to switch it to SCP and retry. |
| `deploy_failed` / `fetch_failed` | An scp step failed | Report the message and offer to retry. |
| run `running` but `count_streams: 0` after ~2 min of polling | The pipeline started but never emitted an output frame | Report it as such with `log_tail` (model/source/config fault). Do NOT start an input stream and do NOT redeploy blindly. |
| channel set SHRINKS between two `count_streams` samples | The pipeline is dying mid-run | Name the channels lost and show `log_tail` — a run fault, not a viewing one. |
| fewer output channels than input streams | Demux / per-stream output config fault | State expected vs seen (e.g. "4 cameras, 1 output channel") and point at the pipeline's output config. |
| ladder green but the user sees blank/frozen tiles | The insight→browser leg | Triage with `edgematic-view-streams` → `sima-use-neat-insight`. Never restart the pipeline. |

## Boundaries

- Builds/deploys/runs existing projects and pulls results; does not create
  projects or edit the pipeline graph.
- Owns *verifying* that a deployed video pipeline is producing stable output
  (device→insight leg). Rendering the grid is `edgematic-view-streams`;
  diagnosing the browser leg is `sima-use-neat-insight`. Verification and the
  grid are still required steps here — delegating the rendering does not make
  showing it optional.
- Device pairing / listing / removal is out of scope here — use
  `edgematic-device-ops`.
- One project, one device, one run per action; no bulk operations.

## References

- `references/build-deploy-run-api.md` — the build / deploy / run / fetch tools,
  their underlying endpoints, request/response shapes, and error codes.
