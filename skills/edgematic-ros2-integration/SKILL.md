---
name: edgematic-ros2-integration
description: >-
  Use when working on running SiMa ROS2 pipelines (e.g. yolov8_seg) on a Modalix
  SoM/devkit and wiring them into Edgematic Studio's agentic chat. Covers
  flashing the SoC, installing ROS2 + Neat, building and running the
  vdp-simaai-ros2 pipelines, Foxglove/Flora visualization, and installing the
  Edgematic Studio skills (playbooks) into the Neat SDK container so Claude/Codex
  can drive Edgematic features. Trigger on mentions of ROS2, Neat, SoM/Modalix,
  yolov8_seg, foxglove/flora, or "edgematic skills / playbooks".
---

# ROS2 + Edgematic Integration

This skill captures the working setup for running ROS2 Neat pipelines on the
SoM and integrating them with Edgematic Studio. It is distilled from the
Edgematic team's Slack discussions (Satyavrat Prabhune, Yaroslav Shymkiv,
Oleksii Tsybulskyi) and should be treated as the current known-good path.

## When to use

- Getting a ROS2 pipeline (yolov8_seg and similar) building and running on a
  Modalix devkit/SoM.
- Visualizing pipeline output with Foxglove bridge / Flora Suite.
- Making Edgematic Studio's agentic chat aware of Edgematic-specific skills
  (playbooks) so the agent can invoke Edgematic features.

## Environment / version rules (read first)

- Neat core 0.2.x is compatible with SoC platform 2.1.2. 0.1.0 is for
  2.0.0. Seeing 0.0.0 or 2.0.0 in Neat components means the wrong package
  is installed. Check the developer.sima.ai compatibility guide before debugging.
- For the ROS2 pipelines use Neat core **0.2.1** specifically:
  `sima-cli neat install core@v0.2.1`. PyNeat is not needed (pipelines are C++).
- These pipelines are known-good on SoC **2.1.2** (`2.1.2_release_master_B1291`).

### Which platform does Neat install onto?

`core@v0.2.1` publishes **two** platforms, so the same command does different
things depending on where you run it:

| Platform | Where | Payload |
| --- | --- | --- |
| `board` (modalix 2.1.2) | the DevKit | `neat-runtime`, `neat-appcomplex`, `neat-gst-plugins`, `neat-internals-dev`, `neat-ev74-firmware` — all `arm64`; `pyneat` `aarch64` wheel |
| `palette` (2.1.2) | the Neat **SDK container** | `sima-neat-*-Linux-{core,dev}.deb`, `sima-lmm-*-Linux-{cli,core,dev}.deb`, `neat-common_*_all.deb` |

So a **host/SDK-side build is a supported path** — the palette platform exists
precisely for it. Do not assume Neat is board-only.

`sima-cli neat install` is **interactive** (it prompts for opt-in resources with
a Space/Enter picker). Under `docker exec` without a TTY it fails with
`Warning: Input is not a terminal (fd=0)` followed by a misleading
`Failed to retrieve or parse metadata`. Run it with `docker exec -it`, or drive
it from a script that allocates a PTY — the metadata is fine, the picker is not.

## Part A — ROS2 pipeline on the SoM

1. **Flash SoC to 2.1.2** using the STMS eLxr TFTP/Netboot flashing steps.
2. **Install ROS2** on the devkit (STMS "Setup ROS2 in eLxr on the Board").
3. **Install Neat** core 0.2.1: `sima-cli neat install core@v0.2.1`.
4. **Clone** `vdp-simaai-ros2` on the devkit. The circulated instructions say
   branch `yolov8_seg_neat_integration`; that branch **does not exist** on the
   remote (verified 2026-07-29). Use **`neat_integration`**.
5. **Start the RTSP server** and edit
   `packages/yolov8_seg/params/yolov8_seg.yaml` for the app used.
6. **Build & run:**

   ```bash
   apt install git
   cd /data/workspace/vdp-simaai-ros2
   source /usr/local/ros2/local_setup.bash
   ./build.sh yolov8_seg
   ./run.sh yolov8_seg
   ```

   Ignore the error from `apt install simaai-socpipeline-dev`.

> On the Edgematic DevKit the workspace lives at
> `/media/nvme/ros-work/vdp-simaai-ros2`, not `/data/workspace/...`, and ROS2 is
> at `/usr/local/ros2/local_setup.bash` (there is no `/opt/ros`). The overlay
> `install/setup.bash` must also be sourced for `simaai_common` message types.

### Known failure modes

- **Node not found at lifecycle set** — `./run.sh` loads `/neat_inference`
  into the container but the follow-up
  `ros2 lifecycle set /neat_inference configure && ... activate` dies with
  "Node not found". The composable node is loaded but not resolvable by
  `ros2 lifecycle`; check the node is actually spun up and the name matches
  before the lifecycle command runs, and that both share the same ROS domain /
  sourced environment.
- **Zero frames from an RTSP source** — pipeline runs but
  `processed=0 pulled=0`. Often a SoC-build mismatch; confirm the board is on a
  supported build (2.1.2) and the RTSP source is reachable on the same network.
- **`module 'pyneat' has no attribute 'Graph'/'InputKind'`** — SDK installed via
  deprecated instructions or wrong channel. Reinstall via the official
  getting-started dev-environment instructions with the matching version tag.

See the `edgematic-ros2-neat-nodes` skill for the failure modes specific to driving this
from Edgematic chat (stale `component_container_mt`, unwritable `HOME` over SSH,
root-owned log file).

## Part B — Visualization (Foxglove / Flora)

- Install the **Foxglove bridge** on the board (VP Confluence
  "foxglove_bridge installation on a board").
- Run the **Foxglove client on the host** to render the pipeline with overlays
  (Mykola's overlay scripts). Install the extensions from the `vdp-simaai-ros2`
  repo ("FoxGlove extensions installation" page).
- **Flora Suite** (open-source, maintained fork of Foxglove Studio 1.x) is the
  preferred forward path: it integrates with Foxglove Bridge already used by the
  robotics teams. Rerun is an alternative for heavy ML multimodal data.

> Edgematic bundles Flora at `/flora` and drives it from chat. Raw image topics
> do not fit down a VPN link (~11.8 MB/s needed vs ~7.7 MB/s available) — point
> the Image panels at the `/compressed` topics. See `edgematic-foxglove-viz`.

## Part C — Edgematic Studio skills (playbooks) into the Neat SDK container

Key facts:

- Edgematic is **not** shipped with skills. Neat SDK env setup auto-installs
  Neat skills, but Edgematic-specific skills must be installed separately via
  `sima-cli playbooks`.
- Skills live in the **public** repo `sima-vertical-solutions/edgematic-playbooks`
  under `skills/`. It needs no token. Studio's SDK extension installs from it by
  default — `infrastructure/sdk-extension/source.json` carries
  `skills.source: gh:sima-vertical-solutions/edgematic-playbooks`.
- Distribution copies each skill into the per-agent home dir:
  `~/.claude/skills/<skill-id>/` and `~/.codex/skills/<skill-id>/`.
  Claude Code (subscription) reads `~/.claude/skills/` on launch; the
  in-process anthropic backend (API key) scans the same folder at startup via
  `discover_skills()`. One install works on both paths.
- Only skills whose `env_type` includes the SDK env are picked up inside the
  Neat SDK container. If a skill is "skipped", update its `env_types` in its
  `playbook.yml` so it is not host-only.

### Installing by hand

The Studio installer does this for you. Install by hand only when tracking an
unmerged branch, or when checking a skill you have just edited:

```bash
sima-cli playbooks install gh:sima-vertical-solutions/edgematic-playbooks
```

Add `@branch` to take an unmerged branch, and `--force` to overwrite an
existing copy. To test a working tree before it is pushed, point it at the
directory instead:

```bash
sima-cli playbooks install ./skills/edgematic-ros2-neat-nodes --force
```

Then verify the skills landed in `~/.claude/skills/<skill-id>/` (and
`~/.codex/skills/`), and check the install summary: `detected` counts the skills
found, `valid` those that passed validation, `discarded` those dropped, with the
reason printed — most often malformed YAML frontmatter.

If the Edgematic activation alias is missing after starting the container and
socat, source `~/.bashrc` and run `grep activate ~/.bashrc`; reinstall the
Edgematic build via `sima-cli install` if only `activate-model-compiler` shows
up.

### Notes

- Neat ships its skills the same way (`sima-cli playbooks install
  gh:sima-neat/playbooks`). Edgematic moved to this pattern in VP-15488;
  before that it installed from the Bitbucket repo behind an auth wall, and
  older notes still describing a Bitbucket API token are out of date.
- Skills are refreshed on install/update, so a change merged to
  `edgematic-playbooks` propagates without a Studio release.
