---
name: edgematic-ros2-legacy-vdp-port
description: >-
  Use when cross-compiling a package from the legacy vdp-simaai-ros2 client
  repository for a Modalix DevKit and porting its develop-branch sources, which
  were written against simaai-socpipeline 2.1.x, onto the board's current Neat
  runtime. Covers finding the tree the build actually compiles before editing
  anything, the sibling sima-core layout that repository needs, the bringup
  package colcon expects, and the six runtime fixes — only one of which is a
  compile error, so a green build is necessary and nowhere near sufficient. Trigger on a vdp-simaai-ros2 package that builds cleanly and then
  dies on the board with a bad_alloc, a segfault on the first frame, an
  unsupported-operation dispatcher error, or an encoder failing to prepare its
  input buffer. Do NOT use for a pipeline the user owns (see
  edgematic-ros2-portable-pipeline), for choosing capabilities in a workspace
  (see edgematic-ros-capabilities), or for compiling anything on the board — that
  never happens.
---

# Porting a legacy vdp-simaai-ros2 pipeline to the current Neat runtime

**Golden rule: every compile happens on the host, inside the ROS 2 SDK
container.** The board receives artifacts and runs them. Never build, install
packages, or write to system library directories on the board — on a live robot
that stack belongs to someone else.

That rule holds even when the container is missing. A build on the board is not
a fallback you may take on the user's behalf: ask them first, and say what it
costs — `edgematic-ros2-portable-pipeline` carries the wording and the three
answers to honour. Here the stakes are higher than there, because this port
exists to link against the pinned sysroot's own headers and libraries; a native
build on the board links against whatever that board happens to have, which is
the exact mismatch the six fixes below are about.

This skill is only usable on a deployment that still works from the
`vdp-simaai-ros2` client repository. Where the Robotics setting **Legacy
vdp-simaai-ros2 repository** is off, the repository is out of scope and
`edgematic-ros2-portable-pipeline` is the path.

## 1. The layout, and the one file you have to write

The repository keeps its packages under `packages/` and builds from the root,
but `open_ros_workspace` needs a bringup package at `src/<pkg>/package.xml`,
with sima-core as a sibling of the repository. So author a thin `src/<pkg>` that
compiles the node sources where they already live and installs the upstream
package's resources — configs, launch files, and the binary model file — **in
place**. Never copy a binary model with `write_file` (it is decoded as UTF-8 and
the write fails) and never shell-copy it into the project.

Scope the colcon invocation to the bringup and message packages so the upstream
`packages/<pkg>` is not built a second time under a different name.

`deploy.yaml` carries two values only the user can supply: a `remote_dir` the
SSH user owns (a root-owned target fails while `tar` restores timestamps) and
the board's real `ros_domain_id` (a wrong id fails silently on hardware).

## 2. Find the tree the build actually compiles, before editing any of it

The single most expensive mistake available here. The upstream repository keeps
node sources in more than one place, and the bringup package decides which ones
are compiled — often real files under the client repository's own `nodes/`
directory rather than anything under `sima-core`. Applying all of the fixes
below to the wrong tree produces a clean build, an unchanged binary, and the
same runtime failure, with nothing to tell you why.

Read the bringup package's `CMakeLists.txt` and resolve the source paths it
globs, following symlinks to see where they land, before you touch a line. A
whole port has been redone for want of that one check.

## 3. Ground every fix in the board's own headers

The develop branch was written against the 2.1.x socpipeline API; the board runs
a much newer Neat. **The old libraries are usually still installed**, so the
mismatch compiles clean and explodes at runtime. Read the fixes off the cross
sysroot's real headers on this host — not off prose, and not off the
2.1.x sources — or the fix is a guess wearing a diff.

## 4. The six fixes, in the order they bite

1. **The config manager is a shared pointer** in the current job header. Declare
   it as one, construct it as one, and assign it to the job directly. This is
   the *only* one of the six that is a compile error.
2. **Relink against the current runtime.** Find the current config-manager,
   dispatcher-core and allocator libraries by absolute path from the sysroot and
   drop the legacy ones. Linking the old shared objects against current headers
   surfaces as a `std::bad_alloc` inside the pipeline constructor — an
   allocation failure that is really an ABI mismatch.
3. **Use the public accessors for GStreamer memory.** Delete any hand-copied
   copy of the private segment struct. Fetch the segment through the accessor,
   forward the same memory taking one reference so a fresh pool buffer is used,
   and attach the memory handles as qdata on it. Switch the decoder and encoder
   elements to their current names. A raw cast of the private struct segfaults on
   frame one.
4. **Submit prepared work; do not call the generic run entry point.** It returns
   "operation not supported" for the CVU and MLA paths. Wrap the prepared-submit
   call so it waits on the job's completion callback, and move both call sites
   onto it.
5. **Leave the extended detections publisher off.** That code path reads a
   different tensor layout than segmentation produces, and over-reads by roughly
   half a megabyte a few hundred frames in — which presents as random corruption
   far from its cause.
6. **`Failed to prepare input buffer` is almost never the encoder's code.**
   It reads like one, and it has cost a full session to chase as one. The two
   causes that are real, in the order to check them:

   - **The source geometry does not match what the pipeline was built for.**
     This pipeline is built for **1280x720** — the render stage parses that, the
     preprocessor's input size is `1280*720*1.5`, and the encoder is configured
     for it. Feed it anything else and the encoder's async prepare fails on frame
     one, appsrc reports an internal data stream error, and the container dies
     with a SIGSEGV. `ffprobe` the clip you are actually streaming **first**.
   - **The encoder element's property string was re-derived from prose and came
     out short.** `neatencoder` needs its full set — type, profile, level, pixel
     format, width, height, frame rate, bitrate, async input mode, rate control —
     not just a bitrate. Read the exact string out of a deploy that is known to
     work (`strings` over its encoder library) instead of reconstructing it.

   How this was settled, and why it belongs in a skill: a known-good reference
   deploy failed **identically** on the same undersized clip. That is proof the
   symptom is not in the source you are editing. Attaching `GstVideoMeta` before
   pushing is something the original encoder legitimately does — keep it if you
   are reconstructing that node — but it is not this message's fix.

## 5. Build, then prove it on the board

Cross-compile with `prepare_ros_build`, naming the build script by its bare
filename; the container's working directory is already the project directory, so
a workspace-relative path fails with "No such file or directory". The script
must be executable — `write_file` cannot set the exec bit, so the user sets it
from their own shell.

Fixes 2 through 6 all compile clean. **A green build means the cross-compilation
worked and nothing more.** Deploy and run per
`edgematic-ros2-portable-pipeline` — its board pre-flight, environment and
detached launch are the same for any pipeline — then report exactly what the
first frames did, rather than reporting the build.
