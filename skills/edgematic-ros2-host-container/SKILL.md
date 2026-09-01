---
name: edgematic-ros2-host-container
description: >-
  Use when the ROS 2 container has to be created, provisioned or repaired on the
  user's own host before any ROS 2 work can start — there is no ROS 2 SDK
  container yet, the container was recreated and lost what was installed into
  it, or a workspace build dies within seconds on a build dependency the
  container does not carry (GTSAM, socpipeline, shapely). Covers the three
  steps: the install command the user runs on the host because Edgematic Studio
  cannot, cloning sima-core into the directory Studio and the ROS container both
  mount, and running sima-core's in-place provisioning script inside the
  container. Trigger on "install ROS2", "set up the ROS container", "I have no
  ros2-sdk container", "provision the container", or a build that fails on a
  missing build dependency. Do NOT use for choosing capabilities or building an
  existing workspace (see edgematic-ros-capabilities), preparing a DevKit before
  a run (see edgematic-ros2-board-setup), running a pipeline on the board (see
  edgematic-ros2-neat-nodes), or SoC flashing and board-side ROS 2 (see
  edgematic-ros2-integration).
---

# Standing up the ROS 2 container on the host

The ROS 2 toolchain lives in a **second container**, beside the one Edgematic
Studio runs in. This skill gets that container onto the user's host and makes it
able to build. It stops there: choosing capabilities and running a build is the
`edgematic-ros-capabilities` flow, and that flow assumes everything below is
already true.

## What "done" looks like

Three facts, each separately checkable. Confirm them rather than assuming the
step that was supposed to produce them worked.

1. A ROS 2 SDK container is **running** on the host. Inside it,
   `/etc/sdk-release` reports `SDK Type = ros2-sdk` — that line is the
   machine-readable discriminator, and it is what tells this container apart
   from the Neat cross-compilation SDK.
2. The host directory Studio mounts is mounted into it **at the same absolute
   path** — `/workspace` on both sides by default. Everything downstream depends
   on this: Studio resolves paths and hands them to the container untranslated.
3. `sima-core` is cloned inside that shared directory, and its provisioning
   script has been run in the container.

## Step 1 is the user's to run, not yours

Studio has no shell on the host, no Docker socket, and no channel into a
container it is not inside; `sima-cli`'s SDK commands are host-only by design.
So there is no tool for this, and looking for one wastes a round. Present the
command as a copyable block, say plainly that they run it on the host, and wait
for them to report back before moving on.

## Step 1 — install the ROS 2 SDK container

On the host:

```bash
sima-cli neat install ros2-sdk
```

It needs `sima-cli` 2.1.16 or newer, already on the host — it is the same CLI
that created the Neat SDK container Studio is running in, so it is normally
there. If the version is older, update it first with
`sima-cli selfupdate --prod`.

The command downloads the matching image and walks the user through
`sima-cli sdk setup`. Afterwards:

```bash
sima-cli sdk ls        # what is installed, and whether it is running
sima-cli sdk ros2      # open a shell in the ROS 2 container
```

**The published package is arm64-only.** On an arm64 host it installs natively.
On x86_64 the compatibility check refuses — that is the package being honest,
not a broken install, so read the refusal back rather than retrying it. The
image can be run under emulation once arm64 binfmt is registered on the host
(`docker run --rm --privileged tonistiigi/binfmt --install arm64`, then install
with `--force`), at a large cost in build time. Offer that as the unsupported
escape hatch it is; do not present it as the path.

**Do not assume the container is named `ros2-sdk`.** `sima-cli sdk setup` names
containers after the image reference, so the real name is usually longer. Read
it from `sima-cli sdk ls` or `docker ps` before using it anywhere. Studio's ROS
build tools address the container by a configured name that defaults to
`ros2-sdk`; when the real name differs, that setting has to point at it, and
that is an operator change — say so rather than renaming things to fit.

## Step 2 — clone sima-core into the shared directory

Use `clone_repository`. Set `repo` to `sima-vertical-solutions/sima-core` and
`parent` to an absolute path **inside the directory Studio and the ROS container
both mount, and not Studio's projects root itself** — a subdirectory of that
mount. `parent` does not have to exist; a single missing level is created for
you, so name one and get on with it.

Cloned outside that shared mount, everything looks fine until the build, which
then fails on a path the container cannot see.

**Never clone through a shell** — not through a provider's own shell tool. A
hand-written clone either writes the token into the repository's own config,
where it survives the call and travels with the tree, or it fails outright on a
private repository; and without the Git-LFS filters it reports success while
every mesh on disk is a pointer file. `clone_repository` handles both, and fails
loudly exactly where a hand clone looks clean.

**Ask for a GitHub token only after a refusal asks for one.** Call
`clone_repository` with no `token`: Studio resolves the credential itself, from
its own configuration or from one stored earlier. Only when the call comes back
`clone_unavailable` with `requirement` set to `token` do you ask — once, in one
sentence, for a token with read access — then retry the same call and tell the
user it is stored and will not be asked for again. Opening a container setup
with a secret prompt asks for a secret before showing that it is needed. The
other `requirement` values, `git` and `git_lfs`, are an operator's to fix:
report which one, and stop.

The provisioning script the next step runs is on sima-core's default branch, so
a plain clone lands on it. If it is missing, the checkout predates it: re-clone,
or pass `ref`. Do not reconstruct its steps by hand.

## Step 3 — provision the container, in place

The stock image cannot build sima-core as it ships: GTSAM is in no eLxr apt
repository, and the SoC development headers collide with the Neat headers the
image now carries. sima-core ships a script that resolves both **inside the
container you already have** — there is no second image to build.

The script must run **as root**, and it refuses to run anywhere that is not this
container (it checks `/etc/sdk-release` for `SDK Type = ros2-sdk`), so it cannot
be run on the host by mistake.

**Run it from the host, as uid 0** — against the container name resolved in
step 1:

```bash
docker exec -u 0 -it <container> \
  bash /workspace/sima-core/tools/docker/provision-modalix-deps.sh
```

**Do not tell the user to reach for `sudo`.** `sima-cli sdk ros2` attaches as
the mapped host user, and the image ships no `sudo` — so inside that shell the
script refuses for not being root, and the obvious repair fails a second time
with a command that does not exist. That is two dead ends in a row, which is
why the host form above is the one to give. If a shell opened in that container
already reports uid 0 — `sima-cli` falls back to no user mapping when the
container cannot map one — running the script directly from it is fine.

It is idempotent — a re-run redoes only what is missing — and tees every run to
a log under `/tmp`, so a run that dies partway can be read back instead of being
whatever survived the terminal scrollback. The GTSAM source build is the slow
part, tens of minutes; `--skip-gtsam` is safe unless the visual-odometry
capability is being built. Flags, guards and the failure modes worth recognising
are in [references/provisioning.md](references/provisioning.md).

## What the provisioning does not survive

Everything the script installs lands in the container's **writable layer**, so
recreating the container — a fresh `sima-cli sdk setup`, a `docker rm` — throws
it away. The next build then fails on a missing dependency again, with nothing
saying that anything was lost. Two responses, and say which one you are
proposing:

- re-run the script — cheap, idempotent, and correct;
- snapshot it so it survives: `docker commit <container> <image>:<tag>`.

A build that fails on a missing build dependency in a container that worked
yesterday is this, not a workspace problem. Check the container's identity and
provisioning before touching the workspace.

## What not to do

- Do not try to run the host commands yourself, or hunt for a tool that would.
  Studio cannot reach the host, and the ROS container is not the one it is in.
- Do not build a separate image for this. Layering a derived build image on top
  of the SDK image was the older path; provisioning the stock container in place
  replaced it, and keeping both leaves two containers that disagree.
- Do not put the workspace outside the shared mount, and do not put it in
  Studio's projects root.
- Do not ask for a credential before a refusal has asked for one.
- Do not report the container as ready because a command printed no error. Check
  the three facts under "What done looks like".

## Where the pieces live

| Concern | Skill |
| --- | --- |
| Capability selection and building the workspace | `edgematic-ros-capabilities` |
| Preparing a DevKit before a run | `edgematic-ros2-board-setup` |
| Running and introspecting a board pipeline | `edgematic-ros2-neat-nodes` |
| SoC flashing and board-side ROS 2 | `edgematic-ros2-integration` |
| Pairing, device status, deployment | `edgematic-device-ops` |
