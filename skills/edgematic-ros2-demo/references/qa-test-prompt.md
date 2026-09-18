# QA prompt — clean Edgematic ROS HELLO + VIEW demo

Use this prompt unchanged for acceptance on a clean, reserved Modalix DevKit.
Replace only the bracketed device value.

```text
Run the prepared ROS demo at /workspace/edgematic-demo end to end on the paired
device [DEVICE]. Treat this as clean-board QA, not a best-effort showcase.

Before the build, fail fast if the workspace/payload cannot supply
foxglove_bridge on a board where it is absent. Check the configured ROS domain,
board reachability, disk space, accelerator ownership, build channel, model,
video, launch/config files, and deploy path. Do not install board packages,
change platform libraries, reboot, or disturb unrelated workloads.

Do not hand setup steps back to QA. The prepared host script must provision its
SDK-local build dependencies and produce the payload; the packaged board runner
must perform SoC preflight, launch, verification, and soak. Use Studio's paired
device transport for deployment and execution. If one of those scripts omits a
required setup action, fail that gate and fix the script rather than asking QA
to repair the host or board manually.

Start exactly one build with build.sh. Poll it every 120 seconds and report:
elapsed time, persisted status, completed/total packages, completion percent,
active package/phase, log-update age, failed packages, and ETA with its basis.
Use ros_progress when present. Label the ETA provisional until a package total
and observed completion rate exist. Never start a replacement build while the
first is active. If cancellation is requested, require confirmed process
termination before starting another build.

After a successful build, stage and deploy exactly the declared payload. Clean
only a previously recorded instance of this demo. Launch detached with recorded
PIDs and the declared ROS domain. Verify HELLO from a fresh message sample.

For VIEW, use the inference node's real output: publish_raw_image and
publish_overlay must be true, the finite file must loop, and /image_raw,
/detections, and /detections_overlay must all have fresh non-zero rates. Any
JPEG/compressed adapter may subscribe to those real image topics only. It must
not read/replay the MP4, synthesize timestamps, reuse stale detections, or draw
its own overlay. Synthetic replay does not pass VIEW.

Start the packaged foxglove_bridge last. Verify its port is listening, then open
Edgematic's embedded live output automatically. Confirm the current bridge log
created subscriptions for the selected image and detections topics and confirm
the rendered frame visibly advances. Soak for at least two minutes; re-sample
topic rates and process identities at 10, 30, 60, and 120 seconds. Leave the
verified demo and bridge running for recording.

Do not report success from a PID, advertised topic, old rate sample, channel
list, or synthetic image. If any gate fails, stop at that gate and report the
exact command/evidence and the smallest corrective action. Do not silently
downgrade VIEW to HELLO or DEPLOY.
```

Acceptance evidence must include the source revisions, build ID and terminal
marker, deployed prefix, saved process identities, fresh topic rates at the end
of soak, bridge listener/subscriptions, and a human-visible advancing frame.
Keep credentials, private addresses, and raw logs out of the reusable report.
