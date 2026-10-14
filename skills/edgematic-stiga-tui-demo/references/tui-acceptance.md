# Remote TUI rendering and acceptance

Source: Stiga PR #55, reviewed at
`5525b80b3ff57b82ed12f5cf5bba1440fa88cda3`.

## Rendering lessons

Build each frame in memory and write/flush it once to the remote PTY. Enter
the alternate screen, hide the cursor, and restore both in a `finally` block.
Do not append a newline after a full-height frame: it scrolls the terminal and
accumulates duplicate headers at every refresh. Home the cursor before drawing
and erase below the final row to clear stale content after a resize. Fit rows
to terminal width using visible lengths rather than ANSI byte lengths.

Keep ROS/teleop imports lazy if menu rendering itself is intended to work with
only Python's standard library. A menu that renders without ROS must still
disable/report unavailable hardware actions. Use the robot's actual command
message type and stop semantics when implementing attended teleoperation.

## Verify without motion

| Check | Evidence |
| --- | --- |
| Correct target | Resolve current paired device and launcher, not a remembered IP. |
| Single session | Reopening focuses the existing panel or explicitly attaches. |
| Render | Full frame appears without repeated headers or scrollback growth. |
| Resize | Shrink and enlarge the PTY; no residual lines, crash or corrupt frame. |
| Coexistence | Ordinary local shell remains usable next to the robot PTY. |
| Lifecycle | Close/reopen produces a usable session and restores terminal state. |
| Ownership | Own children stop on exit; attached robot stack survives. |

Never send movement/mode keys during unattended checks. Stiga's `e`, `b`, `m`,
`t`, `D` and teleop entry are not rendering tests. Inspect the actual TUI's
bindings rather than assuming all robots share them. Do not use quit to stop
an attached moving robot; the operator must use its supported idle/stop path.

Keep menu, live-camera inference, encoders/odometry and actual movement as
separate acceptance claims. A TUI screenshot alone proves only the first.
