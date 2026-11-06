# Running a project's perception on a ROS bag's camera

`run_ros_pipeline` with `input: "bag"` plays a ROS bag from the project on the
board and feeds its camera to the project's own deployed perception, instead of
an RTSP stream.

```
run_ros_pipeline { device, input: "bag", project_id, bag_path,
                   camera_topic?, loop?, rate?, package? }
```

- `bag_path` is project-relative, spelled exactly as the bag list shows it.
- `rtsp_url` and the geometry fields (`source_width`, `source_height`, `fps`) are
  refused with `input: "bag"`: size and rate come from the bag.

## Which perception runs

The project's own, as deployed. The project's ROS workspace declares it in its
`deploy.yaml`:

```yaml
runtime:
  perception_launch: <package> <launch file>
```

- `package` picks another package of the same deployment instead. It is launched
  with `<package>.launch.py`.
- With nothing requested and nothing declared, the call is refused
  (`invalid_ros_bag_playback`) and the reason says which of the two to add. Ask
  the user which perception to run; do not guess a package.
- The project must already be deployed to the device under its `remote_dir`
  (deploy it first, see `edgematic-ros2-user-package`). A project that is not a
  ROS workspace, or names an unusable `remote_dir`, is refused with
  `ros_workspace_invalid`. A deployment or package missing on the device is
  refused before any running pipeline is touched.

The bag's camera reaches the launch as four launch arguments: `camera_topic`,
`source_width`, `source_height` and `fps`. A perception package run this way
must accept them.

## Choosing the camera

- Studio picks the bag's only camera. A raw `Image` topic stands in for its
  `/compressed` twin.
- Several cameras and no `camera_topic` is a refusal that lists them. Ask the user
  which one, then call again with `camera_topic`.

## Refusals before anything launches

The bag camera is checked before the device is touched. Any frame size is
accepted: it is handed to the perception as its source size. These are refused
with `ros_bag_camera_unusable`:

- no camera in the bag, or a `camera_topic` that is not one of its cameras;
- an unsupported encoding (only `bgr8`/`rgb8` raw, or colour JPEG/PNG compressed);
- fewer than two frames.

Relay the reason to the user plainly; do not retry with other parameters.

## What runs

1. The perception is launched first, from the deployment's `remote_dir`,
   replacing an earlier run of the same package, so it is subscribed before
   frames arrive.
2. Then the bag plays. A compressed camera is decoded on the board beside the
   playback: `image_transport` republish when the `compressed_image_transport`
   plugin is installed, otherwise Studio's own decoder (needs `rclpy`, `cv2`
   and `numpy` in the board's ROS Python). The playback's `camera.decoder.kind`
   says which one ran. A board with neither fails the start with that reason.

Poll with `get_ros_bag_playback`, stop with `stop_ros_bag_playback`. Stopping,
the bag ending, or a failed start also stops the perception that playback
launched, because an idle pipeline still holds the board's accelerator.

## Output

Whatever the project's perception publishes: its detections and, when it draws
one, its overlay. View them in Flora as usual. The camera's raw frames are on the
camera's `input_topic` (returned in the reply's `camera`).
