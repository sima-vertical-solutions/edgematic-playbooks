---
name: edgematic-stiga-tui-demo
description: Prepare and verify a Modalix or ROSBOT board for the Stiga operator TUI demo in EdgeMatic Studio. Use when the user asks to pair the board, build or deploy Stiga, install its board runtime, create the TUI launcher, or test the Open Robot TUI action end to end. Do not use for generic ROS demos, arbitrary ROS packages, or production mowing.
---

# EdgeMatic Stiga TUI Demo

Prepare the selected board with Stiga's own deployment tooling, then prove that
EdgeMatic can open and control the interactive TUI session. Keep board setup,
Studio integration, and safety evidence distinct.

## Definition of done

Do not call the demo ready until all of these are true:

- the intended board is paired, selected, reachable, and identified by name;
- the requested Stiga revision was built on the host, never on the board;
- Stiga was deployed to `/root/sima_ws` with the hardware-appropriate flags;
- `/root/sima_ws/run_stiga_tui.sh` exists and is executable on the board;
- EdgeMatic's ROS Pipelines feature is enabled and its TUI command resolves to
  that launcher;
- **Terminal > Open Robot TUI** creates one interactive panel for the selected
  device, accepts resize, coexists with a normal local shell, and can be closed
  and reopened; and
- the session exits cleanly without issuing a robot movement command.

Record the exact revision, board, deployment flags, and observable checks. A
successful build alone is not a successful demo.

## Fixed workflow

1. Use `list_devices` and `get_device_status` to identify the selected board and
   confirm that it is reachable. If it is not paired, use `add_device`; request
   a password only through the secure pairing flow and never repeat it in chat
   or evidence.
2. Establish one shared host workspace containing sibling `stiga` and
   `sima-core` repositories. Reuse matching repositories. Otherwise use
   `clone_repository`, then `open_ros_workspace` for the Stiga workspace and
   honor its session-rebind boundary before continuing.
3. Build with `prepare_ros_build` using Stiga's checked-in `build.sh`. Poll
   `get_build_status` until it reaches a persisted terminal result. Never build
   Stiga on the board and never replace its build script with an ad hoc colcon
   command. The script owns the CPU policy and reserves two logical CPUs for
   other work.
4. At the host setup boundary, read
   [`references/host-setup.md`](references/host-setup.md). Stiga provisioning
   and deployment must run from an attended host terminal because they use
   Docker, interactive `sima-cli` setup, and SSH. Give the user the exact
   command for their board and wait for its result. Do not claim that Studio's
   container-scoped `run_command` performed a host operation.
5. Use Stiga's checked-in `deploy.sh` as the authoritative packager and
   installer. Do **not** substitute the generic `deploy_to_device` tool: that
   path stages a conventional ROS install tree but does not vendor every Stiga
   runtime dependency or generate `run_stiga_tui.sh`.
6. After deployment succeeds, verify that the launcher is executable. In
   EdgeMatic, enable ROS Pipelines, keep the TUI command at
   `/root/sima_ws/run_stiga_tui.sh`, select the paired device, and open
   **Terminal > Open Robot TUI**.
7. Run the acceptance checks below. Preserve evidence from the newest run and
   report failures at the boundary where they occurred: host build, board
   provisioning, board deployment, SSH/PTTY launch, or Studio terminal bridge.

## Hardware and storage boundary

NVMe is not required for EdgeMatic's TUI transport or the
`run_stiga_tui.sh` launcher. It is required by the full Stiga stack because
RTAB-Map maps, bags, captures, and logs belong on NVMe-backed `/media`, not the
board's small eMMC root.

For a ROSBOT without the supported SPI IMU, deploy with `--no-imu`. A board
without NVMe-backed `/media` may use `--skip-provision-check` only for the
operator TUI transport demo after the missing prerequisite has been stated.
That waiver does not make RTAB-Map, mapping, or production navigation
supported. Never describe eMMC-only storage as full Stiga readiness.

Do not use `deploy.sh --run` for this workflow. It launches Stiga's headless
stack, while this demo requires the interactive `run_stiga_tui.sh` entrypoint.

## TUI acceptance

Check each item rather than treating the first rendered screen as completion:

| Check | Required evidence |
| --- | --- |
| Selected target | Panel names or otherwise identifies the paired board that was requested. |
| Single session | Repeated open actions focus the existing TUI instead of creating duplicates. |
| Interactivity | The display responds to a harmless key such as `q`; no movement mode is entered. |
| Resize | The remote PTY follows at least one panel resize without corrupting or terminating the session. |
| Coexistence | A normal local terminal can remain open beside the robot TUI. |
| Lifecycle | Closing the panel ends its remote session; reopening starts a fresh usable session. |
| Cleanup | No Stiga process started by the test is left unintentionally running. |

The robot may move when mode keys are used. Never send `e`, `b`, `m`, `t`, or
`D` during automated or unattended verification. Use `q` to leave a menu. If a
mode was started manually, send `i` to request idle/stop before `q`.

## Diagnose by boundary

- If `run_stiga_tui.sh` is missing, the Stiga deployment did not complete or
  used the wrong remote root. Re-run the host deployment; do not point Studio
  at a fabricated replacement script.
- If the board is reachable over SSH but Studio rejects the session, confirm
  that the same paired device is selected and refresh its status.
- If **Open Robot TUI** is absent, confirm that the installed EdgeMatic build
  contains the feature and that ROS Pipelines is enabled.
- If the panel opens and immediately exits, run the direct PTY smoke test from
  the host reference and inspect that run's board-side error before changing
  EdgeMatic.
- If Stiga is already running, stop only the known Stiga session through its
  own controls or recorded process identity. Do not use broad `pkill` or stop
  unrelated board workloads.

## Handoff record

Report the selected device, board address without credentials, Stiga revision,
host build result and active duration, deployment flags, remote root, launcher
check, Studio acceptance table, and any NVMe/IMU limitation. Do not include
passwords, private keys, tokens, or an unredacted terminal transcript.
