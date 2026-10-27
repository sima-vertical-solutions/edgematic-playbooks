# robot.yaml — the robot profile

A robot profile says what no standard robot file says for a simulator. It is optional: a URDF
plus the robot's ros2_control `diff_drive_controller` config is enough for a wheeled robot
without cameras. Put it at the bundle's top folder as `robot.yaml`. Keys the simulator does not
use are ignored, so a profile written for more is fine. A profile that is not valid YAML is
refused with its line and column (`profile_invalid`).

## Fields

```yaml
name: turtlebot3                 # the robot's library name (letters, digits, _)
description:
  urdf: urdf/robot.urdf          # the entry, bundle-relative (or usd: path/to/robot.usda)
  articulation_root: body_link   # only when the importer's choice is wrong
  base_frame: base_link          # the odometry's child frame (default base_link)
drive:                           # omit when the bundle has a ros2_control diff_drive_controller
  type: differential             # or skid_steer (several wheels per side)
  left_wheel_joints: [wheel_left_joint]
  right_wheel_joints: [wheel_right_joint]
  wheel_radius: 0.033            # metres
  wheel_separation: 0.288        # metres, between the left and right wheels
  wheel_separation_multiplier: 1.0   # skid steer: raise until turns match the command (ROSbot XL: 3.0)
  max_wheel_torque: 40           # N m in Isaac; raise when a skid steer will not turn in place
  max_linear_speed: 1.0          # m/s
  max_angular_speed: 3.0         # rad/s
sensors:
  - id: front_camera
    type: camera
    asset: assets/camera.usd     # a camera USD in the bundle, with its own ROS 2 graphs
    parent: body_link            # the link it is mounted on
    xyz: [0.16, 0.0, 0.12]       # metres, in the link's frame
    rpy_deg: [0, 10, 0]          # degrees; positive pitch tilts it down
    outputs: [rgb]               # rgb (default); depth, depth_pcl cost a render pass each
channels:                        # topic names of the generated graphs (defaults shown)
  cmd_vel: { topic: /cmd_vel }
  odom: { topic: /odom }
  tf: { topic: /tf }
  joint_states: { topic: /joint_states }
```

Only `type: camera` with an `asset` is built; other sensor types are skipped with a warning.

## Drafting the drive from a URDF

| Field | Where it is in the URDF |
| --- | --- |
| wheel joints | `<joint type="continuous">` whose `<child link>` is a wheel |
| left / right | the sign of the joint's `<origin xyz="x y z">` `y`: positive is left |
| `wheel_radius` | the wheel link's `<collision>` `<cylinder radius="...">` |
| `wheel_separation` | left `y` minus right `y` of the two wheel joints |
| `type` | one wheel per side: `differential`; two or more: `skid_steer` |

Show the draft to the user before writing it.

## Example: TurtleBot3 Waffle Pi

From ROBOTIS' `turtlebot3_description` package (the `humble` branch of
`github.com/ROBOTIS-GIT/turtlebot3`). Its `turtlebot3_waffle_pi.urdf` has
`wheel_left_joint` at `y = 0.144`, `wheel_right_joint` at `y = -0.144`, and wheel cylinders of
radius `0.033`. Bundle: the `turtlebot3_description` folder (as `share/turtlebot3_description/`)
plus this profile:

```yaml
name: turtlebot3
description:
  urdf: share/turtlebot3_description/urdf/turtlebot3_waffle_pi.urdf
drive:
  type: differential
  left_wheel_joints: [wheel_left_joint]
  right_wheel_joints: [wheel_right_joint]
  wheel_radius: 0.033
  wheel_separation: 0.288
```

The result publishes `/odom`, `/tf` and `/joint_states` and drives from `/cmd_vel`. It has no
camera: the Waffle Pi's camera is a URDF link, not a camera asset.

## Example: ROSbot XL

A USD robot, a camera asset and a skid-steer drive tuned for Isaac:

```yaml
name: rosbot_xl
description:
  usd: usd/rosbot_xl_isaac/rosbot_xl_isaac.usda
  articulation_root: body_link
drive:
  type: skid_steer
  left_wheel_joints: [fl_wheel_joint, rl_wheel_joint]
  right_wheel_joints: [fr_wheel_joint, rr_wheel_joint]
  wheel_radius: 0.048
  wheel_separation: 0.248
  wheel_separation_multiplier: 3.0
  max_wheel_torque: 40
sensors:
  - id: front_camera
    type: camera
    asset: assets/MetOak_640_380.usd
    parent: body_link
    xyz: [0.16, 0.0, 0.12]
    rpy_deg: [0, 10, 0]
```
