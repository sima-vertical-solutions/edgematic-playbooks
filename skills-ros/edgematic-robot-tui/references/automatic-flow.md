# Workspace and tool sequence

Read this with the skill entrypoint before preparing a robot TUI. All application
facts come from the repository provided in the prompt and live observations.

1. Resolve the named/current selected paired device. Discover the actual tool
   catalog and ROS feature state. If Studio exposes no toggle tool, use its
   Robotics settings instead of inventing a tool name. Reuse the current
   workspace/session after a feature change.
2. Reuse the selected dedicated parent containing the application and sibling
   `sima-core`. If none exists, a fresh dedicated project can use
   `"parent": "/workspace/robot-tui-demo"` for the clone calls.
   Never use `/workspace` itself as the ROS project: Studio cannot adopt its projects
   root. Give `clone_repository` an explicit non-empty destination folder when
   the current schema requires one.
3. Inspect the user-supplied repository and its pinned dependency manifests.
   Import application-owned dependencies under the location declared by its
   build script, such as `<selected-workspace-parent>/<application>/src`.
   Import every selected capability/client dependency plus its sensor provider
   at the declared revision before the first build, using the exposed clone
   tool. Record immutable revisions; do not silently advance dependencies.
4. Open that dedicated parent with `open_ros_workspace`. Respect a returned
   project-rebind boundary. Use only the provider's advertised project-shell
   capability for checked-in provision/staging helpers. Inspect their supported
   options; if the upstream revision lacks a helper, implement it locally from
   [the payload contract](payload-and-lifecycle.md) using the selected application contract.
5. Prepare the board using the selected paired identity and
   [bootstrap contract](bootstrap-and-build.md). Scope readiness to the actual
   requested modes; a menu-only exception cannot certify live inference or
   movement. Do not proceed through a provisioning failure.
6. Call `prepare_ros_build` with the real build-script name. Poll the persisted
   build to a terminal success. Stage and verify the complete named payload,
   then call `deploy_to_device` with the current project, paired device and
   relative payload directory. Preserve the robot's existing runtime root when
   adding a separate perception application.
7. Open the supported Robot TUI panel or device PTY and carry out
   [TUI acceptance](tui-acceptance.md). Only emit the Robot TUI directive when
   the current Studio build supports it and the configured launcher matches
   the deployed robot application.

The agent owns these setup steps within the user's authorized scope. Do not
hand the user a list of repository names, build commands or board repairs to
perform when the available tools can do the work.
