# Provisioning the ROS 2 SDK container

Reference for `sima-core`'s `tools/edgematic/provision-modalix-deps.sh`. Read it
when a provisioning run refuses, fails partway, or leaves a build still short of
a dependency. The workflow itself is in the skill body.

## What it is for

The published ROS 2 SDK image is a working ROS 2 environment, but it is not
enough to build `sima-core`: two of the dependencies are not installable from
the image's own repositories as it stands. This script closes that gap **in the
container that already exists**, rather than by building a derived image. A
derived image was the earlier approach; keeping both leaves two containers that
disagree about what is installed.

## Invocation

From the host, against the real container name:

```bash
docker exec -u 0 -it <container> \
  bash /workspace/sima-core/tools/edgematic/provision-modalix-deps.sh
```

This is the form to give. `-u 0` is not decoration: on Linux and macOS
`sima-cli sdk ros2` attaches with `docker exec -u <host user>`, so the shell it
opens is not root, and **the image ships no `sudo`**. From inside that shell the
script refuses for not being root, and `sudo` then fails as a missing command —
two dead ends where the host form has none.

`sima-cli` does drop the user mapping when the container cannot provide one, and
the image's own default user is root, so a shell that already reports uid 0 can
run the script directly. Check `id -u` rather than assuming either way.

Copying the script in first also works and is what the script's own header
suggests, but there is no need for it once `sima-core` is cloned inside the
shared mount — the container already sees the file at the same path.

## Options

| Flag | Effect |
| --- | --- |
| `--skip-gtsam` | Skip the GTSAM source build. Safe unless the visual-odometry capability is built — that one needs it. |
| `--force-gtsam` | Rebuild GTSAM even when it is already installed. |
| `--jobs N` | Compile jobs for GTSAM. Default 2. |
| `--log FILE` | Write the run log here instead of the default under `/tmp`. |
| `--no-log` | Do not write a log file. |
| `-h`, `--help` | Usage. |

Raise `--jobs` only on a host with real memory behind it. GTSAM's
template-heavy translation units each want multiple GB, and the default of 2 is
chosen so a compile is not killed by the out-of-memory killer on a small build
host. A raised value that gets a process killed presents as a build that simply
stops, not as an error naming memory.

## Guards, and what each refusal means

- **not root** — the script apt-installs packages. Re-run it through
  `docker exec -u 0` from the host. Not with `sudo`: the image does not have it.
- **`/etc/sdk-release` does not report `SDK Type = ros2-sdk`** — this is not the
  ROS 2 SDK container. The usual cause is running it on the host, or in the Neat
  SDK container. It refuses before touching anything, deliberately.
- **architecture is not aarch64** — a warning, not a refusal. The SiMa packages
  are aarch64-only, so the apt step will almost certainly fail from here. On an
  emulated x86_64 host the emulated container reports aarch64 and this does not
  fire.

## What it installs

Roughly in order: the SoC link libraries and headers plus the perception
development packages; the socpipeline libraries; the Python build and runtime
dependencies; the rtabmap system dependencies; and GTSAM from source.

Two of those need explaining, because they are the reason the script exists.

**socpipeline collides with Neat.** Since the base image gained Neat Core, it
ships a package owning the same headers as the socpipeline development package,
most of them with different content. Installing the development package the
plain way dies on a dpkg file conflict. Forcing the overwrite is the wrong fix —
it would replace Neat's newer headers with older ones several installed packages
depend on. The script instead installs the runtime package for its shared
objects and recreates the unversioned symlinks by hand, which is all the
workspace actually needs from the development package. If a build still cannot
link, check that those symlinks exist rather than reinstalling the development
package.

**GTSAM is not in any apt repository here**, so it is built from source, pinned
to the branch that matches the known-good configuration. This is the slow step,
tens of minutes, and nothing caches it — but it self-skips once installed, so a
second run is fast.

## Reading the outcome

The script ends with a summary naming the resolved versions of numpy, shapely
and socpipeline, whether GTSAM is installed, whether the link symlink is
present, and the log path. Read that summary rather than inferring success from
the absence of an error: an apt step that failed partway can still leave the
run looking finished in the scrollback.

Two values are worth a second look:

- **numpy must stay on 1.x.** The image ships 1.x, and the board's pinned
  scientific stack and the OpenCV bindings both expect it. `shapely` and
  `pyclipper` are therefore installed without their dependencies, on purpose —
  resolving shapely's metadata normally pulls numpy 2.x and breaks both. If the
  summary reports a 2.x numpy, something else pulled it in and that needs fixing
  before the build is trusted.
- **the link symlink** — reported missing means the socpipeline step could not
  find a versioned library to link against, and the workspace will fail at link
  time rather than at configure time.

## The build channel, and how it differs from everything else here

The script's last step provisions the **Edgematic build channel**: a small HTTP
endpoint inside the container, plus the address it publishes to
`<shared mount>/.edgematic/ros-build-channel.json`. Studio reads that file to
find it — nothing is configured on either side. Skip it with
`--skip-build-channel`, or run it alone with the sibling
`tools/edgematic/provision-build-channel.sh`.

It is the one part of this that **does not survive a container restart**, which
is a stricter statement than the section below. The binary and the script sit in
the writable layer like everything else and persist; the running endpoint is a
*process* and does not, and nothing restarts it. So a container that was
provisioned yesterday and merely restarted still has its dependencies and has
lost its channel.

The symptom is not an error: `prepare_ros_build` answers `run_on: "host"` and
hands back a command to paste, exactly as it does on a machine that never had a
channel. Check the published file first — it is written last, so its absence
distinguishes "provisioning never reached the tail" from "the process died".

Pass `GH_TOKEN` when launching it. The channel gives it to every build it
starts, and without one those fetches go out unauthenticated and can meet
GitHub's rate limit partway through a long build — reported as
`could not read Username for https://github.com` an hour in. The container's own
`gh` is normally signed out, so nothing recovers it locally.

## It does not survive a recreated container

Every change lands in the container's writable layer. A fresh
`sima-cli sdk setup`, or removing and recreating the container, discards all of
it, and the next build fails on a missing dependency with nothing saying why.
Either re-run the script — it is idempotent — or snapshot the provisioned
container from the host:

```bash
docker commit <container> <image>:<tag>
```
