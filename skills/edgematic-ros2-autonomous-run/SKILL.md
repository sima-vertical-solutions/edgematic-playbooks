---
name: edgematic-ros2-autonomous-run
description: >-
  Use when asked to get a ROS 2 pipeline running on a paired DevKit end to end
  with minimal back-and-forth — "run the pipeline on the device", "build and run
  it end to end", "get the demo up", "run a pipeline over this dataset". The
  orchestrator: works out which of the two ROS 2 paths this deployment is on,
  obtains the sources, READS THE APPLICATION CODE to derive what input the
  pipeline needs and which topics it publishes, provisions that input itself —
  a clip, a URL, a research dataset, a live stream — then builds, deploys,
  launches, verifies against the topics it derived, and shows the output. Names
  the only three things worth asking the user and answers everything else from
  the code. Do NOT use it as a reference for the individual steps: the layout,
  the board traps and the detached launch live in
  edgematic-ros2-portable-pipeline, the catalogue tools in
  edgematic-ros2-neat-nodes, rendering in edgematic-foxglove-viz, pairing in
  edgematic-device-ops. This skill decides the ORDER and what never to ask.
---

# Running a ROS 2 pipeline end to end, without a wall of instructions

The user asked for a working pipeline, not a conversation. Everything below
exists to keep you from stopping to ask for something the code already answers,
and from reporting success you have not verified.

**Finish the job.** If you cannot, say exactly what is blocked, what you tried
and what you need — never hand back a half-run pipeline as if it were done.

## What you may ask for, and nothing else

Three things genuinely need the user. Resolve everything else yourself.

1. **A paired device.** Only they have the board's credentials. If none is
   paired, ask for that first (see `edgematic-device-ops`).
2. **The board SSH credential — once.** Use it to install a key, then never ask
   again. Check whether key access already works before asking at all.
3. **Standing approval for the one destructive act.** On a shared board a reboot
   is the only irreversible step. Get the policy once, phrased as a rule rather
   than a request: *may I reboot when, and only when, the log reports the segment
   pool exhausted AND the robot stack is not running?* With that granted, do it
   and report afterwards.

Two conditional questions, and only these: **if the ROS 2 cross-compiler
container is missing**, whether to build on the device instead (the user's call,
never yours — `edgematic-ros2-portable-pipeline` carries the wording); and **if
an input source is behind a login**, for the archive itself, because you cannot
accept a licence on someone's behalf.

Everything else — which video, which stream, which slot, which topics to watch,
the build, the deploy target, the launch, the viewer — you determine. A question
about any of those is a failure of this skill, not diligence.

## Step 0 — establish which path this deployment is on, and say so

Read `GET /agent/features` and look at the tools you actually have:

- **`list_ros_examples` available** → the client-repository path. A published
  catalogue of ready-made pipelines exists; take the package name from it rather
  than guessing, and `run_ros_pipeline` builds and runs it on the board.
- **Absent** → this deployment has disowned that repository, deliberately. There
  is no catalogue to enumerate and you must not invent one or reach for the
  repository by name. Everything is obtained, cross-compiled on the host and
  deployed — the portable path, which works for any sources the user supplies.

State which path you are on in your first reply. The user cannot see that gate,
and a plan built on the wrong one wastes the whole run.

## Step 1 — obtain the sources

- **Catalogue path:** take the package name from the catalogue listing.
- **Portable path:** the user names a repository or points at a workspace. Clone
  it with `clone_repository` — never an improvised shell clone, which puts the
  credential in the repository config and drops the filters large binary assets
  depend on. Lay it out and author the bringup package per
  `edgematic-ros2-portable-pipeline`, and **read the bringup `CMakeLists.txt` to
  find which sources are actually compiled** before editing any of them.

## Step 2 — read the application's own contract (do not ask, and do not assume)

Everything you need about input and output is already written down in the package
you just obtained. Read it before touching a stream. Four answers, each with a
place it actually lives:

1. **Input geometry and frame rate.** Fixed at build time, and stated in several
   places that must agree: the params file's source width / height / fps, the
   render stage's configured dimensions, and the preprocessor's input buffer size
   (a raw NV12 size is `width * height * 1.5`, which is worth computing back to
   dimensions as a cross-check). Take the geometry from the package, never from
   the source you happen to have.
2. **Where the input comes from and where the output goes.** The params file
   names an input URL and an output sink. Note the parameter names — you will
   rewrite these, and rewriting the wrong copy is a common way to run a pipeline
   that ignores your changes. Rewrite both the source copy and the installed one.
3. **Which topics it publishes, and their types.** Grep the node sources for
   publisher creation and the launch file for remappings; that gives the real
   names before anything runs. Note the message types too — a topic carrying a
   custom message will not render in a stock image viewer however healthy it is,
   and knowing that up front saves a "the viewer is broken" detour. This derived
   list is what you verify against later; do not carry a remembered list from
   another pipeline.
4. **What the input must contain.** The model and its label file say what the
   pipeline can detect. A person detector over an empty-road dataset produces a
   technically perfect run with nothing in it. Match the content to the labels,
   and if the user's chosen source plainly does not, say so before spending a
   build on it.

Report these four in one short block when you have them. It is the cheapest way
for the user to catch a wrong assumption before it costs a run.

## Step 3 — provision the input automatically

Having derived the requirement, satisfy it without asking:

1. **Reuse before fetching.** Check the media library for an asset already at the
   required geometry. Re-downloading and re-transcoding something already present
   is the most common wasted step in this flow.
2. **Otherwise fetch one.** For a URL or a local file, fetch it, transcode to the
   required geometry and frame rate, upload it through the media upload endpoint,
   assign a free slot, start the stream. Keep the transcoded asset so the next
   run reuses it. Where the user named no source at all, choose one that matches
   the labels from step 2 and say which you chose and why — a stated choice they
   can override beats a question that stops the run.
3. **A dataset rather than a video.** Research datasets ship as per-scene image
   sequences or short per-camera clips, not one stream. Pick the camera whose
   viewpoint the pipeline expects, assemble that camera's frames into a single
   H.264 clip at the required geometry, set the frame rate **explicitly** (a
   dataset's capture rate is rarely the pipeline's), then continue as case 2.
   If the download needs an account and a licence, ask for the archive — that is
   the one legitimate question about a source.
4. **A live camera or existing RTSP source** — use it directly when its geometry
   matches, and say plainly it must be restreamed if it does not.

Then point the pipeline at what you actually started: take the server address
from the streams listing (never a loopback the board cannot reach), and write the
input URL and the source geometry fields together, into both copies of the params.
They move as one unit — a URL changed without the geometry leaves the pipeline
decoding to one shape while being fed another, which corrupts memory rather than
failing cleanly.

## Step 4 — build

Cross-compile in the ROS 2 SDK container. Both outcomes of `prepare_ros_build`
are that container: Studio starting it, or you handing the user a command that
execs into it. If the container is missing, that is the question above — ask; do
not fall back to the board on your own initiative.

Poll the build to a real terminal state and read its exit marker. A build that
merely went quiet is not a build that passed.

## Step 5 — deploy, pre-flight, launch

`edgematic-ros2-portable-pipeline` holds the detail. The four that decide whether
the run works at all:

- **Deploy to a directory the SSH user owns.** A root-owned target fails while
  the archive restores timestamps, after appearing to copy fine.
- **Clear prior deployments from EVERY path this board has used**, not just the
  one you are deploying to. A container left from an older directory holds the
  accelerator just as firmly, and it is easy to miss because you are looking at
  the wrong tree. Bracket a character in any process-matching pattern so it
  cannot match — and kill — your own session.
- **Launch detached**, output to a log file. A backgrounded launch over a
  non-interactive SSH command dies when that command returns; the tell is real
  frames for about twenty seconds and then nothing.
- **Start the visualisation bridge last**, after the deploy and after the
  pipeline. A deploy overwrites it in place and kills it.

If a run crashes, **fix the configuration before relaunching**. Each crashed run
leaks accelerator segments from a fixed pool, so retrying an unchanged mistake
makes the next attempt strictly worse — runs dying at ever-lower frame counts are
the pool going, not the code degrading. The reboot that clears it is the
destructive act you already have a policy for.

## Step 6 — verify against the topics you derived, then show

A tool reporting `started` has told you a process was spawned, nothing more.
Before telling the user it works:

- the log is past the point where earlier attempts died, at the rate the params
  ask for, with no discarded frames and no input-buffer failure;
- the process is still alive **from a second session** — that is what proves the
  detachment held;
- **the topics from step 2 are actually publishing**, at a non-zero rate, and the
  output leaves the board (a live rate on the annotated topic, or a non-zero
  count on the output channel).

Then show it: open the viewer on the annotated image topic **that the code
publishes**, not one remembered from another pipeline. When listing topics, show
the ones actually publishing rather than everything advertised, and include the
raw input and the detections — if one of them is missing, name it plainly rather
than quietly returning a shorter list. An advertised-but-silent list reads as a
healthy pipeline, and is how a dead run gets reported as a live one.

## Report at the end

What ran, what you skipped and why, what you worked around, and anything the user
now owns — a board left rebooted, an asset added to the library, a question you
could not answer. Keep it short: the pipeline is the deliverable, not the prose.
