---
name: edgematic-simulation
description: Use when the user wants to bring a robot into the Isaac Sim simulator, build or open a simulated scene, drive a simulated robot from a paired Modalix DevKit, or remove robots, scenes or bundles — "add this robot to the simulator", "import my URDF", "make a warehouse scene with the ROSbot", "load the scene and play", "what does the board get from the simulator", "delete that robot". Covers uploading a robot bundle, creating a ROS-ready robot (drafting a robot.yaml from the URDF when there is none), composing and loading scenes, the board link (which of the robot's topics reach the board, under the robot's own names), and removal. Do not use for a board app's own build, deploy or run (see edgematic-build-deploy-run), for board preparation (see edgematic-ros2-board-setup), or for Foxglove/Flora rendering (see edgematic-foxglove-viz).
---

# Edgematic Simulation

## Overview

Edgematic Studio drives a shared **Isaac Sim** simulator through its **sim-agent**. A board app
runs on a paired **Modalix DevKit** and talks to the simulated robot over the simulator's board
link (Zenoh): the robot's camera and odometry reach the board, and the board's velocity commands
reach the robot.

The whole flow is tool calls; nothing is done in the Isaac editor:

1. **Upload** the robot's files as a bundle: `upload_robot_bundle`.
2. **Create the robot** — a ROS-ready robot in the simulator's robot library: `create_robot`.
3. **Compose a scene** — a world, robots, walking people: `create_scene`.
4. **Load and play**: `load_scene`, then `control_simulation` with `play`.
5. **Check the board link**: `get_board_link` until `applied_state` is `applied`.
6. **Run the board app** (edgematic-build-deploy-run), reading the topic names from the board link.

`get_simulation_status` answers "is the simulator up, what is open, is the timeline playing" at
any point. Every tool that changes something asks the user to confirm, unless the user chose a
permission mode that approves for them — so state what a call will change before you make it.

**No simulation tools at all?** (`upload_robot_bundle`, `create_robot`, `get_simulation_status`
missing from your tools.) Studio hides the whole family while its simulation switch is off, and
the switch resets to off whenever Studio restarts. Tell the user: turn on **Settings → Robotics →
Simulation environment**, then start a new chat (the tool list is read when a chat starts). Do
not work around it with REST calls or a shell: there is no other way to upload a bundle.

**The rule that outranks everything else here: topic names come from the robot, never from
memory.** Robots name their topics as they like (Nova Carter's odometry is `/chassis/odom`,
ROSbot XL's `/odom`). Read them from `list_robots` (`interfaces`) or `get_board_link` before you
write a topic into a config, a launch file or a Flora layout. The one fixed name is the camera on
the board: the simulator compresses the robot's camera and the board always receives it as
`/camera/image_raw/compressed`.

## 1. What a bundle holds

A bundle is one or more folders of the user's project, packed and uploaded by
`upload_robot_bundle` (`folders` are project-relative). What it can carry:

| Part | Needed | Notes |
| --- | --- | --- |
| URDF or xacro + meshes | yes, or a USD robot | Meshes are `.stl .dae .obj` (+ `.mtl`, textures). A `.urdf` that uses xacro (`${...}`, `<xacro:...>`) is expanded like a `.xacro`. |
| The description package | when the URDF uses `package://` | Its `package.xml`, or the ROS install layout `share/<package>/...`. |
| A ready USD robot | optional | `.usd .usda .usdc`; checked by the simulator before use. |
| The robot's ros2_control config | optional | A `diff_drive_controller` block (`left_wheel_names`, `right_wheel_names`, `wheel_separation`, `wheel_radius`) gives the robot its drive with no robot.yaml. |
| `robot.yaml` | optional | What no standard file says: the drive when there is no ros2_control config, the articulation root, camera mounts, topic names. See [references/robot-yaml.md](references/robot-yaml.md). |

Files of any other type (READMEs, licences, scripts) are skipped and listed, never uploaded.
Read the upload's answer: `profiles` (robot.yaml files), `urdf_candidates`, `usd_candidates`,
`warnings`, `skipped`.

What works today: **wheeled robots** (differential or skid steer), **cameras given as a USD
asset** in the bundle. A lidar or IMU in robot.yaml is skipped with a warning. Arms, legged
robots and drones import with physics, but nothing drives them yet. Say so plainly when the user
brings one.

## 2. Create the robot

Call `create_robot` with the `bundle_id`. Pass `profile` (one of `profiles`) or `entry` (one of
the candidates) when the bundle has more than one; with one profile, it applies on its own.
A URDF entry needs the simulator running (Isaac converts it); a USD entry does not.

Read the result, then tell the user what they got:

- `drive` — `null` means the robot will not move from velocity commands. Offer to draft a
  robot.yaml (section 3).
- `sensors` — the mounted cameras. None means the board gets no camera from this robot.
- `interfaces` — every topic the robot publishes or subscribes to, with its message type.
- `warnings` — skipped sensors, no drive, and so on. Repeat them to the user.

A job that is still running comes back as `{job_id, state}`; follow it with
`get_simulation_job`.

## 3. No robot.yaml? Draft one from the URDF

Most robots need only the drive. Work it out from the URDF the bundle carries, then **show the
draft to the user and ask them to confirm it before you write it** — a wrong wheel spacing makes
the robot turn wrongly without any error:

1. The driven wheels: the `continuous` joints whose child link is a wheel (`wheel_left_joint`,
   `fl_wheel_joint`, ...). Left are those with positive `y` in their `<origin>`.
2. `wheel_radius`: the wheel link's collision `<cylinder radius=...>`.
3. `wheel_separation`: the distance between the left and right wheel joints' `y` origins.
4. `type`: `differential` for one wheel per side, `skid_steer` for several.

Write it as `robot.yaml` at the bundle's top folder, upload again, and call `create_robot` again.
The TurtleBot3 example and every field are in [references/robot-yaml.md](references/robot-yaml.md).

## 4. Compose a scene, load it, play

`create_scene` takes a `name`, a `world` and the robots to place:

- `world`: `{}` for a plain ground; `{"asset": "/Isaac/Environments/Simple_Warehouse/full_warehouse.usd"}`
  for NVIDIA's warehouse (any `.usd` path on Isaac's asset server); `{"scene": "<saved scene>"}`
  to build on a saved scene.
- `robots`: `[{"robot_id": ..., "spawn": {"x": 0, "y": 0, "z": 0.02, "yaw_deg": 0}}]`. Spawn a
  wheeled robot a little above the ground (`z` 0.02 to 0.1).
- `walkers` (optional): a person walking between waypoints, for detection apps — `character`
  `/Isaac/People/Characters/male_adult_construction_05_new/male_adult_construction_05_new.usd`,
  two or more `[x, y]` waypoints a few metres in front of the robot's camera.

An existing name is refused (`scene_exists`); ask before you pass `overwrite`. The scene is not
opened: call `load_scene` (it replaces whatever is open in Isaac; unsaved changes are lost), then
`control_simulation` with `play`. **A loaded scene is stopped until Play** — "no camera on the
board" right after a load is almost always this.

`list_scenes` shows each scene's robots. To keep editor changes, `save_scene`.

## 5. The board link

Loading a scene sets what the board gets from its robot (mode `auto`):

- **camera** — the robot's colour camera, compressed, published on the board as
  `/camera/image_raw/compressed`;
- **forward** — the robot's odometry, under its own name;
- **accept** — the robot's velocity topic: what the board publishes there drives the robot;
  the robot stops 0.5 s after the board goes quiet.

Call `get_board_link` and wait for `applied_state: applied` (a few seconds after a load).
`pending` that lasts longer than a minute, or `failed` with `applied.error`, is a simulator-host
problem to report, not something to retry blindly.

To send more (e.g. `/tf` or `/joint_states`) or another camera, `set_board_link` with
`mode: "manual"`. **Manual replaces the whole link**: read `get_board_link` first, then send
`camera`, `forward` and `accept` together, edited. `{"mode": "auto"}` (alone) goes back to
following the scene.

## 6. The board app

Hand the topic names to the board app from the link — never hard-code them:

- odometry: the `forward` topic that the link's `interfaces` list as `nav_msgs/msg/Odometry`
  (`forward` holds topic names only; the types are in `interfaces`). A ready-made scene lists no
  `interfaces`; its link forwards odometry only (Nova Carter's `/chassis/odom`);
- velocity: the `accept` topic;
- camera: `/camera/image_raw/compressed` (`sensor_msgs/msg/CompressedImage`, JPEG).

A board app can also find its topics by type (the demo apps do: odometry and velocity set to
`auto`). Building, deploying and running the app is edgematic-build-deploy-run's job; preparing
the board is edgematic-ros2-board-setup's.

### The board's side is always on — do not start it

A board set up for the simulator runs its half of the link and its Foxglove bridge as services
that start with the board. There is nothing to connect or launch:

- **Do not call `connect_simulation_input` or `start_hil_application`.** They run an older
  hardware-in-the-loop setup (scripts under `/media/hil/`) that these boards do not have; exit
  127 from either means exactly that, not a broken board. `start_hil_application` would also
  start a different demo app.
- **Ignore `tunnel` in `get_simulation_status`'s board part** — it looks for that older setup's
  SSH tunnel and reads `false` on a working link. What tells you the link works: `get_board_link`
  `applied_state: applied`, and the board part's `camera_hz` above zero (the camera arrived on
  the board).
- **The Foxglove bridge is running even when `ros2_node_list` does not list it.** Ask Studio's
  Foxglove status (`GET /devices/{id}/foxglove`), or `ros2_topic_list` while a viewer is
  connected; never conclude "no bridge" from the node list alone, and never start a second one.

### Is the robot moving?

Odometry is the answer, not the board app's log: read the odometry topic on the board twice, a
few seconds apart, while the app publishes velocity. If the board publishes on the `accept`
topic but the position does not change, the command reached the simulator and the robot did not
drive — a simulator-side problem with that robot (its drive, its wheels, its spawn height).
Report it with those two readings; do not redeploy or restart the board app, which is not the
cause.

## 7. Removing robots, scenes and bundles

All three are confirm-gated (unless the user's permission mode approves for them), and none can
be undone except a ready-made scene, which the simulator's setup puts back. Delete only when the
user asked, and state the consequence before you call the tool:

| Tool | Removes | Also |
| --- | --- | --- |
| `delete_robot` | One library robot. | Scenes that place it no longer load it; its bundle stays. |
| `delete_scene` | One saved scene. | Does not close it in Isaac if it is open. A ready-made scene the simulator's setup provides (`carter-warehouse`, ...) comes back on the next setup run. |
| `delete_bundle` | An uploaded bundle **and every robot made from it**. | Scenes that place those robots no longer load them. Name the robots that go with it (`list_robots`, `bundle_id`) before asking. |

`list_bundles` shows the uploaded bundles with their size and candidates.

## Troubleshooting

See [references/troubleshooting.md](references/troubleshooting.md): the robot does not move or
turns too slowly, no camera on the board, `applied_state` stuck, the simulation runs slowly, an
import fails on a file reference or a YAML line.
