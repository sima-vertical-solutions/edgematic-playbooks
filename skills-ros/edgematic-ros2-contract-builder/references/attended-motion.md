# Attended robot motion from a short prompt

Use this only when the user requests physical motion. The prompt supplies the
behavioral goal; derive interfaces and limits from the selected robot's source,
active application, and read-only board inspection. Keep robot-specific values
in project contracts and evidence, never in this shared skill.

## Establish the live motion contract

1. Pin the supplied vendor source revision and inspect the selected board's
   installed driver/firmware revision. Vendor documentation describes supported
   interfaces; the active ROS graph decides what this board actually exposes.
   Query the relevant ROS domains with hidden topics and services included
   (see the contract builder's "Device links, transports and interfaces").
   Inspect message types, publishers, subscribers, QoS, joint names/order,
   and fresh feedback. Do not choose a command topic from names alone.
2. Record base command and feedback interfaces, domain relay needs, wheel/odom
   conversion, physical limits, controller ownership, stop semantics, and
   unresolved facts in the project's robot and acceptance contracts. A topic
   being advertised does not prove that it emits data or controls the base.
   A camera stream and replayed odometry do not prove live motion readiness.
3. Reuse the intended driver where its revision and interface match; pin it
   only after its topic names, types and ordering match the live board. If the
   selected board differs from the vendor's current source, adapt to the
   observed interface and record that difference. Do not flash firmware,
   replace a driver, or infer motor transport from a URDF joint name.

## Implement one guarded command path

- **Single command owner.** Exactly one application node publishes to the base
  command interface. The operator TUI, behaviours, voice and perception send
  intents to that node; none of them publishes to the base directly. Check at
  arming time that the owner is the sole publisher. Avoid duplicate camera,
  relay, controller, and bridge processes when extending a running project.
- **Disarmed by default, preview first.** Start disarmed and publish zero
  motion. Until the operator enables it, publish computed commands to a preview
  topic instead of the real command interface, so the full path can be checked
  live without owning the base.
- **Operator-only arming.** Arming comes only from the operator TUI and requires
  a live TUI heartbeat, current base feedback, the wheels/base at rest and, for
  follow modes, current target data. Voice, behaviours, perception and agent
  tools may select an intent but can never arm. Keep output zero if any guard is
  missing. Bound linear/angular or wheel commands by evidenced limits with a
  ramp, and stop on stale intent, target loss, stop, exit, or disconnect.
- **Hold, then latch, on feedback gaps.** On a short feedback or heartbeat gap,
  command zero and hold; resume only if fresh data returns within the bound.
  Latch a stop only after a longer bound derived from the board's measured
  delivery jitter under the full application load (sample worst-case gaps
  across all running streams first). A bound tighter than observed jitter
  latches spuriously; one far looser leaves the base uncommanded too long.
  Record the measured jitter and chosen bounds in the motion contract.
- **Log every stop reason** (operator stop, guard name, measured value, bound)
  to the node log and the state topic the TUI shows.
- **Zero on shutdown.** Publish zero before the node exits on any signal or
  exception path, so a device that holds its last command cannot keep moving.
- Provide a visible stop/latch and disarm path. Reset may clear a latch only into
  disarmed state; it must not resume old follow intent. Make the TUI show mode,
  target/feedback freshness, requested command, measured odometry, and stop
  reason. Derive key bindings from the existing application or choose and
  document them in the new project; do not assume universal bindings.
- Keep the selected camera input and detector contract. Publish a renderable
  boxed overlay and structured detections. Prefer paced compressed topics for
  remote Flora panels while leaving full-resolution topics available on demand.
  Verify the browser subscribes to the live topics, not just that the bridge
  advertises them.

## Verify in increasing scope

1. Run isolated controller tests for arming, loss/reacquisition, stale feedback,
   hold-versus-latch bounds, stop/reset, stop-reason logging, zero on shutdown,
   bounded commands, singleton ownership, and TUI exit. Include a host test that
   launches the command node itself and checks it stays up and publishes zero;
   run it after every edit of that node, because unit tests of its functions do
   not catch a crash on startup. These tests must not send commands to physical
   hardware.
2. Deploy, launch, and sample live camera, detections, overlay, raw motor
   feedback, derived odometry, and controller state at startup and after 30 and
   60 seconds. Confirm one command owner and zero requested and measured motion
   while disarmed. Check the running payload's source/model identity so an older
   board install cannot mask the new build.
3. Open the operator TUI and live Flora view. Leave the robot disarmed for the
   user's attended test. When the user operates it, capture fresh command and
   wheel/odometry feedback plus visual confirmation of chassis behavior and
   stop response. If that test has not happened, report perception and disarmed
   readiness as verified, and physical following as pending. Do not convert a
   process log or command request into a claim that the robot moved correctly.

Repair in-scope failures and repeat the affected acceptance checks. If a
required motion fact stays unresolved, keep the command path disarmed and
report the exact evidence needed; continue the safe perception and UI work.
