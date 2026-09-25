# Automatic EdgeMatic flow

Read this reference when executing the demo, not merely explaining it. The
operator's only required setup is installing Studio, pairing/selecting the
DevKit, and approving the agent's mutation confirmations.

## Operator contract

The operator may ask only for "the robot TUI demo" and is not expected to know
the Stiga codename or any repository, branch, dependency, workspace, build, or
deployment detail. Do not ask for those values. For this VP-15782 acceptance
bundle, use Studio's shared `/workspace` root and these known-compatible sources:

1. `clone_repository` `{ "repo": "sima-vertical-solutions/stiga", "parent": "/workspace", "ref": "feature/vp-15782-board-bootstrap" }`
2. `clone_repository` `{ "repo": "sima-vertical-solutions/sima-core", "parent": "/workspace", "ref": "develop" }`

Reuse them only when the existing checkouts match those revisions. Once the
Stiga bootstrap change is merged into its default branch, the released skill
must omit the temporary Stiga feature ref; the operator still supplies nothing.

## Tool sequence

1. Resolve the active paired device from the current turn's
   `[context: device_id=…]` prefix with `list_devices` and
   `get_device_status`. That per-turn UUID is authoritative unless the user
   explicitly names a different target in the same request. If neither exists,
   use the sole paired device; when several exist, stop for a selection rather
   than guessing. Never reuse a device name, UUID, host, or address from an
   example, earlier turn, agent history, log, or another workspace. Require the
   resolved device's SSH user to be `root`, because Stiga's platform
   provisioning and declared `/root/sima_ws` deployment cannot run through an
   unprivileged `sima` pairing. If it is not root, ask the operator to remove
   and re-pair that board as root; never request or repeat its password in chat.
2. If ROS Pipelines is off, call `set_ros_pipelines` with `enabled: true`, tell
   the operator the tools become available on their next message, and stop this
   turn. Do not ask them to start a new chat.
3. Reuse an existing Stiga project only when its remote and revision match the
   operator-contract sources above. Otherwise make the two `clone_repository`
   calls exactly as shown so Stiga and `sima-core` are siblings. Never ask the
   operator for those sources, and never clone either repository onto the board.
4. Call `open_ros_workspace` on the shared `/workspace` parent holding both
   checkouts. If it returns a rebind instruction, end the turn exactly as
   instructed; continue from the rebound project on the operator's next
   message.
5. Prepare the paired board from the bound shared workspace with the advertised
   confirm-gated shell tool (`run_command` for in-process providers, or the
   provider's native project shell when that is the only shell it exposes):

   ```text
   cd stiga && tools/deploy/provision.sh --board <ssh-user>@<board-host> --non-interactive --tui-demo
   ```

   Set `timeout_ms` to `600000` when using `run_command`. Do not pass a
   password, private-key path, package override, `--no-imu`, or NVMe override.
   The checked-in script auto-detects Studio's pairing key, makes the narrow
   TUI-demo IMU/NVMe boundary explicit, obtains package specs from the running
   SDK, and fails if board verification has gaps. Success must include
   `RESULT: board READY for the EdgeMatic TUI payload`.
6. Call `prepare_ros_build` with bare script name `build.sh` once. The checked-in
   script builds one package at a time with all online logical CPUs except two
   assigned to that active package. Do not override its job variables.
7. Poll `get_build_status` until its persisted state is terminal. Report actual
   active elapsed time; never include time while the machine or job was
   suspended.
8. Run the following command from the bound shared workspace using the same
   advertised shell capability as step 5:

   ```text
   cd stiga && tools/deploy/stage-edgematic-tui.sh
   ```

   Set `timeout_ms` to `600000`. Success must include
   `EDGEMATIC_STIGA_PAYLOAD_READY=edgematic-tui-payload`. This deterministic
   script vendors Stiga's Python dependencies, native libraries, overlay setup,
   DDS profile, version evidence, and safe run wrappers. Do not rewrite or
   reproduce those staging steps in chat.
9. Call `deploy_to_device` for the selected board with
   `payload: "edgematic-tui-payload"`. This named payload is the exception to
   the ordinary Stiga warning about generic ROS staging: EdgeMatic transfers the
   complete Stiga-authored payload as assembled, using the paired device key and
   the `/root/sima_ws` remote root from `deploy.yaml`.
10. After deployment succeeds, end the response with the bare directive below
   as its final line. It opens or focuses the selected device's fixed Robot TUI
   panel; it carries neither a command nor credentials.

   ````text
   ```edgematic-robot-tui
   ```
   ````

## Stop conditions

- Do not start a second build while one is pending or running.
- Do not build or deploy when board provisioning failed or timed out. Do not
  replace its paired-key authentication with a password prompt.
- Do not deploy after a failed or indeterminate build.
- Do not fall back to `deploy.sh`; it is a host convenience wrapper and
  deliberately refuses inside the SDK container.
- Do not use unnamed/default ROS staging for Stiga. Only the checked-in
  `stage-edgematic-tui.sh` output is complete enough for this demo.
- If the selected board lacks its base runtime, use only the checked-in
  provisioning script above. Do not invent platform-package commands or claim
  the overlay supplies them. A private Neat feature snapshot is deliberately
  skipped for the TUI-only demo; report that inference/movement was not tested.
- Never type a TUI movement-mode key during automated acceptance.

## Success evidence

Capture the paired device name, sanitized provisioning result, Stiga and
sima-core revisions, build terminal state and active duration, the staging
ready marker, deployment record/size, and whether the Robot TUI panel opened.
Exclude credentials and raw private paths.
