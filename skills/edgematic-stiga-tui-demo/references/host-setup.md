# Stiga host setup and deployment

Read this reference only when the workflow reaches host provisioning or
deployment, or when the board launcher is missing. These operations run in a
real host terminal, not inside EdgeMatic's ROS SDK container.

## Preconditions

- Docker and `sima-cli` are installed and usable by the host user.
- The operator can authenticate to the requested board.
- `stiga` and `sima-core` are siblings under the directory shared with the ROS
  SDK container.
- The intended Stiga revision is checked out and recorded before the build.
- No unrelated deployment or robot workload is being replaced.

Provisioning may prompt for `sima-cli` choices or board authentication. Keep it
attended and do not paste credentials into agent chat.

## First use or a reflashed board

NVMe is not needed to open the TUI. The provisioner checks it for the full
Stiga mapping workload because RTAB-Map persists maps, bags, captures, and logs
under `/media`; those writes must not consume the board's eMMC root.

From the Stiga repository on the host:

```bash
cd <shared-parent>/stiga
./tools/deploy/provision.sh --board <ssh-user>@<board-host> [--no-imu]
```

Use `--no-imu` only when the target lacks Stiga's supported SPI IMU. The
provisioner installs the ROS 2, navigation, RTAB-Map, and Neat runtime expected
by the full stack. Its NVMe check protects mapping workloads that write under
`/media`; do not report a board as fully provisioned when that check fails.

## Build and deploy

For a fully provisioned board:

```bash
cd <shared-parent>/stiga
./deploy.sh --board <ssh-user>@<board-host> [--no-imu]
```

For a known ROSBOT used only for the operator TUI transport demo, where the
operator has confirmed both the missing SPI IMU and missing NVMe prerequisite:

```bash
cd <shared-parent>/stiga
./deploy.sh --board <ssh-user>@<board-host> --no-imu --skip-provision-check
```

`--skip-provision-check` is a narrow demo waiver. It does not validate mapping,
RTAB-Map, or a production robot run. Do not add `--run`: that starts the
headless stack instead of leaving the interactive TUI for EdgeMatic to open.

The deployment script owns the container build, runtime vendoring, board copy,
and creation of `/root/sima_ws/run_stiga_tui.sh`. If it fails, preserve the
specific phase and exit status; do not reconstruct the payload by hand.

## Verify the board entrypoint

Check the generated launcher without starting the robot:

```bash
ssh <ssh-user>@<board-host> \
  'test -x /root/sima_ws/run_stiga_tui.sh && echo TUI_READY'
```

Expected output is `TUI_READY`. A missing file means deployment is incomplete,
not that EdgeMatic needs a different command.

If Studio's panel exits before rendering, isolate the board and PTY path:

```bash
ssh -tt <ssh-user>@<board-host> /root/sima_ws/run_stiga_tui.sh
```

The double `-t` forces a PTY even when the caller's stdin is not initially a
terminal. Press `q` to exit. Do not press Stiga movement-mode keys during this
smoke test. If a mode was entered manually, press `i` for idle/stop before
exiting.

## Return evidence to the agent

Return only:

- board name/address and hardware variant;
- checked-out Stiga revision;
- provision and deploy command flags;
- command exit status and active elapsed time;
- `TUI_READY` result; and
- any NVMe, IMU, or runtime warning that remains.

Redact passwords, tokens, private-key material, and unrelated shell history.
