---
name: edgematic-ros2-demo
description: Create or run a deliberately simple ROS 2 hello-world, smoke-test, or SiMa reference demo end to end in Edgematic Studio on a paired Modalix DevKit. Use for demo requests, first-pipeline validation, and small user-defined packages where speed and a known-good path matter more than generality. Do not use for an existing substantial user repository; use edgematic-ros2-user-package instead.
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
- image/detection demos render inside Edgematic's embedded Flora view.

For a text-only hello-world, replace the final item with a fresh message sample
from the expected topic.

## Fixed workflow

1. Check Studio `/version`, ROS feature availability, paired-device status,
   board reachability, ROS domain, and whether another workload owns the MLA.
2. Reuse an existing checked-in demo or template when it matches. For a new
   simple package, create only the package, launch/config files, and dependencies
   needed for the stated output. Do not pull a large robotics repository into a
   smoke test.
3. Build on the host in the ROS 2 SDK container. Verify the expected installed
   package, launch file, component registration, and linked runtime libraries.
4. Deploy under the paired SSH user's home. Do not compile or install system
   packages on the board as part of a demo.
5. Launch with a saved PID, detached session, closed stdin, and a log file. Use
   the same ROS domain for publishers, probes, the bridge, and Studio.
6. Start `foxglove_bridge` last, after the demo publishes. Verify the bridge
   listener and current topic subscriptions.
7. Measure the output from a second session. Distinguish advertised, active,
   and visible; all required levels must pass.

Use `edgematic-ros2-portable-pipeline` for the detailed build, deploy, board,
and detached-launch mechanics, and `edgematic-foxglove-viz` for the viewer.

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

Open the installed Edgematic-hosted view with the paired board's bridge URL and
the `raw,overlay,detections` panels. Confirm the served page actually renders
all three, then verify matching `created ROS subscription` lines in the bridge
log.

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
