# Bootstrap and build lessons

Derived from Stiga PR #55 at `5525b80b3ff57b82ed12f5cf5bba1440fa88cda3`.
These are reusable contracts, not a claim that the PR is merged or deployed.

## Host and SDK

- Inspect the actual container image architecture. Native ARM64 needs no QEMU.
  On AMD64, test that the ARM64 SDK can execute before starting a build.
  `exec format error` after reboot can mean lost binfmt registration, not a
  broken workspace. Follow `edgematic-ros2-host-container` for the installer's
  pinned binfmt helper; do not copy the old PR's floating image tag.
- Preserve the provisioned container and its shared workspace. Recreating it
  loses installed dependencies. Restarting it loses the build-channel process;
  re-run the checked-in channel provisioner and verify the rendezvous endpoint.
- If Git rejects bind-mount ownership, trust only the exact application and
  dependency repositories involved, never `safe.directory=*`.
- Import the manifest-pinned dependencies. `vcs import` does not advance an
  existing branch; explicitly verify revisions instead of assuming it updated.
- Check Python build dependencies separately from native SDK libraries. The
  presence of a SoC library does not prove `pydantic`/`py_trees`/`shapely` exist.

## Concurrency and timing

Default to one Colcon package at a time, with `max(1, online CPUs - 2)` compiler
jobs. Set `MAKEFLAGS` and `CMAKE_BUILD_PARALLEL_LEVEL` consistently. Giving both
Colcon and each compiler the full CPU count multiplies concurrency and can OOM.
Honor a more specific current user/build policy. Validate overrides as positive
integers. Report active build duration, excluding suspended time.

The historical 41-package AMD64/QEMU build took 1h29m32s; it is evidence about
that build, not a promise for another host. Native Apple Silicon timing was
unvalidated. Fields2Cover v1.2.1 specifically needed `INSTALL_CMAKE_DIR=lib/`
(trailing slash) and its own tests/tutorials disabled; apply only if that
dependency/version is selected.

## Board preparation

- Use Studio's managed pairing identity, non-interactive SSH and a bounded
  connection timeout. Authentication failure means repair the pairing; do not
  request a private key or fall back to a password loop.
- Obtain exact ROS/navigation/RTAB-Map/Neat package specs from the selected
  release manifest or SDK metadata. Inside the SDK, `/usr/local/bin/install-ros2`
  and `/etc/sdk-release` can provide these without nested Docker. Missing specs
  are a gap, not permission to skip required runtime installation.
- A stdlib-only menu may defer an inaccessible private Neat snapshot, NVMe and
  SPI IMU checks. That exception ends at menu acceptance: inference needs a
  compatible Neat runtime; motion requires its base and sensors; mapping and
  rosbag recording need their declared storage.
- Verify `/media` is the intended mounted storage before creating map/bag/log
  directories there. `mkdir /media/bags` on eMMC can mask a missing NVMe mount.
- Aggregate host installation failures and board-side verification failures.
  Print readiness and exit zero only when both pass. A final remote check
  cannot erase earlier package-install failures.
- Some CLI resource menus need a PTY and an empty/default selection. Inspect
  current CLI behavior; use this only for the known optional-resource prompt,
  never to answer an unknown licence, credential, or destructive prompt.
