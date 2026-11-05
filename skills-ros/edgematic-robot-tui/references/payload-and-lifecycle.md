# Complete payload and lifecycle contract

## Stage in the SDK, deploy through Studio

Read the application's `deploy.yaml`: remote root, ROS domain, system config,
runtime Python packages, native libraries, upstream setup files and DDS profile
are one runtime contract. Stage into a fresh owned directory containing:

- complete merge-install overlay and the installed TUI/config;
- declared native libraries and checked dynamic-library closure;
- declared Python dependencies, without replacing the board's compatible
  NumPy/SciPy/OpenCV ABI; `pip --no-deps --target` is appropriate for the
  explicitly selected pure-Python extras, not a general dependency solver;
- upstream setup handling, relocation-safe overlay loader and DDS profile;
- launch wrappers rooted at the declared remote installation;
- source revisions, dirty-state indication, build time and payload digest.

Reject unresolved Git LFS pointers and container-absolute symlinks. Verify the
installed TUI and system config exist before printing a staging-ready marker.
Do not mutate a shared install tree to stage a candidate: copy it first. Record the payload size and digest from the actual staged artifact.

The staging helper does no SSH. Use `deploy_to_device` with its named relative
`payload`, after the persisted build succeeds. Respect a deployment refusal;
do not bypass it with an improvised password/SCP flow.

## Launcher environment

Source ROS and upstream setup files with nounset disabled, then the relocated
overlay; generated ROS scripts can reference unset variables. Restore the
desired shell strictness afterwards. Export the manifest's ROS domain, native
library path and DDS profile. Confirm expected packages resolve from a fresh
shell, not only from the build environment.

Separate an owning launcher from a monitor/attach launcher. Detect actual
component processes: there may be no legacy aggregate launch parent. Do not
treat the TUI's own command line, a manual-only row, or a leftover KPI monitor
as evidence of a running base stack. Refuse conflicting owners rather than
starting a duplicate camera/controller/inference graph.

Track owned child process groups with identities and clean up only those.
On normal exit/signals, restore terminal state and stop the children this
session started. An attached monitor must leave the pre-existing stack running.
Do not kill unrelated launch processes or all component containers.
