---
name: edgematic-stiga-tui-demo
description: Prepare, build, stage, deploy, and open a robot operator TUI through Edgematic Studio, including ROSBOT XL and Stiga. Use for robot TUI setup and coexistence with live perception; use ROS pipeline skills for inference itself.
---

# Robot operator TUI through Edgematic

This existing skill ID is retained for compatibility. Select the application
from the user's robot and its actual workspace: ROSBOT XL uses its ROSBOT
application; Stiga is not the default for every Modalix board.

The useful engineering knowledge from
[Stiga PR #55](https://github.com/sima-vertical-solutions/stiga/pull/55)
is preserved in the references below. The PR is withdrawn by the operator;
its feature branch and unmerged helper scripts are **not prerequisites**.
Do not reopen it, require its merge, or silently choose that feature ref.

## Execute

For a ROSBOT XL using micro-ROS, read the
[verified Modalix/MCU path](references/rosbot-xl-micro-ros.md) first. It covers
direct Ethernet, firmware routing, the working agent, motor order, and reusable
low-speed TUI controls; avoid rediscovering these or selecting a MAVLink driver.

Read [workspace and tool sequence](references/automatic-flow.md) first; it
preserves the dedicated-workspace and complete-dependency requirements.

1. Resolve the named/current selected device using `list_devices` and
   `get_device_status`. Pairing identity is authoritative. Require root only
   when the application's provisioning or deployment root requires it.
2. Inspect the current application's manifest, `deploy.yaml`, build script,
   TUI entrypoint and launch modes. Use `clone_repository` if sources are
   absent; resolve the current supported revision, not the withdrawn ref.
3. Read [bootstrap and build](references/bootstrap-and-build.md) when the
   host or board needs preparation. Inspect available script options before
   using them. Never assume the withdrawn PR's `--non-interactive`,
   `--tui-demo`, or staging script exists in the selected revision.
4. Build through the supported ROS SDK/build-channel path. Preserve a
   terminal successful build result and exact source revisions.
5. Read [payload and process ownership](references/payload-and-lifecycle.md).
   Prefer a checked-in staging script when present; otherwise implement a
   workspace-local staging helper from that contract as part of the
   authorized setup. Package a complete named payload and deploy it through
   `deploy_to_device`; an `install/`-only copy is often incomplete.
6. Inspect the actual Studio version for Robot TUI support and its configured
   launcher. Use the singleton panel when supported. Otherwise open the
   existing device terminal and run the verified application TUI through its
   PTY. Do not claim a missing panel opened or send an unsupported directive.
7. Read [TUI acceptance](references/tui-acceptance.md). Verify render, resize,
   singleton/session lifecycle and cleanup without movement keys.

When the deployed Studio supports the Robot TUI response directive and the
selected device's configured launcher is verified, emit:

```edgematic-robot-tui
```

## TUI and YOLO together

Keep teleoperation operator-controlled. The perception application must not
start a duplicate base controller or overwrite the TUI deployment. Inspect
the TUI's ROS domain, command topic and message type; ROSBOT XL can use
`TwistStamped`, so a Stiga `Twist` publisher is not a drop-in replacement.

Use the actual camera (UVC/Logitech and RealSense need different drivers),
derive its negotiated geometry, and match the detector's encoding and shape.
Put perception and the intended base state in the same ROS domain. Let one
owner operate the camera and one bridge serve Flora. Verify advancing raw,
detection and overlay samples while the operator drives; advertise only the
odometry that exists, commonly `/odometry/wheels` or `/odometry/filtered` on
ROSBOT XL. A video-only RTSP detector does not create odometry.

Do not issue motion keys during unattended validation. Do not substitute a
replay trajectory for live robot odometry. A working menu alone proves neither
movement nor inference. If hardware is unavailable, finish host/build/payload
work and report the exact physical acceptance still pending.

## Evidence

Record device, source/build revisions, successful staging marker, payload
digest, deployment result, panel/PTY checks, topic samples, active build time,
and remaining hardware limits. Keep credentials out of logs and handoffs.
