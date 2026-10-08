---
name: edgematic-ros2-contract-builder
description: Generate, build, deploy, run, and verify a new ROS 2 package from a user prompt and robot contracts. Derive hardware facts from the GitHub repository supplied in the prompt and an expanded URDF; materialize evidence, build target, and acceptance contracts before generation. Use when no implementation package exists and Edgematic AI must discover relevant sensors and drivers, author the package, expose live output in Flora, and provide a read-only operator TUI; route an existing package to edgematic-ros2-user-package.
---

# Edgematic ROS 2 Contract Builder

Before deriving the application graph, follow
[SiMa-first component selection](../edgematic-ros-capabilities/references/sima-first-selection.md).
Reuse compatible SiMa models, artifacts, Neat and ROS components; generate only
the missing application logic or adapters. Include selection and fallback
evidence in the project alongside its contracts.

Turn an expanded robot contract into working source code and runtime evidence.
This skill owns the gap between a confirmed ROS application graph and an
existing package: **the agent authors the package with `write_file`**. Do not
stop after describing components, producing a graph, or telling the user to
write the implementation.

Load `edgematic-ros2-portable-pipeline` for build, staged deployment, board
preflight, detached launch, and runtime verification. Load
`edgematic-ros2-board-setup` before running on a Modalix DevKit. If source code,
`package.xml`, or a launch file already exists, route to
`edgematic-ros2-user-package` instead.

## Resolve the input contract

Start with the user's prompt and robot/vendor GitHub link. Inspect that source
at an immutable revision. Use an uploaded expanded `robot.urdf`, or locate and
expand the URDF from the supplied repository with its declared dependencies.
If neither source is available, ask for the missing source; never select a
built-in robot profile, customer implementation, or remembered hardware default.

Read [contract file requirements](references/contract-files.md). Resolve one
layout, either the project root or `input/`, and materialize these four artifacts:

1. `robot.urdf` — fully expanded model from the supplied source.
2. `robot_contract.yaml` — evidence sources, interfaces, expected sensors,
   driver constraints, and unresolved facts. Copy only facts established by the
   selected source, exact URDF, and read-only device inspection. Record source
   URLs, immutable revisions and the evidence for each hardware fact.
3. `build_target.yaml` — ROS distribution, architecture, SDK, middleware,
   board class and build constraints observed on the selected SDK and board.
   Record the command/API and value for mutable fields. Leave unknown values
   null with a reason; required unresolved fields block their build/run step.
4. `acceptance.yaml` — requested input, nodes/topics/types/rates, visible output,
   TUI checks and whether physical motion is required. Choose input from the
   prompt and supplied application: `rosbag`, `live` (including `managed_rtsp`),
   or explicitly requested file input. Do not silently replace a live camera
   request with replay. Physical motion requires the user's requested scope and
   a validated motion contract; keep the generated monitoring TUI read-only.

Reconcile existing user-supplied files without silently replacing conflicting
facts. Device identity, calibration, controller limits and safety policy remain
unresolved until supported by evidence; URDF topology alone does not prove them.
Write absent contracts with `write_file`, then re-read all four before deriving
the application. These are project artifacts, never additions to shared skills.

## 1. Establish evidence, without borrowing the answer

After all four files are present, call `discover_ros_contract` with the prompt,
expanded URDF, selected input mode, no-motion default, and the observed build
target. Pass a target object only when its required fields are complete; an
incomplete materialized target stays explicit rather than being replaced with
stale values. The tool reports only what the model proves and which facts remain
missing. Then resolve relevant gaps automatically in this order:

1. the materialized contract files;
2. the selected target's installed SDK and `sima-core` interfaces;
3. the paired board, using read-only inspection for detected devices, OS,
   architecture, runtime versions, and available interfaces;
4. the robot or sensor vendor's official documentation, URDF, driver repository,
   and package manifests at a recorded revision;
5. ROS package indexes and upstream interface documentation.

Do not inspect or copy any pre-existing implementation for the same robot when
the request says this is an AI-generation proof. Use only the robot vendor's
public sources to establish robot-specific hardware facts; they must not become
an unacknowledged code transplant. Record every external repository URL and
immutable revision under `docs/evidence.md` in the generated project.

Classify each fact as `proven`, `vendor_supported`, `observed`, `assumed_for_demo`,
or `unresolved`. Never infer wire protocols, device paths, calibration, safety
limits, or production motion behavior from link or joint names.

### Demo-scope exception

When `physical_motion_required: false`, build a read-only, perception-driven
proof from the explicitly selected rosbag, managed RTSP, or direct USB V4L2 input.
Missing motor-controller transport, command limits, safety interlocks, and live
base-driver details are production blockers, but they do **not** block package
generation for a no-motion camera demo. Keep them in
`docs/production-gaps.md`, do not instantiate a motion command publisher, and
make the TUI incapable of driving the robot.

Only hardware that participates in the requested demo can gate generation. For
example, a camera-perception run does not wait for a live lidar driver, even
when the URDF contains a lidar frame. Prefer recorded ROS input for message-level
fidelity. A managed RTSP stream is a live network input, not proof of the
robot-mounted camera driver. For direct USB, use only the selected `/dev/v4l/by-id/`
device and measured capture format; never probe other video nodes or fall back
to a network source. Use a file publisher only when the acceptance
contract explicitly selects file input for this application.

## 2. Derive and confirm the application

Call `derive_ros_application` with the acceptance contract's `input_mode`,
the typed `input_source` for live mode, and an explicit `rosbag_loop` for
rosbag mode, then `inspect_ros_application`. Pass the same typed source to
`discover_ros_contract` and to any source-changing adjustment. For USB V4L2,
include the exact device, measured width/height/FPS/pixel format, a frame in
the selected URDF, raw/compressed topics, client bringup package and
`fallback: none`.
`managed_rtsp` maps to application input mode `live`; never disguise it as
`file` merely because an older tool schema lacks live derivation. If the loaded
tool does not advertise the selected mode, report that exact tooling gap and
stop before generation. Reconcile the derived result with the four materialized
files and the evidence classifications. Use
`adjust_ros_application` to remove unsupported motion or to correct topics,
QoS, bridge allowlists, rosbag looping, and confirmed sensors. A
`sensor_confirmations` value of `false` explicitly excludes that sensor from
this application without removing its URDF frames; use it for optional sensors
that are outside the accepted demo scope.

Present one compact confirmation summary: active sensors, input mode, components,
topics and types, target, deliberate exclusions, and production gaps. Call
`confirm_ros_application`. Do not generate until the persisted lifecycle is
`confirmed`; do not repeatedly ask after the same gate has been approved.

## 3. Generate a complete package

When this generated application will use `open_ros_workspace` and
`prepare_ros_build`, establish the registrar's layout **before** opening the
workspace: the application has its own client directory beside the core
directory containing `capabilities/`. Put the generated ROS package under the
client's `src/`, and put its `deploy.yaml` (including `bringup`), build/run
scripts, model references, and contracts in that same client directory. Call
`open_ros_workspace` on their common parent only after those files exist.
Do not put the generated package or `deploy.yaml` at the common parent root;
other sibling directories cannot identify the client for the registrar. Check
that exactly one sibling client has a valid `deploy.yaml` before registering.

Use `write_file` with project-relative `name` and whole-file `content`. Create a
self-contained package or workspace with at least:

- `package.xml` and `CMakeLists.txt` or `setup.py`/`setup.cfg`;
- launch files and deterministic parameters;
- the expanded URDF and `robot_state_publisher` wiring;
- rosbag, managed-RTSP, direct USB V4L2, or file input adapters chosen by the contract;
- when the selected rosbag fixture is not already uploaded, a deterministic
  real-video-to-rosbag generator plus the generated bag itself; the missing
  fixture is a package-generation task, not a fifth required user upload or a
  blocker. Use a real scene with ordinarily detectable objects, record its
  source and license, and never substitute a generated rectangle unless the
  acceptance contract explicitly asks for synthetic imagery;
- perception publishers for both a renderable image and structured results;
- every runtime-loaded ROS plugin selected by the graph (for example the
  `compressed_image_transport` publisher/subscriber plugin), with an official
  upstream source pinned and cross-built into the payload when the target SDK
  or image does not guarantee it; declaring the client API package alone is not
  dependency closure;
- `/tf`, `/tf_static`, odometry, and joint-state wiring required by acceptance;
- `foxglove_bridge` topic configuration limited to the accepted allowlist, plus
  an explicit runtime source for the bridge: either prove the target image
  guarantees it or fetch an official upstream revision and cross-build it into
  the deploy payload; a bridge found on a previously used board is not proof;
- a read-only TUI executable showing node presence, topic type/rate, lifecycle,
  and recent log state; the only interactive actions may be refresh, help, and
  quit — never velocity or actuator commands;
- launch, contract, and package tests; build/stage/run scripts; and a README
  that separates demo guarantees from production gaps.

Prefer standard ROS messages for visible output. The Flora image topic must be
`sensor_msgs/msg/Image` or `sensor_msgs/msg/CompressedImage`; structured results
must retain their real type. Give every generated node a stable name. Do not
claim a driver exists merely because its topic is replayed: name replay nodes
as replay or fixture publishers.

Bridge the exact camera source topic as well as inference output. If the bag
publishes `/camera/image_raw/compressed`, the allowlist and live layout must
include that exact topic; `/image_raw/compressed` is not an alias. For managed
RTSP, use the active raw image topic and record the managed stream identity plus
measured width, height, and frame rate. For USB V4L2, implement and test the
capture component in the client package; a graph component does not prove its
executable exists. Preserve the exact device identity in launch parameters.
Show the current raw input beside
`/detections` and `/detections_overlay` so the demo proves input, structured
results, and rendered output independently.

After writing, re-read `package.xml`, the build file, every launch file, and the
TUI entry point. Check that installed paths match launch references and that all
topic names/types agree with `input/acceptance.yaml`.

## 4. Test, build, and deploy

Run source-level contract tests before the cross-build. The tests must catch at
least malformed URDF, missing package dependencies, launch parse failures,
unexpected motion publishers, absent required topics, and a TUI that imports or
binds motion-control messages.

Build in the ROS 2 SDK container selected by `input/build_target.yaml`; never
compile the target package on the board. Poll to a terminal exit marker and
inspect installed package indexes, executables, launch/config assets, and linked
libraries. A zero exit code alone is insufficient. Before deployment, verify
that `ros2 pkg prefix foxglove_bridge` resolves from the staged payload when the
target image does not supply it. Also enumerate each selected runtime plugin
with its package's discovery command (for example `ros2 run image_transport
list_transports`) and prove both publisher and subscriber transports resolve
from the staged environment. Pin and record public bridge/plugin dependencies
and build-only system packages so CI and a clean board follow the same path.

Stage only the declared payload. Apply the portable-pipeline storage rule before
deployment: select a writable NVMe-backed application directory from live
`lsblk`/`findmnt` evidence, and use `/data/simaai/applications/<application>`
only when the board has no writable NVMe filesystem. Persist the selected path
in `deploy.yaml` and record its backing device with the source revision and build
manifest. Update the active project's client `deploy.yaml` before invoking
deployment; a `deploy.yaml` nested only inside a custom `payload` directory does
not override the project-level destination used by Studio. Before launch,
follow the board setup and portable-pipeline preflight.
Stop only a previously recorded instance of this deployment. Launch detached
with durable logs, then start `foxglove_bridge` after the publishers are live.

## 5. Acceptance is advertised, active, visible, and operable

Do not report success until all four levels pass:

1. **Advertised:** expected nodes and topics exist with exact message types.
2. **Active:** fresh rate samples meet the contract and logs continue advancing.
3. **Visible:** Flora subscribes to the exact image/result topics and renders
   current messages, not a stale frame. For video replay, this includes the raw
   bag topic, structured detections, and overlay in separate panels.
4. **Operable:** the generated TUI renders at normal and narrow terminal sizes,
   updates node/topic/log state, exits cleanly, and exposes no motion command.

For replay input, prove it loops or state its finite duration. For managed RTSP,
prove the stream is owned by Edgematic Streams, is reachable from the board,
and continues delivering frames. For USB V4L2, prove direct ownership of the
selected device and fresh compressed camera, detection, and boxed-overlay
topics. Sample live input at startup, after 30 seconds,
and after 60 seconds to catch launch processes that die with the SSH session.
Measure replay header latency against the replay clock (for example, `ros2 topic
delay --use-sim-time`) rather than wall time, and make redirected CLI metrics
unbuffered so timeout termination does not leave empty evidence. Include the
current bridge subscription log in the evidence.

If a check fails, diagnose, edit the generated source or configuration, rebuild,
redeploy, and repeat the entire acceptance sequence. Do not paper over a runtime
failure by weakening `input/acceptance.yaml`.

## Handoff

Report the generated package path and source revision, evidence sources and
assumptions, build and deployment identities, node/topic/type/rate table, Flora
subscription proof, TUI checks, all changed files, and every remaining
production gap. Explicitly say that a replay- or managed-RTSP-driven no-motion
proof does not validate the physical robot driver, robot-mounted camera driver,
or safety system.
