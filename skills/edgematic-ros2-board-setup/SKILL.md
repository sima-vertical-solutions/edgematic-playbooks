---
name: edgematic-ros2-board-setup
description: Use BEFORE running a ROS2 pipeline on a Modalix DevKit — preparing the board so the run can succeed, and checking it is still prepared. Covers the pre-flight order (pairing, a clean board, Neat version match, workspace state, input stream, foxglove_bridge), the rule that the pipeline's RTSP input must come from Edgematic's own Streams rather than an ad-hoc external server, and the failures that let a pipeline report "started" while producing nothing. Trigger on "set up the board", "prepare the DevKit", "why is the pipeline not producing output", "no detections", "the run started but nothing happens", or any ROS2 run against a board whose state is unknown. Do NOT use for running/introspecting a prepared pipeline (see edgematic-ros2-neat-nodes), pairing or deploying (see edgematic-device-ops), Flora rendering (see edgematic-foxglove-viz), or first-time SoC flashing (see edgematic-ros2-integration).
---

# Preparing a DevKit before a ROS2 pipeline run

A ROS2 pipeline launched against an unprepared board does not fail. It reports
`status:"started"`, the launcher spawns, and then nothing is published. Every
condition below produces that same symptom, which is why the board is checked
*before* the run rather than diagnosed after it.

**The rule this skill exists to enforce:** the pipeline's video input comes from
**Edgematic's own Streams**, never from an RTSP server someone started by hand.

## Pre-flight order

Each step gates the next. Stop at the first failure and report it — do not run
the pipeline "to see what happens", because a start always succeeds.

### 1. The device is paired and reachable

`list_devices` / device status (see `edgematic-device-ops`). An unreachable board
fails the SSH build/run with a transport error rather than a pipeline error, so
this is the cheapest check and it disambiguates everything after it.

### 2. The board is clean

A previous run that was killed rather than stopped leaves the board in a state
that *looks* healthy:

- A stale pipeline process still holding `/dev/rpmsg*`, `/dev/simaai-mem` or the
  MLA shared-memory segment. The next run then blocks on a resource it cannot
  take, with no error.
- Root-owned FastDDS/shared-memory files under the DDS temp directory. A pipeline
  started by a different user cannot open them and silently publishes nothing —
  `ros2_topic_list` shows the topics but no data flows.
- A container squatting the board at high CPU, starving the pipeline.

Stop any running pipeline through the supported path first (`run_ros_pipeline` is
safe to re-run — it stops what is running for that package and reports
`replaced_running`). If the board was killed hard, the shared-memory files must be
cleared before the next start.

### 3. Neat matches the workspace

The C++ pipelines link against Neat core; PyNeat is not required for them. A
mismatch surfaces at node load as `dlopen error: libsima_neat.so.3: cannot open
shared object file` — not at build, and not as a pipeline error.

**Any Neat reinstall invalidates the build tree.** `build.sh` is a no-op when
CMake sees nothing stale, so a reinstalled Neat leaves a stale `.so` linked in.
Remove the package's build directory and rebuild; do not assume a rebuild
happened because the build step ran.

Use `get_compatibility_doc` for the device/bundle matrix rather than hard-coding a
version here — the expected version moves with the release.

### 3b. Check compatibility, and offer to fix it rather than narrating it

Two reads, both cheap:

- `get_compatibility_doc` — the deployment's Neat/SDK compatibility matrix,
  fetched live. Use it rather than hard-coding a version here; the expected
  version moves with the release.
- `GET /devices/{id}/neat` — what the board actually has, and a verdict against
  the bundle.

When the board is behind or missing Neat, **offer the install as a confirmable
action** instead of printing instructions. `/devices/{id}/neat`,
`/devices/{id}/neat/install` and `/devices/{id}/neat/update` are all
quick-action-allowlisted, so a pill here fires — state what will be installed and
on which device, and let the user press it. Installing is poll-based; report the
outcome rather than assuming it finished.

Do not offer a pill for `/agent/features` — that endpoint is deliberately
excluded, so the button cannot fire. Point at Settings → Robotics instead.

**A Neat install invalidates the build tree** (see above), so anything installed
this way needs a rebuild before the pipeline is run.

### 4. The workspace is present and builds

The colcon workspace must exist on the board and build the target package. Two
build-time traps, both of which look like unrelated compiler noise:

- **`simaai-socpipeline-dev` cannot install alongside the Neat SDK.** Both ship
  identically-named headers into `/usr/include`, and neither declares a conflict,
  so `apt` reports nothing and the failure appears at unpack. Any board carrying
  Neat — which is most of them — hits this. The workaround is to extract the
  package elsewhere and put it first on the include path, leaving Neat untouched.
- **`orocos_kdl` missing from the board image.** The vendor package is installed
  but the library it wraps is not, so anything using `tf2_geometry_msgs` fails at
  configure, deep into a long build.

**The workspace path is deployment-specific and the defaults are often wrong.**
`EDGEMATIC_ROS_RUN_CMD` and `EDGEMATIC_ROS_STATUS_TMPL` carry a hard-coded path,
and on a board where the workspace lives somewhere else every ROS2 tool fails
with the family switched on and correctly advertised — which reads as a gate
problem and is not one. Confirm the workspace path on the device before blaming
anything upstream of it, and point the env vars at it.

### 5. The input stream comes from Edgematic Streams

This is a requirement, not a preference. Start the stream through Studio
(`start_stream`, or the Streams page) and pass the returned `rtsp://…` address to
`run_ros_pipeline` as `rtsp_url`.

**Never leave the pipeline on its baked-in default.** The params file on the board
carries whatever address was last written into it — typically a hand-started
server on someone's desk that is no longer reachable. `run_ros_pipeline` accepts
`device` alone and will happily run against that stale address, which is the most
common cause of a started-but-silent pipeline.

**Geometry must be measured, never guessed.** When `rtsp_url` is passed,
`source_width`, `source_height` and `fps` are required, and they describe the
*incoming feed*. A value that does not match the real stream corrupts the
pipeline's memory instead of failing cleanly, so a wrong number is worse than a
missing one. Do not copy the pipeline's existing defaults and do not infer them
from the video's nominal resolution — read them from the stream that was actually
started.

> Known gap: Studio does not yet record geometry on the stream it starts, so this
> value cannot be resolved automatically today. Until it does, treat an unverified
> geometry as a blocker rather than launching with a guess.

### 6. foxglove_bridge, only if visualizing

Needed only to render output (see `edgematic-foxglove-viz`). Not a precondition
for the pipeline itself — do not block a run on it, and do not start it
speculatively.

## After the run starts

`status:"started"` means the launcher was spawned. Confirm the pipeline is alive
before telling the user it is working:

- topics appear **and carry data** — the overlay topic existing is not evidence
- the expected nodes are loaded into the container

If the log stops at `Loading MLA model …` and never advances, the run is wedged
loading the model on the coprocessor. That call has no timeout, so it presents
exactly like a healthy pipeline waiting for frames. It is a platform-side defect,
not something to retry — say so rather than restarting repeatedly.

## What not to do

- Do not start an RTSP server by hand to "get something flowing" — it reintroduces
  the stale-address failure this skill exists to prevent.
- Do not treat a successful build as a working pipeline, or `started` as running.
- Do not guess stream geometry.
- Do not assume the board is in the state the last session left it in; a DevKit is
  shared and is frequently reflashed.

## Where the pieces live

| Concern | Skill |
| --- | --- |
| Pairing, status, deployment | `edgematic-device-ops` |
| Starting and listing streams | `edgematic-media-streams` |
| Running and introspecting the pipeline | `edgematic-ros2-neat-nodes` |
| Rendering output in Flora | `edgematic-foxglove-viz` |
| First-time SoC flash and full integration | `edgematic-ros2-integration` |
