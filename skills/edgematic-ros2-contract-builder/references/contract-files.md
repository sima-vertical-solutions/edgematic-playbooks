# Contract file requirements

The four files divide facts by ownership so the agent can generate code without
silently inventing a hardware contract. YAML keys may be extended, but the
meaning of the required fields stays stable. The agent derives missing files
from the user-supplied repository, expanded model and read-only target evidence.
No robot model has a bundled profile or a privileged source of defaults.

Studio normally uploads the files as `robot.urdf`, `robot_contract.yaml`,
`build_target.yaml`, and `acceptance.yaml` at the project root. The equivalent
`input/<name>` layout is also valid. These are the same four logical inputs,
not two sets of files.

## `input/robot.urdf`

Supply a fully expanded XML robot. It is authoritative for names and topology:
links, joints, parents, children, origins, transmissions, Gazebo sensor elements,
and `ros2_control` declarations that are actually present. It is not authoritative
for a device protocol, Linux device path, calibration, controller limits, topic
names, or safety policy unless those facts are explicit attributes in the file.

## `input/robot_contract.yaml`

Required logical fields:

```yaml
schema_version: 1
robot:
  name: null  # resolve from the supplied source
  vendor: null  # resolve from the supplied source
evidence_policy:
  forbidden_implementations: []
  allowed_vendor_sources: []
interfaces:
  sensors: []
  base:
    model: unresolved
    driver: unresolved
unresolved: []
```

Each sensor entry should identify its kind, frame, desired ROS message/type, and
whether the demo uses `live`, `rosbag`, or `file` input. Source URLs should be
official and may be resolved by the agent, but generated evidence must record an
immutable revision. Put unknowns in `unresolved`; never encode a guess as a fact.
Official source facts are `vendor_supported`, not user-proven, and conflicting explicit
input must be surfaced rather than silently replaced.

## `input/build_target.yaml`

Required logical fields:

```yaml
schema_version: 1
target:
  ros_distro: null
  architecture: null
  sdk: null
  board_class: null
  middleware: null
build:
  container: null
  workspace: null
```

Use versions observed from the selected SDK and paired board when the file leaves
them unresolved, and record observation provenance. An unobserved mutable value
is `null` plus an unresolved reason, never a version copied from an
old demo, or a previous board. Do not silently cross-build against a different
target.

## `input/acceptance.yaml`

Required logical fields:

```yaml
schema_version: 1
scope:
  input_mode: rosbag
  physical_motion_required: false
required_nodes: []
required_topics: []
flora:
  required: true
  topics: []
tui:
  required: true
  read_only: true
  required_sections: [nodes, topics, logs]
runtime:
  minimum_stable_seconds: 60
```

Every required topic entry needs a name, exact ROS type, and either a minimum
rate or an event/count condition. If `physical_motion_required` is false,
`cmd_vel`, actuator command interfaces, teleoperation, and motion keys are out of
scope and must not be generated.

Two supported no-motion input modes are:

- `rosbag`: recorded ROS messages, with explicit finite or looping behavior;
- `live` with `transport: managed_rtsp`: an Edgematic-managed camera stream,
  whose returned URL and measured geometry are runtime observations.

Do not treat managed RTSP as `file`, and do not claim that an RTSP frame proves
the physical camera driver. Acceptance must require the exact active raw input,
structured detections, rendered overlay, TF, Flora subscriptions, and a
read-only TUI. Rosbag-only odometry and joint-state checks do not carry over to
the camera-only managed RTSP mode.

## Evidence classification

- `proven`: explicit in an uploaded file.
- `vendor_supported`: explicit in official vendor documentation or source at a
  recorded immutable revision.
- `observed`: read from the selected SDK or paired board without changing it.
- `assumed_for_demo`: safe, reversible fixture behavior that acceptance permits.
- `unresolved`: cannot be established from allowed evidence.

Only `proven`, `vendor_supported`, and `observed` facts may justify a live driver.
An `assumed_for_demo` fact may justify a replay/fixture node but must appear in
the README and handoff. An unresolved physical-motion fact blocks motion even
when the rest of a no-motion demo can proceed.
