# Simulation troubleshooting

| Symptom | Check | Usual cause and fix |
| --- | --- | --- |
| No camera on the board, right after a load | `get_simulation_status`: timeline | The scene is loaded but stopped. `control_simulation` with `play`. |
| No camera on the board, timeline playing | `get_board_link` | `camera` is `null` (the robot has no camera: its robot record's `sensors` is empty), or `applied_state` is not `applied` yet. |
| `applied_state` stays `pending` | wait a minute, then `get_board_link` again | The simulator host applies a link within seconds; longer means the host's applier is not running. Report it; do not keep setting the link. |
| `applied_state: failed` | `applied.error` | The host refused the link (e.g. a topic name it does not accept). Fix the link with `set_board_link`, or go back to `{"mode": "auto"}`. |
| The robot does not move | the robot record's `drive` (`list_robots`) | `drive: null`: the bundle has neither a ros2_control `diff_drive_controller` nor a `drive` in robot.yaml. Draft one (SKILL.md section 3). Also check the board publishes on the link's `accept` topic, not a hard-coded `/cmd_vel`. |
| A skid-steer robot drives straight but hardly turns | the drive in robot.yaml | Wheels slip sideways in simulation. Raise `wheel_separation_multiplier` (ROSbot XL needed 3.0) and `max_wheel_torque` (ROSbot XL: 40), upload and `create_robot` again. |
| Odometry missing on the board | the link's `forward` | The board app subscribed to a topic the robot does not publish. Use the `forward` topic that `get_board_link`'s `interfaces` list as `nav_msgs/msg/Odometry`. |
| Everything is slow | `get_simulation_status`: `real_time_factor` | The simulator runs below real time (0.3 to 0.5 is normal for a warehouse with a camera). Time-based moves cover less ground: drive by odometry, not by duration. |
| `create_robot` fails with `profile_invalid` | the error's line and column | robot.yaml is not valid YAML there; a missing space after a `:` is the usual one. |
| `create_robot` fails on a file reference | the error lists the references | A mesh path points outside the bundle, at a package the bundle does not carry, or at a missing file. Add the package folder (with `package.xml`, or as `share/<package>/`). |
| `joint_not_found` / `link_not_found` | the error lists the robot's joints or links | A name in robot.yaml does not match the URDF. Use one from the list. |
| `simulator_not_running` | `get_simulation_status` | Start it with `control_simulation` `start` (a few minutes) when the user agrees: it costs GPU time. |
| A deleted ready-made scene came back | — | The simulator's setup rewrites its ready-made scenes on every run; save a copy under another name to change one. |
