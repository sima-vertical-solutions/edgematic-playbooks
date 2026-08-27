---
name: edgematic-media-streams
description: Use when the user asks to manage the Edgematic Studio video media library or control streams from chat — listing videos, adding a video (a curated catalogue clip by name, or uploading a local file from the user's computer), removing a video, starting or stopping an RTSP/WebRTC stream, or listing the running input streams or the output streams. Covers opening a file picker in chat for local uploads, picking a free stream slot automatically, returning every playback address (RTSP + WebRTC, and UDP host/port for outputs), collecting missing fields inline, and reporting media/stream errors clearly. Do not use for device pairing/deployment, Neat Library C++/Python application development, model compilation, canvas/graph editing, or web-ui React work.
---

# Edgematic Media & Streams

## Overview

Manage the video media library and control the RTSP/WebRTC streams that feed a
running pipeline — all from chat. You do this through the agent's media and
stream tools, which call the Edgematic Studio backend in-process (the backend in
turn drives the neat-insight media/stream service). The user speaks in natural
language ("what videos do I have?", "add the detection sample", "stream
people.mp4", "stop all streams"); you translate that into the right tool call,
collecting any missing information first and reporting playback addresses and
outcomes clearly.

The media library has two kinds of entries: **curated default clips** (vendor
`sima`, added by name) and the **user's own added videos** (vendor `user`). A
single Studio instance is one user's — there is no cross-user sharing to reason
about.

## Tools

| Tool | Purpose | Notes |
| --- | --- | --- |
| `list_videos` | List the media library (curated + user videos) with status | Read-only. Optional `vendor` (`sima`/`user`) or `status` filter. |
| `add_video` (with `name`) | Add a **curated catalogue clip** by `name` | Downloads a known SiMa sample by name. |
| `add_video` (NO arguments) | Upload a **local file** from the user's computer | Call `add_video` with no arguments → the chat opens a file picker and the browser uploads directly. Use whenever the user wants to add their own video (not a curated clip). |
| `remove_video` | Remove a video from the library by `name` | Requires confirmation. |
| `start_stream` | Start an RTSP/WebRTC stream for a video | `video` (library name or `rtsp://` URL); optional `index` pins the slot, else the lowest free slot is used. Returns the slot + RTSP + WebRTC addresses. |
| `stop_stream` | Stop a running stream | `index` stops one slot; `all: true` stops every slot. Requires confirmation. |
| `list_input_streams` | List running input streams (playing slots) with RTSP + WebRTC | Read-only. Slots are **1-based** (1–16). |
| `list_output_streams` | Output addresses **plus live per-peer egress and browser decode/render statistics** | Read-only. Output channels are **0-based** (0–79). The tool to reach for when a stream is running but the user can't see it. |

Full request/response and error detail: `references/media-streams-api.md`.

**Input slots and output channels share the `?channel=N` viewer endpoint but use
different bases** (slots 1-based, output channels 0-based). Never assume an
output channel maps to the slot of the same number — see the reference.

## Workflow

1. **Understand the intent** — list/add/remove a video, or start/stop/list streams.
2. **Pick the right add path.** A curated SiMa sample → `add_video {name}`. The
   user's OWN file from their computer → `add_video` with **no arguments** (this
   opens a file picker in chat and the browser uploads directly). If unsure which
   they mean, ask. Never ask the user to paste a URL or a file path.
3. **Gather missing fields with `ask_user` before acting.** For `add_video`, you
   need the catalogue `name`. For `start_stream`, you need a `video`. For
   `remove_video`, you need the `name`. Do not guess a video name.
4. **Resolve videos by name.** Videos are referenced by their library name
   (e.g. `people.mp4`). If the user is vague ("stream that detection clip"), call
   `list_videos` first and confirm which entry they mean.
5. **Let the slot be auto-picked.** `start_stream` chooses the lowest free slot
   automatically. Only pass an explicit `index` (1–16) if the user asks for a
   specific slot. If all 16 slots are in use, tell the user and offer to stop one.
6. **Don't add your own confirmation.** `remove_video` and `stop_stream` are
   gated by the runtime approval policy, which decides from the user's posture
   whether to prompt — so never ask "shall I?" on top of it. What you MUST do is
   be certain of the TARGET: resolve a vague reference with `list_videos` first.
   Confirming identity is ambiguity work; asking for permission is not.
7. **Report the result** clearly:
   - Video lists as a short table (name, vendor, status).
   - `start_stream` → the chosen slot and BOTH addresses (RTSP and WebRTC), so
     the user can open the stream in any viewer.
   - `list_output_streams` → the UDP host/port and WebRTC base.
   - remove/stop as a one-line confirmation.

## Adding a video

Two ways, and you pick based on WHERE the video comes from:

1. **Curated catalogue clip — `add_video {name}`.** Downloads a known SiMa sample
   into the library. Use this when the user names a curated sample ("add the
   detection sample", "add people.mp4"). If unsure which catalogue names exist,
   call `list_videos` (curated clips appear with vendor `sima`, often status
   `remote` until downloaded).
2. **The user's own local file — `add_video` with NO arguments.** Calling
   `add_video` with an empty argument object opens a **file picker in the chat**;
   the user selects a file and the browser uploads it directly into the library
   (you do NOT receive the bytes). After you call it, tell the user to pick their
   file and end your turn — they will message you when the upload is done (their
   message names the file); then confirm it's added and, if it fits, offer to
   stream it. Use this for ANY "add my video / upload from my computer" request.

Do NOT ask the user to paste a URL or a filesystem path — there is no URL-based
add. Local files always go through no-argument `add_video`.

## Streaming addresses

When a stream is running, it is reachable at several addresses derived from the
Studio server's IP and the slot index `N`:

- **RTSP:** `rtsp://<server-ip>:8554/src<N>`
- **WebRTC:** `https://<server-ip>:8081/offer?channel=<N>`
- **Output UDP:** `udp://<server-ip>:9000+<channel>` (see `list_output_streams`)

Always report the addresses returned by the tool verbatim — the server derives
the correct host IP (never `localhost`). Give the user both the RTSP and WebRTC
addresses for an input stream so they can pick whichever their viewer supports.

## Key rules

- **Slots are 1–16 and auto-assigned.** Don't ask the user for a slot number
  unless they want a specific one; `start_stream` picks the lowest free slot.
- **`add_video` is for curated clips by `name` only.** For the user's own file,
  use no-argument `add_video` (chat file picker). There is no URL/path add.
- **After starting a stream that feeds a RUNNING pipeline, verify and show the
  output.** An input slot playing is not the same as the pipeline emitting an
  annotated output channel. Confirm the output came up and holds
  (`count_streams` twice across **10 s**, non-shrinking — the ladder in
  `edgematic-build-deploy-run`), then emit the grid via `edgematic-view-streams`.
  Remember the namespaces differ: slot `N` in does NOT imply channel `N` out.
- **Report every address the tool returns.** A stream isn't useful without its
  playback URL — surface RTSP + WebRTC (and UDP host/port for outputs).
- **Be sure of the TARGET before removing a video or stopping a stream — but
  don't ask for permission.** Both are gated by the runtime, which prompts (or
  doesn't) according to the user's approval posture; a second question from you
  only stalls the run. A wrong target, however, is unrecoverable, so resolve a
  vague reference with `list_videos` / `list_input_streams` first.

## Error handling

Every tool surfaces a typed error `{code, message}`. Relay it clearly and, where
useful, suggest the next step.

| Error code | Meaning | What to tell the user |
| --- | --- | --- |
| `insight_unreachable` | The media/stream service didn't respond | The media service is unavailable — check the Studio backend, then retry. |
| `insight_operation_failed` | The service rejected the operation (e.g. all slots busy, bad file) | Relay the message; for "all slots in use", offer to stop a stream first. |
| `upstream_unavailable` | The curated catalogue source is unreachable | Only affects `add_video {name}` (curated clip). Listing is unaffected (curated clips just won't appear until it recovers); suggest uploading a local file via no-argument `add_video` instead. |
| `invalid_tool_params` | Missing/invalid arguments (e.g. no `name`, no `video`) | Ask for the missing field (a video name or a slot). |

Note: `list_videos` no longer fails when the curated catalogue is unreachable —
it returns the user's own videos and silently omits the `sima` clips. If the
user expected curated clips and none appear, mention the catalogue may be
temporarily unavailable.

## Boundaries

- Local files are uploaded via the no-argument `add_video` chat file picker (the
  browser uploads directly) — there is no URL/path add and no server-side fetch.
- This skill controls media and streams, not device pairing/deployment (see the
  device skill) and not application/pipeline development.
- Act on one video/stream at a time (except the explicit `stop_stream all`).
- **When video misbehaves — a stream is running but the user sees nothing, a
  tile is blank/frozen/stalled — read `sima-use-neat-insight`.** It owns the
  diagnostic ladder (ingest stats → egress stats → browser/ICE state). Do NOT
  stop/restart a stream or a pipeline to "fix" a viewing problem: that destroys
  working state and does not address the browser leg. Showing streams in chat is
  `edgematic-view-streams`.

## References

- `references/media-streams-api.md` — tools + underlying backend/insight
  contract, request/response shapes, address derivation, the egress/browser
  statistics shape, the input/output channel-namespace collision, and error
  codes.
- `sima-use-neat-insight` — WebRTC egress/browser statistics and the full
  video-troubleshooting ladder.
