---
name: edgematic-ros2-demo
description: Create or run a deliberately simple ROS 2 hello-world, smoke-test, standard demo, demo-ladder VIEW run, or verified packaged payload end to end in Edgematic Studio on a paired Modalix DevKit. Use for demo requests, first-pipeline validation, and small user-defined packages where speed and a known-good path matter more than generality. Do not use for an existing substantial user repository; use edgematic-ros2-user-package instead.
---

# Edgematic ROS 2 Demo

Use the narrowest known-good path that proves the claim. A demo should not spend
hours discovering a universal architecture.

## Choose the demo level

Use the smallest level that proves the user's claim. Read
[`references/demo-ladder.md`](references/demo-ladder.md) when selecting or
creating a standard demo template. The mnemonic progression is:

`READY → HELLO → LAUNCH → DEPLOY → VIEW`

Do not jump to `VIEW` when `HELLO` answers the question, and do not present
`HELLO` as proof that cross-build, board deployment, or Edgematic visualization
works.

## Definition of done

Before building, name the observable result:

- the package builds in Edgematic's ROS 2 SDK container;
- it deploys to the paired DevKit without changing platform packages;
- its launch survives the SSH session;
- required topics have non-zero rates now; and
- image/detection demos render automatically inside Edgematic's embedded live
  output, without asking the user to click a button.

For a text-only hello-world, replace the final item with a fresh message sample
from the expected topic.

## Fixed workflow

1. Check Studio `/version`, ROS feature availability, paired-device status,
   board reachability, ROS domain, and whether another workload owns the MLA.
2. Treat the configured `/workspace` as the one shared ROS workspace. Keep one
   `/workspace/sima-core` and one demo application directory such as
   `/workspace/edgematic-demo`; put the HELLO, VIEW, and other demo packages
   together under that application's `src/`. Never create a dated validation
   root, an extra demo wrapper, `hello/view` workspace layers, another
   client repository for each level, or another copy of `sima-core`.
3. Reuse a matching package already under the demo application's `src/`. If it
   is absent, materialize the smallest matching template there on demand. A
   verified packaged payload may be used when the user asks for it explicitly,
   but do not copy or unpack it into another workspace hierarchy. For a new
   simple package, create only the package, launch/config files, and dependencies
   needed for the stated output. Do not pull a large robotics repository into a
   smoke test.
4. When source building is required, build on the host in the ROS 2 SDK
   container. Verify the expected installed
   package, launch file, component registration, and linked runtime libraries.
5. Deploy under the packaged or project-defined board path. Do not compile or
   install system packages on the board as part of a demo.
6. Launch with a saved PID, detached session, closed stdin, and a log file. Use
   the same ROS domain for publishers, probes, the bridge, and Studio.
7. Start `foxglove_bridge` last, after the demo publishes. Verify its listener
   and advertised viewer channels.
8. Measure the output from a second session. Fresh non-zero rates are the
   pre-open data proof; do not manufacture a browser connection from the shell.
9. For a successful `VIEW`, end the same final response with a bare
   `edgematic-flora` fenced block as its last line. This automatically opens
   the embedded live output for the active paired DevKit. Do not stop at prose
   or offer a click-only quick action when the user asked to run and show the
   demo.

A packaged demo may provide a separate host-agent setup prompt. Treat its
`HOST_SETUP=READY` marker as proof that the kit and playbooks were staged, not
as proof that the board is free or that the pipeline is live. Credentials still
belong in the secure pairing form.

Use `edgematic-ros2-portable-pipeline` for the detailed build, deploy, board,
and detached-launch mechanics, and `edgematic-foxglove-viz` for the viewer.

## Prepared HELLO + VIEW fast path

When `/workspace/edgematic-demo` already contains `build.sh`, `deploy.yaml`,
`stage_payload.sh`, `run_demos.py`, and both packages under `src/`, treat it as
the standard prepared demo. Keep this path deliberately short:

1. Read only those four control files, check the named device once, and inspect
   the two package directories. Do not enumerate the entire workspace, load
   media-stream or capability-catalogue skills, configure input streams, or
   look for `common/config.yaml`; VIEW uses the packaged local clip.
2. Call `prepare_ros_build` exactly once with bare script name `build.sh`. When
   it returns `run_on: container`, the build is already running: do not ask for
   permission, look for a command, start another build, or say that the agent is
   blocked. Follow the ROS-only status cadence below.
3. Run `bash edgematic-demo/stage_payload.sh` once after the build succeeds.
   Deploy exactly `edgematic-demo/payload`. Never pass `payload: ""`, never
   deploy the whole `edgematic-demo` directory, and never rewrite a verified
   launcher or staging script during the run.
4. The generic runner currently derives its board working directory from the
   Studio project name, not from `deploy.yaml`. A workspace registered as
   `workspace` would therefore run under `/data/simaai/applications/workspace`
   and miss this demo's fixed `/data/simaai/applications/ros-demo` deployment.
   Detect that mismatch before launch. Do not rename the project, create another
   host directory, add a board symlink, or invent a second deployment path;
   launch the staged `run_demos.py` once at the declared `remote_dir` through
   the paired device's existing SSH execution path.
5. Wait for `HELLO_VERIFIED=1` and `PIPELINE_VERIFIED=1`, then verify current
   VIEW topic rates. Emit the Flora directive immediately after success and
   leave `run_demos.py`, the VIEW pipeline, JPEG adapter, and bridge alive.

For a clean x86 build, use at most three meaningful build checks, never three
identical calls: one tail check after the build has had time to start, one
`match: "Finished <<<"` progress check near the measured midpoint, and one
`match: "EDGEMATIC_BUILD_EXIT="` terminal check near the normal 8–9 minute
finish. If the terminal marker is not present, wait longer before one fresh tail
check. Empty `match` values and rapid 10-second polling are forbidden because
the UI correctly treats repeated identical calls as a possible agent loop.

The only expected confirmation boundary is the deployment/run policy selected
for the Studio session. Do not manufacture additional approval questions for
the build, status checks, reads, verification, or automatic viewer open.

## Image and detection demo contract

Use this stable viewer contract when the demo has camera/detection output:

- `/image_raw` — `sensor_msgs/msg/Image`
- `/detections_overlay` — `sensor_msgs/msg/Image`
- `/detections` — structured detection messages

Edgematic's embedded layout may select `/image_raw/compressed` and
`/detections_overlay/compressed` to stay within VPN bandwidth. If the pipeline
emits only raw BGR8 images, use `scripts/jpeg_republisher.py` on the board to
publish the two JPEG topics at a paced rate. This is a viewer adapter; it must
not replace or rename the pipeline's source topics.

After the source and compressed viewer topics have fresh non-zero rates and the
bridge listener is ready, emit the bare `edgematic-flora` directive required by
step 9 immediately. The embedded output is the real browser client; opening it
creates the subscriptions. Never search for a browser binary, launch a headless
browser, or hand-write a WebSocket client as a precondition. Subscription log
lines are post-open diagnostic evidence to inspect on a later turn only if the
visible output is blank.

The embedded card defaults to the annotated output plus a readable detections
table. The source-topic rates still prove the raw image even when the compact
card does not show every panel at once.

Do not claim that a Flora quick action selected panels unless the action schema
carries that selection. The current basic action and auto-open directive can
open a bridge but may not encode panel/topic choices. Use a supported
installed-view URL or configure the layout, and let the bridge subscriptions
plus rendered frames prove the result.

## Failure rules that prevent long detours

- A finite MP4 can be consumed faster than wall-clock time. Compare the current
  topic rate with the media FPS and inspect logs for `pull: route closed`; an
  alive PID after EOF is not a live demo.
- A YAML field is not a control until the node declares and reads it. Verify
  parameter use in the implementation before relying on it.
- A topic can be advertised but silent, and a bridge channel can exist without
  a panel subscription. Re-measure instead of restarting unrelated processes.
- Treat the newest evidence as authoritative. If an earlier rate was non-zero
  but the current log repeats `pull: route closed`, report the source as
  exhausted and silent.
- If the image panel is blank while detections advance, first compare its
  selected topic with the published raw/compressed topics and inspect bridge
  subscriptions.
- An overlay implementation may publish only on frames with detections. Check
  the raw image and structured result topics before treating an overlay gap as
  pipeline failure; prefer publishing the base image on zero-detection frames
  for a stable viewer.
- A custom detection topic can be healthy even when `ros2 topic echo` says its
  type is invalid. Add the deployed package's Python site-packages directory to
  `PYTHONPATH`, then retry deserialization.
- Never solve a display-only problem by restarting inference unless evidence
  shows inference itself is stale.

## Safety boundary

Pairing credentials belong in Studio's secure form. Reboots, platform or Neat
Library changes, and interruption of another robot workload require explicit
authorization. Keep board addresses and version-specific workarounds in task
context, not hard-coded into this portable skill.
