---
name: edgematic-ros2-legacy-vdp-port
description: >-
  Use when cross-compiling a package from the legacy vdp-simaai-ros2 client
  repository for a Modalix DevKit and porting its develop-branch sources, which
  were written against simaai-socpipeline 2.1.x, onto the board's current Neat
  runtime. Covers the sibling sima-core layout that repository needs, the
  bringup package colcon expects, and the six runtime fixes — only one of which
  is a compile error, so a green build is necessary and nowhere near
  sufficient. Trigger on a vdp-simaai-ros2 package that builds cleanly and then
  dies on the board with a bad_alloc, a segfault on the first frame, an
  unsupported-operation dispatcher error, or an encoder rejecting its input
  buffer. Do NOT use for a pipeline the user owns (see
  edgematic-ros2-portable-pipeline), for choosing capabilities in a workspace
  (see edgematic-ros-capabilities), or for compiling anything on the board — that
  never happens.
---

# Porting a legacy vdp-simaai-ros2 pipeline to the current Neat runtime

**Golden rule: every compile happens on the host, inside the ROS 2 SDK
container.** The board receives artifacts and runs them. Never build, install
packages, or write to system library directories on the board — on a live robot
that stack belongs to someone else.

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

## 2. Ground every fix in the board's own headers

The develop branch was written against the 2.1.x socpipeline API; the board runs
a much newer Neat. **The old libraries are usually still installed**, so the
mismatch compiles clean and explodes at runtime. Read the fixes off the cross
sysroot's real headers on this host — not off prose, and not off the
2.1.x sources — or the fix is a guess wearing a diff.

## 3. The six fixes, in the order they bite

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
6. **Re-attach the video metadata before the encoder.** The encoder rejects a
   forwarded DMA buffer whose padded NV12 layout it cannot infer ("attach
   GstVideoMeta for a custom padded layout"). The decoder's output is
   height-padded and that metadata is lost across the ROS boundary, so rebuild it
   from the real buffer size before pushing, and add the GStreamer video library
   to the build dependencies.

## 4. Build, then prove it on the board

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
