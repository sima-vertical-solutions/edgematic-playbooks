---
name: edgematic-foxglove-viz
description: Use when the user asks to visualize, see, watch, or monitor a running pipeline's live output in the bundled Flora (Foxglove-fork) app — the annotated detection overlay, per-instance segmentation masks, or the raw camera feed — connected over the DevKit's foxglove_bridge WebSocket. Covers the yolov8_seg ROS2 pipeline's topic contract (/detections_overlay, /detections, /image_raw), guiding the user through board-side prerequisites (ROS2 workspace build, pipeline start, foxglove_bridge launch, RTSP input) over the built-in SSH terminal, constructing the Flora auto-connect URL, and when to emit the "Open in Flora" quick-action pill. Do not use for starting/stopping the underlying RTSP/WebRTC media stream itself (see edgematic-media-streams), device pairing/status (see edgematic-device-ops), or building/deploying/running the pipeline (see edgematic-build-deploy-run).
---

# Edgematic Foxglove Visualization (Flora)

## Overview

> **Never name the visualizer to the user.** "Flora", "Foxglove", and "the
> Foxglove app" are implementation detail; the user is looking at Edgematic
> Studio's **live output**. Say "the live output", "the detailed output view",
> or "the detections panel" — the surface itself carries no other product's
> name, and your prose must not reintroduce one. The names below are for your
> understanding of the plumbing only.

**Flora** — a Foxglove Studio fork (MPL-2.0) — is Edgematic's bundled
visualization surface, served as a static SPA at **`/flora`** on this same
Studio server. It renders live ROS2 topics by connecting directly to the
DevKit's **`foxglove_bridge`** over a browser WebSocket
(`ws://<devkit-ip>:8765`) — there is no server-side proxy or agent tool in the
loop once the connection is open; Flora talks straight to the board.

Use the available Studio tools and the provider shell to inspect and repair the
board within the user’s requested scope. For SSH, use the managed identity and
known-hosts path returned by `list_devices`; `connect_device` repairs pairing.
See `edgematic-device-ops` for that contract. Surface live output in either form:

- **Offer a `flora` quick-action pill** when you are merely *offering* the option
  (one click opens the embedded Flora pane).
- **Emit a ```edgematic-flora``` fenced block as the last line of your reply** to
  open the embedded pane **automatically, with no click** — do this when the user
  asks to *see / open / show* the live output, especially "open it automatically"
  / "don't make me click". Empty body targets the active DevKit; `{ "url":
  "ws://<host>:8765", "panels": ["overlay", "raw", "detclean"] }` overrides the
  target and panel selection in Studio versions supporting directive panels. A pipeline must be running (a Studio run, OR
  the user's word that a board-side pipeline is up) and a DevKit paired — trust
  the user; do not require a tool call to confirm the run. Never answer such a
  request with prose alone.

The one board-side thing that is **no longer manual** is `foxglove_bridge`
itself: Studio can probe it and start it over SSH. Both Flora pills handle that
automatically — if the bridge is down when the user clicks, the frontend starts
it and only then opens Flora. So **do not** walk the user through
`ros2 launch foxglove_bridge …` as a prerequisite unless they ask, or unless a
pill has already reported that the bridge could not be started.

For a packaged demo or clean-board QA, "Studio can start it" is not evidence
that the package exists. Before an expensive build/deploy, verify the payload
supplies `foxglove_bridge` or that the target image guarantees it. A bridge
found on one previously used board must not become an undeclared prerequisite.

Starting/stopping the RTSP input stream is **not** this skill — hand that off to
`edgematic-media-streams`.

## The yolov8_seg ROS2 pipeline contract

The board runs the `yolov8_seg` ROS2 package from the SiMa ROS 2 client
workspace it was provisioned with. Once it and `foxglove_bridge` are up, these
topics are live:

| Topic | Message type | What it is | Renders in |
| --- | --- | --- | --- |
| `/detections_overlay` | `sensor_msgs/Image` (`bgr8`) | The camera frame annotated with color-tinted per-instance segmentation masks + bounding boxes, baked into the pixels | Any Foxglove **Image** panel — this is what you want front-and-center |
| `/detections` | custom `simaai/DetectionArray` | Structured boxes + per-instance ~160×160 masks | **NOT** renderable by a stock Image/3D panel (custom message type) — use a **Raw Messages** panel to inspect the fields |
| `/image_raw` | `sensor_msgs/Image` | The un-annotated decoded camera frame, pre-inference | Any Foxglove **Image** panel |

`foxglove_bridge` listens on **port 8765** by default — this is the port
Flora's `ds.url` connects to, not the RTSP port (8554) or the WebRTC port
(8081) used for the raw video stream itself.

The bundled Flora default layout already opens `/detections_overlay` in an
Image panel and `/detections` in a Raw Messages panel side by side, so a
fresh connection shows something useful with zero manual panel setup.

## Board-side prerequisites

Verify these using the available tools or managed SSH:

1. **ROS2 workspace built.** `./build.sh yolov8_seg` (one-time, or after the
   workspace is updated).
2. **Pipeline started.** `./run.sh yolov8_seg` (foreground) or
   `./run.sh yolov8_seg --bg` (background, so the terminal is free for the
   next command).
3. **RTSP input live.** The pipeline's params yaml points `rtsp_url` at the
   **host's** neat-insight RTSP server (port **8554**), so a mediasrc slot
   must already be streaming before the pipeline has frames to annotate —
   start one via the **Streams** page or the `edgematic-media-streams` skill
   (`start_stream`) *before* step 2, or the pipeline will sit waiting for
   input.

`foxglove_bridge` is deliberately **not** on that list: Studio starts it for
the user as part of either Flora pill. Mention it only when a pill reports it
could not be started (see Troubleshooting).

Confirm the device is paired first (`edgematic-device-ops` — `list_devices` /
`get_device_status`) and get its `host` (IP) — you need it to build the Flora
URL below.

### What Studio knows about the bridge

`GET /devices/{id}/foxglove` reports the bridge's live state, and the UI gates
both Flora affordances on it, so you can rely on the pill doing the right thing
rather than pre-flighting the board yourself:

| Report | What the UI does |
| --- | --- |
| `status: running` | Opens Flora directly. |
| `status: stopped`, `control_enabled: true` | Starts the bridge over SSH, waits for the port, then opens Flora. |
| `status: stopped`, `installed: false` | Refuses — the ROS2 package isn't on the board. Tell the user to install `foxglove_bridge`. |
| `status: stopped`, `control_enabled: false` | Refuses — this deployment doesn't drive the board. Walk the user through `ros2 launch foxglove_bridge foxglove_bridge_launch.xml port:=8765` over the terminal. |
| `status: unknown` | Lets the user try anyway — the probe couldn't tell, and blocking would be worse than a possible retry. |

## The Flora URL

Once the board side is up, the auto-connect URL is:

```
<server-origin>/flora/view?ds=foxglove-websocket&ds.url=ws://<devkit-ip>:8765
```

- `<server-origin>` is this Studio server's own origin (the browser's current
  origin — Flora is same-server, not a separate host).
- `<devkit-ip>` is the paired DevKit's `host` field.
- The default layout (baked into the bundle) opens with
  `/detections_overlay` + `/detections` already selected — no manual panel
  setup needed on the user's part.

Give the user this URL only if they ask for it directly; normally you offer
it as the quick-action pill below instead (the UI substitutes the real IDs).

## Which pill to emit

There are two, and picking the right one is the whole decision:

### `publish` — the pipeline is NOT running yet

When the user asks to **build / run / deploy** the application, or asks to see
its output *before anything is running* ("build yolov8_seg", "run it and show
me the detections"), emit:

```quick-actions
[{"type":"publish","label":"Build & run on DevKit"}]
```

One click runs the entire chain — host-side RTSP input provisioning → build →
deploy → run — and then opens the live Flora view **automatically**, both
embedded in the chat and in a new browser tab. You do not need to offer a
Flora pill afterwards, and you must not chain separate build/deploy/run
`http` pills to achieve the same thing.

Requires a paired DevKit. It does **not** require a prior successful build —
it builds as part of the chain — so it is the right pill for a project that
has never been built.

For ROS packages, use the applicable ROS build/deploy skill and verify the
actual launch before presenting its output.

### `flora` — the pipeline IS already running

When the pipeline is already up and the user just wants to look at it, end
your reply with **both** of these buttons, so one click lands on the view they
want instead of opening the surface and hunting for panels:

```quick-actions
[{"type":"flora","label":"Show overlay","panels":["overlay"]},{"type":"flora","label":"Detections + overlay","panels":["overlay","detclean"]}]
```

- **Show overlay** — the annotated video on its own, full width. This is the
  default ask ("show me the detections", "let me see it running").
- **Detections + overlay** — the same video beside a table of what was
  detected (class, score, box). Offer this when the user is checking *what*
  was found or debugging accuracy, not just watching.

`panels` accepts `overlay`, `raw`, `detclean`, `detlist`, `detections`,
`state`, `odometry`, and `frames`. Prefer `detclean` for a detections table — `detections` is the raw
message dump (segmentation mask bytes included) and is unreadable in chat.
Omitting `panels` keeps whatever the surface is already showing.

Emit these once the board-side prerequisites above are satisfied (pipeline
running, RTSP input live) — if either is still missing, walk the user through
it first. You do **not** need the bridge to be up: the pill starts it. Don't
offer them for a project that has no camera/detection pipeline at all.

## Detailed-output acceptance and diagnosis

A board process launched through managed SSH can be viewed directly. The
`edgematic-flora` directive and `flora` actions do **not** require a Studio
`active_run_id`. A registered publish card is a separate entry point; do not
explain a missing chat action by inventing a run-record prerequisite.

Use the explicit verified bridge URL in the directive, especially when the
selected device differs from the target. The directive supports the same
`panels` vocabulary as the quick action. Completed historical directives keep
a **View detailed output** action; only the latest reply auto-opens. Quick
actions in a recovered conversation retain its latest explicit directive target.
On older Studio builds without directive-panel support, use a `flora` quick
action for the panel selection.

Verify the complete browser path: restored chat → output action → mounted
detailed pane → actual advertised topics and messages → pop-out. A unit test
of the pane alone cannot prove the Studio shell mounts it. If clicking changes
state but no pane appears, inspect the shell consumer and the chat’s embedded
Flora wiring before restarting a healthy pipeline.

The detailed topic browser must follow the current bridge graph, including
custom, slow, static and subsequently advertised topics. A short activity probe
only helps choose initial panels; it is not the authority for hiding the topic
browser or filtering its graph. An SSH readiness poll must not tear down a
working browser WebSocket. Pop-out must stop the embedded subscriber only after
the new window opens successfully; a blocked window leaves the current view usable.

For remote camera output, keep full-resolution `sensor_msgs/Image` for inference
and publish paced JPEG `sensor_msgs/CompressedImage` topics for browser display.
Include both compressed topics in the bridge whitelist. The existing
`edgematic-ros2-demo/scripts/jpeg_republisher.py` supports multiple `--topic`
arguments, `--quality 70`, and `--max-fps 10`; copy it into the generated package,
install it and launch it with the app. Bind panels to the **verified live** topics,
not a hardcoded default. Merely installing image_transport does not create a
compressed publisher for a plain rclpy Image publisher.

Validate raw camera, annotated output and detection messages for at least
0/30/60 seconds in the detailed view and the pop-out. Record the topic names,
message/frame counts, reconnects and visible panel errors. Do not claim that
an advertised topic proves frames render, or that a queued-byte count alone
proves network saturation. Preserve URDF TF; do not imply stationary joint
states or transforms are measured odometry.

## Troubleshooting

| Symptom | Likely cause | What to tell the user |
| --- | --- | --- |
| Flora tab opens but never connects / spins on "Connecting…" | A firewall blocks 8765, or the bridge died right after starting | The pill starts the bridge, so a dead connection here usually means the port is blocked: `nc -z <devkit-ip> 8765` from the host. Also check `/tmp/edgematic-foxglove-bridge.log` on the board — that's where the launch output goes. |
| "foxglove_bridge did not come up in time" | The bridge process started but never opened its port — usually a missing ROS environment or a port already taken | `cat /tmp/edgematic-foxglove-bridge.log` on the board. If the ROS env is the problem, check `/opt/ros/*/setup.sh` exists; if the port is taken, `ss -ltn \| grep 8765`. |
| "foxglove_bridge is not installed on the DevKit" | The ROS2 package is absent | Install it on the board (`sudo apt install ros-$ROS_DISTRO-foxglove-bridge`, or build it into the workspace), then retry. |
| Image panel stays black / no frames | RTSP input isn't live, or the pipeline hasn't started | Confirm a mediasrc slot is streaming (`edgematic-media-streams` — `list_input_streams`) and that `./run.sh yolov8_seg` is running. |
| `/detections` panel shows nothing / errors | Using an Image panel on `/detections` instead of Raw Messages | `/detections` is a custom message type — it only renders in a **Raw Messages** panel, never an Image panel. |
| Pipeline process won't stop cleanly | `Ctrl+C` sometimes leaves it wedged | `kill -USR2 <pid>` for a clean shutdown (the pipeline's signal handler). |
| Board seems generally stuck / dispatcher unresponsive | The SiMa app-complex dispatcher wedged | `systemctl restart simaai-appcomplex.service`, then re-run steps 2–3. |
| Flora loads but the page is blank / mixed-content console error | Studio served over `https://` while `ds.url` is `ws://` (not `wss://`) | Browsers block insecure `ws://` from an `https://` page. This flow assumes Studio is served over plain `http://` on the LAN — see `docs/demos/flora-yolov8-demo.md`. |

## Boundaries

- Starting/stopping the RTSP input stream is `edgematic-media-streams`'s job,
  not this skill's — reach for it before or alongside these steps when the
  input isn't live yet.
- Device pairing/status is `edgematic-device-ops`; building/deploying/running
  the pipeline itself is `edgematic-build-deploy-run`. This skill only covers
  getting the *visualization* connected once those are already in place.

## References

- `docs/demos/flora-yolov8-demo.md` — the full end-to-end demo script this
  skill supports, with numbered steps and the same troubleshooting table.
