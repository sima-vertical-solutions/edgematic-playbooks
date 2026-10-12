---
name: edgematic-ros2-user-package
description: Build, extend, deploy, run, and verify an existing or current-project ROS 2 package through Edgematic Studio on a paired Modalix DevKit. Use for a short outcome prompt that points to a repository, active project, package, launch file, or custom topic contract, including an attended robot follow application. Use edgematic-ros2-demo for standard demos.
---

# Edgematic ROS 2 User Package

Preserve the package's explicit model and runtime contract. When a component is
missing or replacement is needed, follow
[SiMa-first component selection](../edgematic-ros-capabilities/references/sima-first-selection.md)
before introducing an external model or duplicate runtime; a deployment request
alone is not permission to replace a working user-selected model.

Preserve the user's package and make its actual build/run path work. Do not
replace it with a reference demo or generalize from a different repository.

Load `edgematic-ros2-portable-pipeline` for the detailed workspace, build,
deploy, board, and detached-launch mechanics. This skill owns routing, the
package contract, and the evidence required before reporting success.

## Robot source boundary

For robot work, use the GitHub repository supplied in the prompt and record its
immutable revision. Derive model, geometry, sensors, driver packages, topics,
message types, launcher paths, calibration and limits from that source and
read-only inspection of the selected device. Do not import a remembered robot
profile or customer application as a default. Keep task-specific findings in the
project contracts and evidence, outside these shared skills. Resolve missing
source or required facts before the dependent action.


## Keep one workspace

Use the workspace the user configured; do not create another workspace beneath
it. Keep the shared capability repository once at `<workspace>/sima-core` and
place each application repository or package beside it as
`<workspace>/<application>`. Do not introduce dated validation directories,
`hello/view` grouping layers, or per-application copies of `sima-core`.

Preserve an existing user repository's internal structure. The direct-child rule
controls where that repository is placed, not how its source tree is rewritten.
Only use a different root when the user explicitly points to an existing
workspace elsewhere.

## Establish the real package contract

1. Identify the source repository, ROS workspace root, package name, package
   type, launch entry point, parameters, expected outputs, and paired device.
2. Read `package.xml`, `CMakeLists.txt` or `setup.py`, and the launch file before
   editing. Resolve symlinks and globbed source paths so changes land in the
   tree the build really compiles.
3. Reuse the package's own model, media, configuration, and topic contract. Ask
   only for an irreducible input such as missing device pairing, credentials
   entered in Studio's secure form, or an unavailable proprietary artifact.
4. Treat the board as shared unless the user says otherwise. Read-only
   inspection is safe; rebooting, installing board packages, replacing platform
   libraries, or stopping an unrelated robot stack needs explicit authorization.

## Extend an existing application from a short outcome prompt

If the user asks the current project to add live perception, odometry, or robot
following, inspect its source and active run first, then write the missing
application code, contracts, launch wiring, and tests in that project. The
current project's package is the source to extend, not a reason to route to a
new package generator or start a second workspace. Keep working components and
their model provenance; derive the delta from the prompt, supplied robot source,
URDF, and observed device interfaces. Resolve required build and runtime
dependencies in the SDK rather than asking the user for routine shell steps.
For a runnable script created with `write_file`, set `executable: true`, verify
the mode in the host and build container, and preserve it on later edits.

For requested physical motion, read
[attended robot motion](../edgematic-ros2-contract-builder/references/attended-motion.md)
before implementing or launching the base path. The user's requested behavior
defines scope; the exact command interface, guard thresholds, operator bindings,
and feedback topics come from the selected application and live robot evidence.
Leave the robot disarmed for unattended verification and hand the controls to
the operator for the physical acceptance step.

## Build and deploy

- Build on the host in Edgematic's ROS 2 SDK container. The board is a runtime
  target, not a compiler.
- For a running ROS build, poll `get_build_status` every 120 seconds. Report
  elapsed time, completed/total packages, active package or phase, log activity,
  failures, and ETA from `ros_progress`; label an ETA provisional when the
  package total or first completion is not yet available.
- Use Studio's ROS workspace/build/deploy tools when they support the package.
  Otherwise use the repository's checked-in scripts rather than inventing a
  parallel build wrapper.
- Confirm artifacts, registered components, linked SONAMEs, and package indexes;
  a zero build exit alone is insufficient when optional dependencies can
  silently skip targets.
- Deploy to a path owned by the paired SSH user. Preserve unrelated board files
  and record the exact deployed prefix.
- Source the board ROS underlay and deployed prefix deterministically. Do not
  assume a generated merge-install `setup.*` restores the workspace's own
  prefix; verify `AMENT_PREFIX_PATH` and `LD_LIBRARY_PATH` when package discovery
  fails.

## Run without losing the process

- Preflight the exact runtime resources the package uses: ROS domain,
  accelerator ownership, model/media paths, disk space, and port availability.
- Stop only a previously recorded instance of this deployment. Prefer saved
  PIDs or exact executable identities; never broad-match a full SSH command line.
- Launch detached with stdin closed and stdout/stderr redirected to a durable
  log. Verify the process from a second SSH session so a surviving local shell
  is not mistaken for a surviving workload.
- Start or restart `foxglove_bridge` only after deploy and after publishers are
  live. An in-place deploy can invalidate a running bridge binary.

## Prove the outcome at three levels

1. **Advertised:** expected nodes and topics exist with the expected types.
2. **Active:** current logs advance and a fresh `ros2 topic hz` sample is non-zero.
3. **Visible:** the bridge log shows a subscription for the exact panel topic
   and Edgematic/Flora renders current frames or messages.

Do not report success from PIDs, topic names, channel advertisements, or an old
rate sample. For file input, also prove that the source loops or state the finite
end time; an alive node after `pull: route closed` is not an active pipeline.

The latest evidence supersedes earlier success. If a prior rate was non-zero but
the current log shows a closed source route with no later decode/result lines,
report the package as inactive until a fresh rate proves otherwise.

For a robot follow request, also verify one camera, controller, base-command
owner, and bridge; current feedback and zero requested/measured motion while
disarmed; and the guarded stop paths in isolated tests. A healthy camera or
advertised odometry topic does not prove physical following. Record observed
motion only after an attended operator test with fresh feedback.

## Visualization

- Prefer the package's renderable standard message topics. Structured detections
  and image output are separate evidence; preserve both.
- Match the served Edgematic layout, not a source file that is not in the
  installed bundle. If it selects `/compressed`, require those topics or
  deliberately select a raw topic.
- Raw 1280x720 BGR8 video is about 2.8 MB per frame. Across a VPN, publish a
  paced, compressed or downsampled viewer topic rather than opening multiple
  full-rate raw subscriptions.
- A channel advertised by the bridge is not proof of a browser subscription.
  Verify `created ROS subscription on <topic>` in the current bridge log.
- Do not claim a quick action or auto-open directive selected panels unless its
  actual schema carries panel/topic fields. Verify the installed view's selected
  topics.
- If a custom message is listed but `ros2 topic echo` cannot load its type, add
  the deployed Python package directory to `PYTHONPATH` before diagnosing the
  publisher.
- If overlay publication is detection-conditional, judge gaps alongside raw
  images and structured detections, and record that contract in the handoff.

## Hand off

Report the source revision, build/deploy prefix, launch identity, current rates,
visible topics, bridge subscription evidence, files changed, and any remaining
product gap. Keep credentials and raw logs out of durable summaries.
