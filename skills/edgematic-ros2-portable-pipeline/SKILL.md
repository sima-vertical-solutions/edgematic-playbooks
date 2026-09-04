---
name: edgematic-ros2-portable-pipeline
description: >-
  Use when building, deploying and RUNNING a ROS 2 Neat pipeline on a paired
  Modalix DevKit from a workspace of the user's own — a package they wrote, or
  one they are porting — rather than from a SiMa client repository. Covers the
  minimal colcon layout whose only fixed sibling is sima-core, cross-compiling
  in the ROS 2 SDK container, the sima-owned deploy target, the board
  environment that merge-install breaks, and the detached launch that keeps a
  run alive after the SSH command returns. Trigger on "run my own ROS 2
  pipeline", "build a standalone pipeline for the DevKit", or a pipeline that
  starts, shows real frames for about twenty seconds and then goes dark. Do NOT
  use for creating or provisioning the ROS 2 container (see
  edgematic-ros2-host-container), choosing capabilities in a client workspace
  (see edgematic-ros-capabilities), the pre-built yolov8_seg pipeline (see
  edgematic-ros2-neat-nodes), or Foxglove/Flora rendering itself (see
  edgematic-foxglove-viz).
---

# Running a ROS 2 pipeline the user owns

This skill is for a pipeline that belongs to the user. The only thing it has to
build against is **sima-core** — the capabilities sibling — plus their own
bringup package. Everything else here is board mechanics, true of any ROS 2 Neat
pipeline whatever repository it came from.

Prefer it whenever the user has their own workspace. It is the only path
available at all on a deployment whose Robotics settings have disowned the
legacy client repository — and this skill deliberately does not name that
repository anywhere, because naming it is exactly what makes a skill invisible
to the deployments that need this one most.

## 1. The layout the tooling requires

```
<workspace>/
  sima-core/                 # capabilities sibling — this is what makes the parent a ROS workspace
  <app>/
    src/<pkg>/               # the bringup package: package.xml + CMakeLists.txt
      launch/<pkg>.launch.py
      params/<pkg>.yaml      # input RTSP + output UDP endpoints
      configs/*.json         # Neat stage configs (node_name + caps)
    build.sh                 # the colcon driver
    deploy.yaml              # remote_dir (sima-owned) + ros_domain_id
```

`open_ros_workspace` recognises the workspace once `<app>/src/<pkg>/package.xml`
exists **and sima-core sits beside it**. Upstream repositories often keep their
packages under `packages/` and build from the root; when that is the shape, author
a thin `src/<pkg>` that compiles the node sources where they already are and
installs the package's resources **in place**. Never copy a binary model file
with `write_file` — it is decoded as UTF-8 and the write fails — and never shell-copy
it into the project; install it from its original path in CMake.

Capability selection is only needed if the package `exec_depend`s a sima-core
capability. A self-contained pipeline selects none, and `open_ros_workspace`
listing them all as unselected is the expected result, not a problem to fix.

## 2. Cross-compile — on the host, in the container, never on the board

`prepare_ros_build` with the build script named explicitly; the result's `run_on`
says whether Studio started it (`container`) or handed the user a command. Watch
the log to completion rather than assuming.

**Both of those are the cross-compiler.** `run_on: "container"` means Studio
started the build in the ROS 2 SDK container over its build channel;
`run_on: "host"` means no channel was reachable, so the result carries a
`command` for the user to run — and that command is still an exec INTO the same
container. There is no third outcome in which a build happens somewhere else,
and you must not invent one.

### When there is no cross-compiler: ask, never fall back

If the container is missing the handed-back command fails on the host — no such
container, or no container runtime at all — and `prepare_ros_build` cannot be
used until that is fixed. The DevKit can compile natively, so the tempting move
is to build there instead. **Do not do it silently.** Building on the board
compiles against whatever that board happens to have rather than the pinned
sysroot, and it writes into a live robot's stack: a root-owned build leaves
artifacts the pipeline user cannot use, a rebuild swaps shared objects under a
pipeline that is still running, and a later Neat reinstall invalidates the build
directory without saying so. Those failures surface far from the build, as a
pipeline that runs and produces nothing.

So stop and put it to the user with `ask_user`. Keep the question itself short —
they may not know what a cross-compiler is, and a wall of text is not a choice:

> I can't reach the ROS 2 cross-compiler container, so I can't build this the
> normal way. I can either help you install that container, or build directly on
> the DevKit — which is faster to start but changes the board. Which would you
> prefer?

Offer it as three `prompt` pills: **Install the container**, **Build on the
DevKit**, and **Tell me more**. On *Tell me more*, give the detail above —
compiling against the board's own libraries instead of the pinned sysroot, the
root-owned artifacts, the swap under a running pipeline, the invalidated build
directory after a Neat reinstall — and say plainly that installing the container
is the fix and a device build is a one-off.

Then honour the answer:

- **Install the container** — hand over to `edgematic-ros2-host-container`,
  which is the skill for exactly this, and come back here afterwards.
- **Build on the DevKit** — proceed, but say once what they have accepted, and
  walk them through it over the built-in SSH terminal rather than pretending a
  Studio tool does it: there is no agent tool that builds an arbitrary workspace
  on the board. Build as the same user that will run the pipeline (never as
  root), stop a running pipeline first, and remove the package's build directory
  before rebuilding if Neat was reinstalled since the last build.
- **No answer / unsure** — do not guess. A build that starts on the wrong machine
  is far more expensive to undo than a second question.

Two failures that look like broken code and are not:

- **The build script must be executable.** `write_file` cannot set the exec bit —
  a permission is not file content — so the user sets `+x` from their own shell.
  Without it the build dies instantly on a bad interpreter / permission denied.
- **Name the script by its bare filename**, not a workspace-relative path. The
  container's working directory is already the project directory, so a path
  produces exit 127 and "No such file or directory".

A green build proves cross-compilation. It does not prove the pipeline runs:
anything that depends on the board's Neat ABI compiles clean against the headers
and fails at runtime. Verify on the board, and say which of the two you have.

## 3. Deploy

`deploy_to_device` places the merge-install tree at the `remote_dir` from
`deploy.yaml`.

- **`remote_dir` must be owned by the SSH user** (`sima`). A root-owned target
  fails while `tar` restores the directory's timestamps ("utime: Operation not
  permitted"), after appearing to copy fine.
- **`ros_domain_id` must match the board.** A wrong id fails *silently* on
  hardware — everything launches and nothing ever discovers anything. Ask; do not
  guess.
- Deploy overwrites files in place, so a deployed `foxglove_bridge` is killed by
  its own overwrite. Start the bridge **after** deploying, never before.

## 4. Board pre-flight, before every run

Have the user run these over the built-in SSH terminal; both are cheap and both
have cost hours when skipped.

- **The MLA shared-memory signature must be the live one.** Read the first four
  bytes of the MLA shared-memory node with `od` (`xxd` is frequently absent from
  the board image). A stale value left by a previous stack means the board needs
  a reboot before anything will run.
- **The MLA must be free** — no pipeline container from an earlier session still
  holding it. When matching a process name, bracket the first character of the
  pattern so the search cannot match the very command that runs it and kill the
  user's own session.

## 5. The two things that decide whether the run survives

1. **Set the environment explicitly, do not source the deployed setup script.**
   The merge-install setup script re-sources the container's build-time parent
   prefixes and drops this workspace's own, so `ros2` cannot find the package;
   on some board images the local variant emits no prepend either. Source the
   base ROS 2 overlay for the CLI, then prepend the deployed prefix to
   `AMENT_PREFIX_PATH` and its `lib` to `LD_LIBRARY_PATH` directly.
2. **Launch detached.** A backgrounded launch over a non-interactive SSH command
   dies of `SIGHUP` the moment that command returns. The tell is unmistakable and
   routinely misread: real annotated frames for roughly twenty seconds, then the
   tile goes dark. Launch it under `setsid` with stdout and stderr redirected to
   a log file, so it outlives the session that started it.

## 6. Verify, do not assume

- On the board: the encoder's frame-rate line, zero discarded frames, and the
  process still alive **from a second SSH session** — that last one is what
  proves the detachment worked.
- In Studio: `count_streams` for the output channel the pipeline encodes into,
  and `list_output_streams` for the browser leg when a tile is blank despite a
  healthy run.
- Poll for up to about two minutes after a run starts. A channel exists only
  after its first annotated frame, so never show the user a zero-count grid and
  call it a result.

## 7. Making the output visible

- **Video, the short path:** point the encoder's UDP sink at a Studio output
  channel and the annotated stream appears in the streams grid with no Foxglove
  involved. Take the server address from `list_output_streams` — never
  `localhost`, which the board cannot reach.
- **Foxglove / Flora:** only renderable topics appear. A pipeline emitting custom
  SiMa message types gives Foxglove nothing to draw, so publish a
  `sensor_msgs/Image` overlay from the node holding the finished frame and point
  an Image panel at that. Start `foxglove_bridge` last — after the deploy and
  after the pipeline.
