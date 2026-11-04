# ROS Demo Ladder

Use these names consistently in plans, templates, evidence, and demo reports.
Each level proves the levels before it, but only when its own acceptance checks
pass.

| Level | Name | Template/result | What it proves |
|---|---|---|---|
| 0 | `READY` | Environment preflight | Studio, paired board, ROS domain, and required runtime are reachable and compatible. No user package is built. |
| 1 | `HELLO` | Minimal publisher/subscriber package | A user-defined ROS 2 package builds and exchanges a typed message locally. This is the standard hello-world template. |
| 2 | `LAUNCH` | Parameters plus launch file | The installed package is discoverable and multiple configured nodes start through `ros2 launch`. |
| 3 | `DEPLOY` | Host build, board deploy, detached run | Edgematic cross-builds the package, deploys it to Modalix, and the process remains active after SSH disconnect. |
| 4 | `VIEW` | Standard image/detection viewer contract | The board publishes live renderable topics, the bridge subscribes, and Edgematic's embedded Flora view renders them. |

## Template naming

Use technically descriptive package and artifact names rather than novelty
labels:

- package stem: `edgematic_ros_demo`
- launch files: `hello.launch.py`, `deploy.launch.py`, `view.launch.py`
- nodes: `hello_publisher`, `hello_subscriber`, and purpose-specific viewer nodes
- text topic: `/demo/hello`
- image topics: `/image_raw` and `/detections_overlay`
- structured results: `/detections`

The level name is an evidence label, not a ROS distribution version and not a
claim that later levels passed.

## Evidence card

Record one compact card per run:

```text
Level: READY | HELLO | LAUNCH | DEPLOY | VIEW
Package/revision:
Studio/platform/runtime versions:
Board/device alias:
ROS domain:
Observed result:
Checks and current rates:
Visible topics and bridge subscriptions:
Limitations/expiry:
```

Do not include credentials, raw logs, or private addresses in a reusable
template.
