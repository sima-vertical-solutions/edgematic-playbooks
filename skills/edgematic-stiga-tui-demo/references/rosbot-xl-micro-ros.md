# ROSBOT XL on Modalix: reuse the verified micro-ROS path

Use when the robot's MCU exposes `/_motors_response` and `/_motors_cmd`, or
when a mounted Modalix sees MCU traffic from `192.168.77.3` to agent
`192.168.77.2:8888`. These are observed legacy defaults, not universal board
addresses. Resolve the user's selected Modalix through pairing each time.

## Fast decision sequence

1. Verify the paired board's SSH host key and stable machine identity. Preserve
   the working webcam/inference process. Resolve physical Ethernet interfaces
   from current link state; a previously attached USB adapter may be gone.
2. Check MCU protocol and address ownership before changing the network.
   Observed micro-XRCE packets and named wheel feedback select the legacy
   micro-ROS path. Current upstream ROSBOT MAVLink hardware drivers are **not**
   compatible with this firmware; do not spend time rebuilding them or flash
   the MCU to fit a recently cloned branch.
3. Reuse a matching agent and operator bridge from the application source.
   Start with agent-only telemetry. Confirm real encoder, IMU and battery
   messages, not merely topic names. A TUI subscription creates a topic in the
   graph even with zero publishers.
4. Keep commands disabled for a bench/unspecified-motion request. Once the
   user has requested movement and resolved an earlier bench restriction,
   carry that authorization forward; do not ask for it again during routine
   build, deployment or reopening. Leave arming to the operator.
5. Reuse the source build, named payload and singleton TUI flow. Check fresh
   odometry, one base-command owner, and zero initial output before handoff.
   Do not send movement or arm keys as an automated rendering test.

## Direct Ethernet resolves a shared-LAN default-address collision

ROSBOT's external Ethernet cable and internal switch can put its MCU and
Modalix on the same office LAN. In the verified incident an unrelated host
already owned `192.168.77.2`; it was not the user's Modalix. Leave such a host
untouched. Isolating the external cable onto the laptop removed the collision.

For an overlapping laptop Wi-Fi subnet, a dedicated Ethernet connection can
use a host address with `/32` and a host route to the selected Modalix. The
verified example was laptop `192.168.135.2/32` with route
`192.168.135.3/32`, while Wi-Fi/VPN kept the internet default route. These
values are an example, not defaults to assign to another installation.

After isolation, repeat duplicate-address detection before assigning the
MCU's expected agent address to Modalix. Preserve the board management address
and add `192.168.77.2/24` on its Ethernet interface. Keep the original DHCP
profile available; the direct profile need not autoconnect on a shared LAN.
Removing a primary IPv4 alias can also remove its secondary addresses, so
verify the resulting addresses/routes after each profile change.

A board's transient hostname can change when DHCP disappears. A TUI launcher
must not reject the same paired board solely because its hostname changed;
use the verified machine identity and SSH host key. Reconnect the owned TUI
and Flora sessions after a cable/routing change and confirm the actual target.

## Known matching agent and telemetry contract

The Husarion ARM64 agent image verified for this legacy MCU is:

`husarion/micro-xrce-agent@sha256:2e2976d7f59165388c4a74a77f48ceddfef7c7a9fe25dbb601c00991e541fe11`

It supplies MicroXRCEAgent 2.4.1. Extract its binary and shared-library closure
on the host/SDK, keep those libraries private to the agent, verify `ldd` on the
board, and include them in the application's named deployment payload. Do not
replace the working ROS/Neat libraries or require a board-side image download.
Run `MicroXRCEAgent udp4 --port 8888` with
`XRCE_DOMAIN_ID_OVERRIDE=<application-domain>` and its private library path.
Setting `ROS_DOMAIN_ID` alone does not override the MCU participant's domain.
Use a separate owned process/service, not full robot bringup that resets the
MCU or starts controllers. Default agent DDS transport worked; an ad hoc
loopback-only FastDDS profile caused incomplete discovery during short probes.

| MCU topic | Type | Verified meaning |
| --- | --- | --- |
| `/_motors_response` | `sensor_msgs/msg/JointState` | Four named wheel encoders; observed about 33 Hz |
| `/_imu/data_raw` | `sensor_msgs/msg/Imu` | Raw onboard IMU; observed about 25 Hz |
| `/battery_state` | `sensor_msgs/msg/BatteryState` | Voltage; some optional fields are NaN |
| `/_motors_cmd` | `std_msgs/msg/Float32MultiArray` | Four wheel angular velocities in **RR, RL, FR, FL** order |

The underscore-prefixed topics are hidden from default ROS CLI listings; use
hidden-topic discovery or explicit subscriptions. The supplied URDF's generic
command-order field had a different order, so validate against the actual
firmware contract and observed named feedback before commanding motors.
The observed firmware emitted header.nanosec values greater than 1e9; use local
receipt time for freshness and valid ROS timestamps for derived odometry.
Static URDF transforms and synthetic joint states are not measured odometry.

Sources: [legacy firmware](https://github.com/husarion/rosbot_xl_firmware/tree/162b253d8372a8b3cd9f6edc0c5e877a4cdc787c),
[legacy hardware description](https://github.com/husarion/rosbot_xl_ros/blob/ea9894d286606dd96420eb1aa36ba6c681ba8d12/rosbot_xl_description/urdf/rosbot_xl_macro.urdf.xacro),
[agent packaging](https://github.com/husarion/micro-xrce-agent-docker).
The source's motor timeout is 3 seconds; this is not proof of the installed
firmware version or a measured physical stopping distance.

## Operator controls: small increments with continuous hold available

Reuse the Edgebot operator implementation at `342f8e828264775848c04f5fc8557a5dc2c017dd`:
[operator](https://github.com/sima-vertical-solutions/edgebot/blob/342f8e828264775848c04f5fc8557a5dc2c017dd/src/edgebot_bringup/scripts/rosbot_operator.py),
[base bridge](https://github.com/sima-vertical-solutions/edgebot/blob/342f8e828264775848c04f5fc8557a5dc2c017dd/src/edgebot_bringup/scripts/rosbot_base_bridge.py),
and [isolated ROS acceptance](https://github.com/sima-vertical-solutions/edgebot/blob/342f8e828264775848c04f5fc8557a5dc2c017dd/tests/test_base_ros_isolated.py).
Do not generate a new driver/TUI every session. The test requires
`ROS_DOMAIN_ID=193` and `ROSBOT_BRIDGE_SCRIPT` pointing to the built bridge;
never redirect that synthetic test into the live robot domain. The bridge
accepts `TwistStamped` on `/edgematic/manual/cmd_vel`, converts it to the legacy
motor array and publishes `/odometry/wheels` from real wheel velocity feedback.
The verified geometry is the supplied mecanum URDF: radius 0.05 m, wheelbase
0.170 m, track 0.270 m. Do not apply it to ordinary tires without adapting the
kinematics. This is a low-speed operator bridge, not the upstream MAVLink stack.

Default attended controls are `M` arm/disarm, `W/S` forward/reverse, `A/D` turn,
arrows equivalent, `Space/X` stop and disarm, `Q` exit. The TUI limits commands
to 0.05 m/s and 0.15 rad/s; each direction event renews a 0.25-second input lease.
A tap gives a small increment; holding/repeating permits continuous travel.
Do not force a new arming for every tap when the user requested continuous
movement. Optional `--jog` is an explicitly selected single 0.20-second pulse
per arming; key repeat cannot extend that pulse.

The separate bridge has a 0.30-second command/feedback deadline plus its
0.05-second timer interval, rejects stale timestamps and conflicting command
owners, ramps commands, and bypasses the ramp for zero/stop. Keep it running
independently of the remote PTY so lost keyboard input is stopped locally.
These software deadlines do not guarantee physical stopping distance or
protect against every board/MCU failure; preserve the firmware watchdog.

Verify policy tests and ROS wiring in an isolated ROS domain with synthetic
feedback. On real hardware, observe idle motor arrays, fresh encoder odometry,
TUI disarmed state and ongoing detection frames without injecting motion.
Give the user the installed launcher command after confirming it exists; do
not hand them a nonexistent wrapper or claim physical movement was tested.

Flora's existing camera bridge may have a video/TF-only whitelist. Add actual
odometry/telemetry topics through the supported bridge configuration when
requested; topic existence alone does not advertise them in Flora. Keep its
client-publish and service capabilities disabled for this viewing session.
