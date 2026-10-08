---
name: edgematic-ros2-starter-prompts
description: Generate copy-ready starter prompts for Edgematic ROS 2 work when a user asks what to type, wants a prompt generated, or wants examples for a new contract-built package, an existing package, rosbag replay, or a visible end-to-end demo. Do not build, deploy, or run anything unless the user separately asks to execute the generated prompt.
---

# Edgematic ROS 2 starter prompts

For component selection, execution skills apply
[SiMa-first component selection](../edgematic-ros-capabilities/references/sima-first-selection.md).
When model choice matters, the prompt may say “Prefer compatible SiMa models and
capabilities; explain any custom additions.” Keep catalogue queries, versions,
benchmark instructions and selection evidence mechanics out of the user prompt.
Preserve an explicit USB camera or RTSP choice; do not force a default transport.

Generate the smallest prompt that can route the request to the right execution
skill. Keep platform mechanics in those skills instead of making the user name
containers, launch files, transport commands, or deployment layouts.

## Robot source boundary

For robot work, use the GitHub repository supplied in the prompt and record its
immutable revision. Derive model, geometry, sensors, driver packages, topics,
message types, launcher paths, calibration and limits from that source and
read-only inspection of the selected device. Do not import a remembered robot
profile or customer application as a default. Keep task-specific findings in the
project contracts and evidence, outside these shared skills. Resolve missing
source or required facts before the dependent action.


## Boundaries

- This is a prompt-only skill. Do not build, deploy, start streams, or change a
  device unless the user separately asks to execute the prompt.
- Choose one route: a new contract-built package, an existing user package,
  rosbag replay, or a clean recording-ready end-to-end demo.
- Ask for a missing project or device only when the execution skill cannot
  resolve it. Prefer placeholders in the generated prompt.

## Prompt contract

The recommended prompt states the desired outcome and acceptance result, not
the implementation recipe. When relevant it names:

- the project/repository and target device;
- real RTSP or rosbag input and whether replay should loop;
- native ARM64 or emulated AMD64 as a host constraint, never as the Modalix
  output architecture;
- raw camera, structured detections, rendered overlay, odometry, and TF;
- build, deploy, run, record, stop, and replay outcomes;
- that a topic is visible only after it is advertised **and emits messages**;
- retained logs, bag, manifest, hashes, screenshots, and explicit gaps.

Take exact visible topics from the selected application's declared contract and
verify their current publishers. Do not copy a robot's topic names into the
prompt by default. A real-scene input bag must not contain precomputed
detections. If odometry or TF comes from a fixture, label it replayed.

## Output

Return one recommended fenced prompt and a short placeholder list. Offer at
most two alternatives, and only when they route to materially different flows.
Do not paste shell commands or internal acceptance YAML into the starter prompt.

For a clean demo, the concise prompt should preserve this acceptance meaning:
install/provision if needed, build and deploy to Modalix, start the managed RTSP
input, run inference, record input and results to writable NVMe, show only active
raw/detection/overlay/odometry/TF outputs, stop and replay the bag, verify again
at start/30/60 seconds, then retain evidence ready for a screen recording.

Unless the user asks for different wording, return this recommended prompt:

```text
Run the standard ROS 2 end-to-end demo on my paired Modalix and show the verified live output. Use real managed RTSP input, record input and detections to NVMe, replay the bag, fix in-scope failures, and retain recording-ready evidence.
```
