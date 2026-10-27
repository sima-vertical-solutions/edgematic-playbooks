# Simulation troubleshooting

## The ladder: when a simulated run does not work, for any robot

Go down in order and stop at the first rung that is wrong — each one depends on the ones above.
Every rung is a tool call; none needs a shell.

1. **The simulator** — `get_simulation_status`, `sim_agent` part: known (not `{"unknown": …}` —
   that is Settings → Robotics or the WireGuard tunnel), a scene open, timeline `playing`,
   `real_time_factor` (below 1 everything moves slower).
2. **The link** — `get_board_link`: `applied_state: applied`; `link.camera` not `null`; the
   `forward` and `accept` topics are the ones `interfaces` lists for this robot.
3. **The board** — `get_simulation_status`, `board` part: `zenoh_bridge: true`, `camera_hz` above
   zero, then `odometry.moving` while the app commands the robot.
4. **The robot** — `list_robots`: `drive` (not `null`, sensible `wheel_radius` and
   `wheel_separation`), `sensors`, `warnings`.
5. **Only then the app** — the topics it subscribes and publishes against the link's names, and
   that it keeps the board's ROS domain.

Report the rung that failed and the values that show it; suggest the fix that row gives below.

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
| No simulation tools in the tool list | — | Studio's simulation switch is off (it resets on every restart). Settings → Robotics → Simulation environment, then a new chat. |
| The board sends velocity, the robot stays put | `get_simulation_status` → `board.odometry` (`moving: false`) | The command arrives; the simulated robot does not drive. Check its `drive` (`list_robots`); report it as a simulator problem with that robot, with both readings. A scene with a robot whose drive is known to work tells the robot apart from the rest of the chain. |
| The robot turns the wrong way, or arcs when told to go straight | the drive in `list_robots` | Left and right wheels swapped (left wheels have positive `y` in the URDF) or a wrong `wheel_separation`. Fix the robot.yaml, upload, `create_robot` again. |
| `camera_hz` none with the link applied and the timeline playing | `get_board_link` `link.camera`; the app's environment | `link.camera` is `null` (no camera on the robot), or a board app set its own `ROS_DOMAIN_ID` / DDS config and no longer hears the board's topics. |
| `board.odometry` unknown | `get_board_link` `forward` | The link is not applied, or forwards no odometry: read `interfaces` for the robot's `nav_msgs/msg/Odometry` topic. |
| `board.zenoh_bridge: false` | — | The board's half of the link is down: a provisioning job for whoever set the board up, not something to start from chat. |
| The simulator view in Studio is black or will not connect | — | Isaac's viewer takes one viewer at a time. Close the simulator view in any other tab or window, then reload the Simulation panel. |
| "No `foxglove_bridge`" from `ros2_node_list` | `get_simulation_status` → `board.foxglove_bridge` | The bridge is a board service and is often missing from the node list. Trust `foxglove_bridge`, not the list. |
| `ros2_topic_list` comes back empty on a simulator board | the `domain` you passed | The board runs on the simulator's domain (77). Omit `domain` or pass `77`; `0` lists nothing. |
