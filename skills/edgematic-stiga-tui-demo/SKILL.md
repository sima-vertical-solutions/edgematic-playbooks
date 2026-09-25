---
name: edgematic-stiga-tui-demo
description: Automatically set up the host and paired Modalix or ROSBOT, build and deploy the supported robot operator demo, and open its TUI through EdgeMatic Studio. Use for requests such as "set up this robot demo" or "show the Robot TUI" even when the user does not know the Stiga codename, repositories, ROS dependencies, or commands. Do not use for generic ROS packages or production mowing.
---

# EdgeMatic Stiga TUI Demo

Drive this workflow with EdgeMatic tools. Do not hand the operator host-side
build, deploy, or SSH commands: after Studio installation and device pairing,
the agent owns repository setup, build, payload assembly, deployment, and TUI
open.

The operator does not need to know that the supported demo application is
Stiga. Treat a request for the paired robot's operator/TUI demo as this workflow
and choose the repositories, revisions, workspace layout, provisioner, and
payload yourself. Do not ask the operator for an application name, repository,
branch, workspace path, package list, or board-side install commands.

## Definition of done

The demo is ready only when:

- the intended board is paired as `root`, selected, reachable, and identified
  by name;
- the checked-in non-interactive provisioner reports the board ready for the
  EdgeMatic TUI payload through Studio's managed pairing key;
- the requested Stiga and sima-core revisions are recorded;
- Stiga's managed ROS build has a persisted successful result;
- the checked-in EdgeMatic staging script produced the complete named payload;
- that payload was deployed to `/root/sima_ws` through the paired device;
- the selected board's singleton Robot TUI panel opened automatically; and
- the session can exit without issuing a movement command or leaving a Stiga
  process unintentionally running.

A successful compile is not a successful demo. A pre-existing launcher is not
proof that the requested revision was deployed.

## Execute the workflow

Read [`references/automatic-flow.md`](references/automatic-flow.md), then carry
out its tool sequence. Important invariants:

- Build in the SDK container, never on the board.
- Provision with checked-in
  `tools/deploy/provision.sh --non-interactive --tui-demo`; never give the
  agent a device password or private-key path.
- Let Stiga's `build.sh` use all online logical CPUs except two; do not cap it
  further or multiply package-level and compiler-level parallelism.
- Stage with checked-in `tools/deploy/stage-edgematic-tui.sh` after the build.
- Deploy only its `edgematic-tui-payload` through `deploy_to_device`. The named
  payload contains Stiga's otherwise-missing runtime libraries, vendored Python
  packages, setup files, and generated launch wrappers.
- Open the panel with the `edgematic-robot-tui` response directive only after
  deployment succeeds. The directive selects the backend's fixed
  `/root/sima_ws/run_stiga_tui.sh`; it never contains a command.

The user may need to approve the build/deploy mutations and send a continuation
after enabling ROS tools or rebinding the cloned workspace. Those are product
authorization/session boundaries, not manual setup work. Do not ask the user to
run shell commands that the flow's tools can execute.

## Hardware and storage boundary

NVMe is not required for EdgeMatic's TUI transport, the 467 MiB Stiga overlay,
or `run_stiga_tui.sh`. The full Stiga mapping stack requires NVMe-backed
`/media` because RTAB-Map persists maps, bags, captures, and logs there rather
than saturating the board's eMMC root.

For an eMMC-only ROSBOT, accept the TUI demo while reporting that RTAB-Map,
mapping, and production navigation remain unvalidated. A missing supported SPI
IMU has the same boundary: it does not prevent rendering the operator menu, but
hardware-dependent modes are not accepted.

## Safe TUI acceptance

Check each item:

| Check | Required evidence |
| --- | --- |
| Selected target | The panel resolves the paired board requested by the user. |
| Single session | Reopening focuses the existing Robot TUI instead of creating a duplicate. |
| Render | The Stiga operator menu renders through the remote PTY. |
| Resize | The display follows a panel resize without exiting or corrupting. |
| Coexistence | A normal local shell remains usable beside the Robot TUI. |
| Lifecycle | Closing and reopening creates a fresh usable session. |
| Cleanup | Exiting leaves no stack started by the test unintentionally running. |

The robot may move when mode keys are used. Never send `e`, `b`, `m`, `t`, or
`D` during automated or unattended verification. Use `q` to leave a menu. If a
mode was started manually, request idle/stop with `i` before `q`.

## Diagnose by boundary

- No ROS tools: enable them with `set_ros_pipelines` and resume next turn.
- Build failure: report the persisted package/phase failure; do not deploy an
  older install tree.
- Missing staging script: the selected Stiga revision does not support this
  automatic flow; do not reconstruct the payload ad hoc.
- Missing ready marker: staging failed. Preserve its bounded stderr and stop.
- Deploy refusal: report the paired-device, transport, build, or payload error
  returned by `deploy_to_device`; do not bypass it with raw SSH.
- Provision refusal: report the exact sanitized gap and stop. Re-pair when the
  managed key fails; never fall back to interactive password authentication.
- Panel exits immediately: distinguish a missing base runtime from a launcher
  or PTY failure using the newest panel error. Do not restart unrelated board
  workloads.

## Handoff record

Report the selected device, board address without credentials, source
revisions, active build duration, staging marker, deployed payload size/remote
root, TUI acceptance table, and any NVMe/IMU limitation. Never include
passwords, private keys, tokens, or an unredacted terminal transcript.
