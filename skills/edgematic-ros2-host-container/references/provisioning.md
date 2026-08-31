# Provisioning the ROS 2 SDK container

Reference for `sima-core`'s `tools/docker/provision-modalix-deps.sh`. Read it
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

Inside the container, as root:

```bash
sudo bash /workspace/sima-core/tools/docker/provision-modalix-deps.sh
```

From the host, against the real container name:

```bash
docker exec -u 0 -it <container> \
  bash /workspace/sima-core/tools/docker/provision-modalix-deps.sh
```

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

- **not root** — the script apt-installs packages. Re-run with `sudo`, or
  `docker exec -u 0`.
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

## It does not survive a recreated container

Every change lands in the container's writable layer. A fresh
`sima-cli sdk setup`, or removing and recreating the container, discards all of
it, and the next build fails on a missing dependency with nothing saying why.
Either re-run the script — it is idempotent — or snapshot the provisioned
container from the host:

```bash
docker commit <container> <image>:<tag>
```
