---
name: edgematic-ros2-neat-nodes
description: Use when the user wants to build, run, or introspect the SiMa ROS2 Neat pipeline (yolov8_seg / neat_inference) on a paired Modalix DevKit from chat — "build a ROS2 YoloV8 pipeline and run on device", "show me the ROS topics", "show me the ROS (neat) nodes", or checking that segmentation detections are publishing. Covers the agent tools run_ros_pipeline / ros2_topic_list / ros2_node_list, the yolov8_seg topic contract, and when to auto-open Flora. Do NOT use for foxglove_bridge start/Flora rendering itself (see edgematic-foxglove-viz), device pairing/status (see edgematic-device-ops), or Edgematic model-archive projects (build_project/run_pipeline — a DIFFERENT, non-ROS flow).
---

# ROS2 Neat Nodes (yolov8_seg) on a Modalix DevKit

The DevKit runs the SiMa **`vdp-simaai-ros2`** workspace (branch
`neat_integration`), whose `yolov8_seg` package is a single NEAT-native
**`neat_inference`** lifecycle node — it decodes an RTSP feed, runs YOLOv8
segmentation on the MLA, and publishes the results. The workspace is
pre-provisioned on the board (typically at `/media/nvme/ros-work/vdp-simaai-ros2`);
you drive it over SSH through three agent tools — you do **not** need the
terminal for these.

## Board prerequisites (one-time, done outside Studio)

Assumed already in place; if `run_ros_pipeline` fails to build/run, these are the
usual cause:

- **Neat core `0.2.1`** installed on the DevKit — `sima-cli neat install
  core@v0.2.1` (C++ pipelines; PyNeat not needed). This provides
  `libsima_neat.so.3`, which `libneat_inference.so` links against. A version
  mismatch surfaces as a `dlopen error: libsima_neat.so.3: cannot open shared
  object file` at node load.
- **Rebuild after any neat reinstall.** Any `sima-cli neat install` / NEAT deb
  reinstall invalidates `build/` — the fix is `rm -rf build/yolov8_seg` then
  rebuild (`run_ros_pipeline` runs `build.sh`, which is a no-op if CMake sees
  nothing stale, so a stale `.so` needs the `rm -rf` first, over the terminal).
- **RTSP input from Edgematic Streams.** The pipeline decodes an RTSP feed, and
  that feed must be one Studio started (see below). The params file on the board
  carries whatever address was last written into it — often a hand-started
  server that is no longer reachable — and `run_ros_pipeline` accepts `device`
  alone and will run against it, publishing nothing. Never leave it on the
  baked-in default.

Full board-setup runbook (flash, ROS2 + Neat install, foxglove_bridge): the
`edgematic-ros2-integration` skill and its `ros2-pipelines-on-som` reference.

## The three tools

- **`run_ros_pipeline`** `{ device, package?, rtsp_url?, source_width?,
  source_height?, fps? }` — builds (`./build.sh`) then runs
  (`./run.sh`) the `yolov8_seg` package on the board. **`status:"started"` means
  "the launcher was spawned", NOT "the pipeline is running"** — it returns the
  same value when the launch dies immediately, so never report success on the
  strength of it alone. Confirm with `ros2_node_list` (expect `/neat_inference`)
  or `ros2_topic_list` before telling the user it is up. The launch is
  **detached**, so the tool returns immediately with `{status:"started", package,
  log}` while the build+run keep going (build is ~seconds when already built, longer on a
  fresh tree). It does NOT block your turn. This is the tool for "build a ROS2
  YoloV8 pipeline and run on device" — NOT `build_project`/`run_pipeline`, which
  are for Edgematic model-archive projects, not the ROS2 colcon workspace.
  **Re-running is safe and is the normal case** — the launch stops whatever was
  already running for that package before starting, so never ask the user to
  stop the old one first, and never refuse to re-run because something is up.
  The reply's **`replaced_running`** says how many it displaced: `0` is a fresh
  start; anything higher means the output the user is watching has just
  restarted and will be blank for a few seconds — **say so**, because otherwise
  the gap reads as a failure.
- **`ros2_topic_list`** `{ device }` — `ros2 topic list` over SSH → the advertised
  topics. Use for "show me the ROS topics".
- **`ros2_node_list`** `{ device }` — `ros2 node list` over SSH → the running
  nodes (`/neat_inference`, `/yolov8_seg_neat_container`, `/foxglove_bridge`).
  Use for "show me the ROS (neat) nodes".

All three take the paired device by name or id. A transport failure surfaces as
`device_unreachable`; a non-zero board-side exit as `ros_command_failed`.

## Topic contract

Once the pipeline is up (a healthy run publishes at a few Hz):

| Topic | Type | What it is |
| --- | --- | --- |
| `/detections_overlay` | `sensor_msgs/Image` (bgr8) | frame + segmentation masks/boxes |
| `/detections` | `simaai_common/msg/DetectionArray` | per-instance boxes + masks |
| `/image_raw` | `sensor_msgs/Image` (bgr8) | decoded input frame |

If `ros2_topic_list` shows these topics but no frames are visible in Flora, the
node is likely **active but publishing 0 frames** (a stale/wedged instance) —
re-run `run_ros_pipeline` to restart it fresh.

## Example pipelines (neat_integration branch)

The `vdp-simaai-ros2` (`neat_integration`) workspace ships several NEAT example
pipelines under `packages/`. Pass the one you want as `run_ros_pipeline`'s
`package`; `yolov8_seg` is the default demo. When the user asks to "show the
examples", list these with a one-line description each.

| Example (`package`) | What it does | Key topics → relevant panels |
| --- | --- | --- |
| **`yolov8_seg`** (default) | YOLOv8 instance **segmentation** (masks + boxes) | `/detections_overlay` (Image), `/image_raw` (Image), `/detections` (DetectionArray) |
| **`yolov8`** | YOLOv8 **object detection** (boxes only) | `/detections_overlay` (Image), `/detections` (DetectionArray) |
| **`yolo_pose`** | YOLO **pose** estimation | `/image_raw` (Image), `/simaai/genericrender/output` (annotated Image) |
| **`yolov8_seg_sensor_fusion`** | seg + Intel **RealSense** depth fusion | `/…/color/image_raw`, `/…/depth/image_raw`, `/simaai/segmentation/detections`, `/simaai/sensor_fusion/output` |
| `yolov8_rover` / `yolov8_seg_rover` | rover variants — **only on the Husarion ROSBot XL** | as above + rover odom/cmd_vel |

All publish `/neat_inference/transition_event` (lifecycle state). For Flora, the
inline card's default panels (overlay + raw + detections + pipeline-state) fit
`yolov8_seg`/`yolov8`; for `yolo_pose` prefer the render-output image, and for
sensor-fusion the RealSense color/depth + fusion output.

## Feeding the pipeline an Edgematic stream (RTSP input)

The pipeline decodes an RTSP feed. To have it consume a stream the user started
in Edgematic (the Streams panel), chain the media tools with `run_ros_pipeline`:

1. Ensure a stream is playing. If the user hasn't started one, do it for them:
   `add_video { name: "sample_detection.mp4" }` (downloads a sample clip; or no
   `name` to prompt an upload) → `start_stream { video: "sample_detection.mp4" }`.
   `start_stream` returns `{ index, rtsp, webrtc }` — grab the **`rtsp`** URL
   (shape `rtsp://<host>:8554/src<N>`).
2. `run_ros_pipeline { device, rtsp_url: "<that rtsp URL>", source_width,
   source_height, fps }` — this rewrites the pipeline's input to that stream and
   runs it (no rebuild).

   **The three geometry fields are required whenever `rtsp_url` is passed** —
   the call is refused without all three, so `{ device, rtsp_url }` alone fails.
   They describe the **incoming feed**, not a preference: a value that does not
   match the real stream corrupts the pipeline's memory instead of failing
   cleanly, which makes a wrong number worse than a missing one. Read them from
   the clip you started. Do not copy the pipeline's existing defaults and do not
   guess. Studio does not yet record geometry on the stream it starts, so if you
   cannot establish it, say so and stop rather than launching on a guess.

   **Verify the host is board-reachable before blaming the pipeline.** The
   stream tools report the *host's* view of itself, which is not always the
   address the board can route to (measured: one host answered on
   `172.16.1.208` from the board while `172.16.1.114` — the reported endpoint —
   was unreachable). A wrong host here produces a pipeline that runs happily
   with **`/image_raw` at 0 Hz** and a blank overlay, and no error anywhere.
   If frames never arrive, say so plainly and have the user run
   `ros2 topic hz /image_raw` and `nc -z <host> 8554` from the DevKit terminal.

   A geometry that disagrees with the clip shows as `Caps negotiation failed:
   framerate mismatch` repeating in the run log with nothing decoding — that is
   the benign half of getting it wrong, and the reason to read the values off
   the stream rather than reconcile them afterwards.
3. Then introspect / open Flora as below.

If the user already started a stream, call `list_input_streams` to get its `rtsp`
URL and pass that. Everything is automatic from one prompt like "stream a sample
video and run the pipeline on it".

## Recommended flow for "build and run on device"

1. Confirm a DevKit is paired (else offer the `/devices` navigate pill).
2. Call `run_ros_pipeline { device }`. It returns `status:"started"` immediately —
   tell the user the pipeline is building+running on the board.
3. End the reply by **auto-opening Flora** with the directive (no click):

   ````
   ```edgematic-flora
   ```
   ````

   and offer inspection pills:

   ````
   ```quick-actions
   [
     { "type": "prompt", "label": "Show me ROS topics", "prompt": "List the ROS topics on the DevKit" },
     { "type": "prompt", "label": "Show me ROS nodes",  "prompt": "List the ROS nodes on the DevKit" }
   ]
   ```
   ````

Flora rendering + `foxglove_bridge` start are owned by the
`edgematic-foxglove-viz` skill; starting/stopping the RTSP input is
`edgematic-media-streams`.

## "It says started but there is no output"

The three failures below all present identically — `status:"started"`, topics
advertised, nothing on screen — so diagnose in this order rather than guessing.

1. **Nothing launched.** The detached child died on startup while the spawning
   SSH call still exited 0. Check `ros2_node_list` for `/neat_inference`; if it
   is missing, read the board log named in the tool's `log` field. Two causes
   both kill the launch *before its first line runs*, because a shell applies
   redirections before executing anything:
   - `PermissionError: '/root/.ros'` — the command exported a `HOME` the SSH
     user cannot write, and ROS2 `launch` creates its log directory first.
   - the log file itself is not writable (a root-owned leftover from a run
     started with `sudo`). Nothing is appended, so the log looks *stale* rather
     than empty — always compare its mtime against the board's `date` before
     concluding anything from its contents.

   **Never diagnose a running pipeline with `pgrep -x component_container_mt`.**
   `-x` matches `comm`, which the kernel truncates to 15 characters; the name is
   22, so it reports zero for a process that is very much alive and will
   convince you the pipeline is dead. Use `pgrep -f "component_container_m[t]"`
   — the bracket keeps the pattern from matching the command carrying it.
2. **Launched, but the source is stale.** The node is up and topics are
   advertised, yet nothing is decoding. Restarting the RTSP stream *underneath*
   a running pipeline does this: the board's source never reconnects and the
   pipeline sits idle forever. The tell is a board log whose newest line is
   minutes older than `date` — a healthy run appends continuously. Fix by
   restarting the pipeline **after** the stream, never before.
3. **Running fine, but the video has nothing to detect.** `/detections`
   publishes with `num_detections: 0` and the overlay draws no boxes. This is
   not a fault — sample clips often hold long empty stretches, so a user
   watching a live panel sees "no detections" most of the time. Confirm before
   debugging anything else: a healthy node logs `decoded N seg instances` per
   frame, and `N` genuinely tracks what is on screen. Sample the topic over
   ~30s and count non-zero frames rather than trusting a glance at the panel.
