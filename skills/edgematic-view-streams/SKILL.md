---
name: edgematic-view-streams
description: Use AFTER EVERY deploy+run of a video pipeline — emitting the streams grid is a required closing step of the build/deploy/run flow, so invoke it unprompted once the run's output is verified stable. ALSO use when the user asks to see, show, display, open, or preview the live video streams in the Edgematic Studio chat, or to re-show them after a page reload or in a new chat. ALSO use when the user reports seeing FEWER streams than expected, a blank/frozen/stalled tile, or streams that stopped after they replied — the skill carries the triage ladder for the browser-side leg the stream count cannot see. It counts the active streams and emits the standard streams block so the UI renders a compact multi-stream grid as the last chat message (poppable into the workspace). Do not use for adding/removing videos or starting/stopping streams (that is edgematic-media-streams), nor for device deployment, model compilation, or canvas/web-ui work.
---

# Edgematic View Streams

## Overview

**Two entry points, one behaviour.** This skill runs either because the user
asked to see the streams, **or** as the mandatory closing step of a deploy: once
a video pipeline is running and its output has been verified stable
(`edgematic-build-deploy-run` owns that ladder), the user gets the grid without
having to ask for it. Never end a video deploy without emitting the block.

Show the currently-active live video streams inline in chat. insight serves up
to **80 output channels** (`0..79`); the device pushes one annotated output per
active pipeline stream. This skill determines how many are live and renders them
as a compact grid **as the last chat message**, so the user sees every active
stream at a glance and can pop the grid out into the workspace.

The grid is ALWAYS the multi-stream panel — **including when only one stream is
active**. One stream is a one-tile grid, with the same chrome and the same
pop-out; there is no separate single-stream presentation, and you should never
describe or offer one.

Because the grid is emitted as an ordinary assistant message, it **re-renders
automatically after a page reload** (the message is replayed from the
transcript). To show the streams in a **brand-new chat**, just invoke this skill
again — it re-emits the block.

**The grid is live only while it is the last message.** As soon as the user
sends anything, the tiles go idle. Say so when you emit it — see *Key rules*.

This skill only *displays* streams. To add videos or start/stop a stream, use
`edgematic-media-streams`. To diagnose a stream the user cannot see, read
`sima-use-neat-insight` — this skill's tools cannot tell you why a tile is
blank.

## Tools

| Tool | Purpose | Notes |
| --- | --- | --- |
| `count_streams` | Count the active **ingest** channels (device→insight) | Read-only. Returns `{ count, channels }`. Says NOTHING about whether a browser is rendering — see *Scope* below. |
| `list_output_streams` | Per-channel **egress** + per-peer browser decode/render stats | Read-only. The diagnostic surface: use it whenever the user sees fewer streams than `count_streams` reports. |

### Scope — what `count_streams` actually measures

`count_streams` is backed by insight `GET /api/ingest/stats`, which counts the
**device→insight** leg. The user is looking at the **insight→browser** leg. The
two are independent: a channel can ingest perfectly while its browser tile
renders nothing.

So `count_streams` returning 4 is **not** evidence that the user is wrong when
they say they see 1. Never use it to rebut a report about what is on screen.
When the two disagree, the user is describing the leg `count_streams` cannot
see — go to *Triage*.

## Workflow

1. **Call `count_streams`.** It returns `{ count, channels }` — one entry per
   active ingest channel, so no per-channel probing is needed for the *count*.
2. **If `count` is 0, branch on WHY you are here.**
   - **Right after a deploy/run** — this is almost always *not yet*, not *none*:
     an output channel exists only once the device has pushed its first annotated
     frame, which takes seconds to ~2 minutes. Poll `count_streams` every ~10 s
     for up to ~2 minutes. Only if it is still 0 report it as a **pipeline**
     problem, with `get_pipeline_status.log_tail` — and do **not** offer to start
     a stream: `start_stream` fills input slots (1–16) and cannot create an
     output channel (0–79).
   - **On a bare request** with no run in flight — tell the user there are no
     active streams and offer to start one (via the media/streams skill).

   Either way, do NOT emit an empty block.
3. **Otherwise, emit the standard streams block** as your reply (see below), and
   put it at the **END of your message**. The Studio UI parses it at render time
   and always renders the grid after your prose, so text written below the block
   will appear ABOVE it — write the block last so what the user reads matches
   what they see. Keep any surrounding prose short (e.g. "Here are your N live
   streams:") — the block itself is the payload. Emit the block for ANY count,
   one included.
4. **Tell the user the grid is last-message-only** and that replying will idle
   it. Offer the durable alternative when they need the streams to persist.

## Standard format — the `edgematic-streams` block

Emit a fenced block tagged `edgematic-streams` whose body is a JSON object. The
UI renders a compact grid (up to 4 rows) of tiny live tiles, one per channel,
with a "pop out" control that opens the streams in the workspace.

````
```edgematic-streams
{ "count": 12, "channels": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], "rows": 4 }
```
````

Fields:

- `channels` (preferred) — the exact list of active channel indices from
  `count_streams`. Pass it through verbatim.
- `count` — shorthand: the UI expands it to the contiguous roster `0..count-1`
  (insight channels are contiguous). Use only if you don't have `channels`.
- `rows` (optional, 1–4, default 4) — the maximum grid height.

Always prefer sending `channels` exactly as `count_streams` returned them. A
malformed or empty block renders as plain text, so only emit it when `count > 0`.

## Key rules

- **Every deploy of a video pipeline ends with this block.** When a run reaches
  a stable streaming state, emit the grid unprompted — the user should never have
  to type "show me the streams" to see what they just deployed. The stability
  ladder that precedes it belongs to `edgematic-build-deploy-run`; run it first
  and show only channels you have evidence are live. A grid emitted for channels
  you never verified is a guess dressed as a result.
- **A chat grid is live ONLY while it is the final message.** Earlier turns
  render idle tiles (deliberately — otherwise every scrolled-back block would
  reopen dozens of peer connections). The moment the user sends any message, the
  grid you just emitted tears down its peers and stops showing video. Always say
  this when you emit the block, e.g. "this grid goes idle once you reply — say
  'show streams' any time to bring it back, or open the durable viewer below."
- **For streams that must survive the next message**, offer the multi-channel
  viewer URL instead of (or alongside) the grid — insight's
  `GET /api/viewer-url?mode=light&src=0,1,2,3` returns a persistent multi-source
  view, and the `/streams` route holds its sessions independently of the chat.
  See `sima-use-neat-insight` for the endpoint contract.
- **`count_streams` counts ingest, not what the user sees.** See *Scope*. If the
  user reports fewer streams than it returns, believe the user and triage.
- **NEVER restart, rebuild, redeploy, or stop a pipeline to fix a viewing
  problem.** A blank tile is a browser/WebRTC symptom; restarting destroys a
  healthy run and fixes nothing. Confirm frames are being processed
  (`count_streams`, run status), then work the browser path in *Triage*. Do not
  offer a restart/redeploy pill on a display-layer complaint.
- **One `count_streams` call, not 80 probes.** insight's ingest stats already
  enumerate the active channels; the array length IS the count.
- **Emit the block only when there is at least one active stream** — but for
  ANY count from 1 upward, always as the same multi-stream block. Never
  special-case a single stream or describe it as anything but the grid.
- **Put the block LAST in your message.** The grid always renders after the
  prose, so a block written mid-message still appears at the end — text after it
  reads out of order. Emit exactly one block per message; if you emit more, only
  the last is used.
- **Pass `channels` through verbatim** from `count_streams` — don't invent or
  reorder indices.
- **The grid is the last message.** Don't bury it under a long explanation; a
  one-line lead-in is enough.

## Triage — the user sees fewer streams than `count_streams` reports

This is the common failure, and `count_streams` cannot diagnose it. Work down:

1. **Is it the last-message rule?** If the grid was emitted before the user's
   most recent message, it is *supposed* to be idle. Re-emit the block. This
   explains most "it worked, then it didn't" reports — check it first.
2. **Call `list_output_streams`.** Its `egress` payload carries per-channel and
   per-peer state. Read, in order:
   - `channels[].active` — the SENDER is publishing. Note that this is a TTL
     flag (`active_ttl_ms`, ~10 s): `active: true` only means insight sent
     something recently. It does **not** mean the browser is rendering.
   - `peers[].browser.video.active` — whether that peer's `<video>` element is
     actually presenting frames. **This is the field that matches what the user
     sees.**
   - `peers[].browser.video.last_frame_age_ms` — a large value on an `active`
     channel means the stream stalled after connecting.
   - `frames_per_second`, `freeze_count`, `pli_count` — decode health. Rising
     PLIs with freezes indicate packet loss / a corrupted RTP stream, not a
     configuration fault.
   - `metadata.dropped_no_data_channel` — detection metadata arriving with no
     data channel open to deliver it on.
3. **Count the peers per channel.** One peer per visible tile is expected. Far
   fewer peers than emitted channels means negotiation failed for those tiles —
   the offer to `/video/offer?channel=N` did not complete. Report that plainly
   rather than guessing at pipeline config.
4. **Anything deeper** — SSRC/payload-type history, competing senders on the
   same UDP port, ICE detail — is `sima-use-neat-insight`'s ladder. Read it
   rather than improvising. It documents `GET /api/ingest/stats?all=1&verbose=1`
   and the full egress-stats tree.

Report what the numbers say. If the evidence does not identify a cause, say so
and name the next probe — do not offer a destructive "fix" to fill the gap.

## Error handling

`count_streams` surfaces a typed error `{code, message}`.

| Error code | Meaning | What to tell the user |
| --- | --- | --- |
| `insight_unreachable` | The media/stream service didn't respond | The stream service is unavailable — check the Studio backend, then retry. |
| `not_implemented` | Stream tooling isn't wired in this environment | Streams can't be listed here; mention the environment lacks the media service. |

## Boundaries

- Display-only: no adding/removing videos, no starting/stopping streams (use
  `edgematic-media-streams`).
- **Display-only does not mean optional.** Verifying that a freshly deployed
  pipeline is producing stable output is `edgematic-build-deploy-run`'s ladder;
  rendering the result is this skill's job, and a video deploy is unfinished
  until both have happened.
- **When video misbehaves — blank tiles, freezes, stalls, a channel that reports
  active but shows nothing — read `sima-use-neat-insight`.** It owns the
  diagnostic ladder (ingest stats → egress stats → browser/ICE state); this
  skill's tools stop at the Studio boundary and cannot see the browser leg.
- Not for device deployment, model compilation, canvas/graph editing, or web-ui
  work.

## References

- `references/view-streams.md` — the `count_streams` contract and the
  `edgematic-streams` block schema in detail.
- `sima-use-neat-insight` — WebRTC egress/browser statistics and the full
  video-troubleshooting ladder.
