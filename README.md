# Edgematic Playbooks

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

Curated coding-agent skills for Edgematic Studio, the agentic visual development environment for building and running AI applications on SiMa.ai hardware with the Neat SDK.

Each skill teaches an agent one Edgematic Studio workflow — pairing a DevKit, compiling a model, deploying a pipeline, benchmarking it on the board — using the Studio HTTP API and its agent tools. `sima-cli` installs them into the agent skill homes (`~/.claude/skills`, `~/.codex/skills`), where the Studio agent discovers them at runtime.

Skills are installed automatically when you install the Edgematic Studio SDK extension. Install them by hand with the commands below.

## Install with sima-cli

```bash
sima-cli playbooks install gh:sima-vertical-solutions/edgematic-playbooks
```

Pin an immutable ref for a reproducible install — a tag or a commit SHA:

```bash
sima-cli playbooks install gh:sima-vertical-solutions/edgematic-playbooks@v0.1.0
```

Install a single skill by pointing at its directory:

```bash
sima-cli playbooks install gh:sima-vertical-solutions/edgematic-playbooks/skills/edgematic-device-ops
```

Reinstalling over an existing skill needs `--force`:

```bash
sima-cli playbooks install gh:sima-vertical-solutions/edgematic-playbooks --force
```

Then inspect what landed:

```bash
sima-cli playbooks list                      # installed playbooks and their source
sima-cli playbooks describe edgematic-device-ops
sima-cli playbooks update                    # refresh to the latest upstream commit
sima-cli playbooks remove edgematic-device-ops
```

`sima-cli` 2.1.0 or newer is required. Every skill installs for both supported agents, `claude` and `codex`.

## Skills

| Skill | What it covers |
| --- | --- |
| [`edgematic-studio-api`](skills/edgematic-studio-api) | The Studio HTTP + WebSocket API surface — projects, builds, deployments, runs, devices, models, agent tool invocation, and LLM settings. |
| [`edgematic-device-ops`](skills/edgematic-device-ops) | Pair, list, and remove SiMa DevKits; read live device status; deploy a project over SCP or NFS. |
| [`edgematic-build-deploy-run`](skills/edgematic-build-deploy-run) | Build a project, deploy it to a paired DevKit, run it on the board, and pull results back — including the async build/run poll flow. |
| [`edgematic-model-compile`](skills/edgematic-model-compile) | Compile your own ONNX model into a SiMa MPK — upload, attach calibration data, run a standard or custom-script compile, poll to completion. |
| [`edgematic-run-metrics`](skills/edgematic-run-metrics) | Benchmark a compiled model's latency, FPS, power, and energy on a paired DevKit, and read the resulting report. |
| [`edgematic-media-streams`](skills/edgematic-media-streams) | Manage the video media library and control RTSP/WebRTC streams — add and remove videos, start and stop streams, list inputs and outputs. |
| [`edgematic-view-streams`](skills/edgematic-view-streams) | Show the live video streams inline in the Studio chat as a multi-stream grid. |
| [`edgematic-ros2-host-container`](skills/edgematic-ros2-host-container) | Install the ROS 2 SDK container on the user's own host and provision it to build — the host-only install command, cloning sima-core into the shared mount, and the in-place provisioning script. |

## Layout

```text
skills/<skill-id>/
├── SKILL.md          # the skill body the agent reads (YAML frontmatter + Markdown)
├── playbook.yml      # install manifest: id, name, version, agents, compatibility
├── agents/           # per-agent interface metadata (openai.yaml)
└── references/       # supporting docs the skill links to on demand
```

`sima-cli` discovers a skill by walking the repository for any directory holding a `SKILL.md` or a playbook manifest, so `skills/` is a convention rather than a requirement — but keep to it.

## Contributing

Skill authoring rules, the manifest contract, and the local validation loop are in [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Apache License 2.0 — see [LICENSE](LICENSE).
