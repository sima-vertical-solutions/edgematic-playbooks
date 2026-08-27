# Media & Streams API reference

The agent media/stream tools call the Edgematic Studio backend in-process (never
over HTTP). The backend in turn talks to the neat-insight media/stream service.
This reference documents the underlying contract so you know exactly what each
tool does, what it needs, and how it can fail.

## Media model

A video listing entry (`DefaultVideo`) carries: `id` (`<vendor>/<name>`, e.g.
`sima/sample_detection.mp4`), `name` (filename in the library), `vendor`
(`sima` for curated defaults, `user` for added videos), `status`
(`remote` = catalogue clip not yet downloaded, `downloading`, `downloaded`,
`failed`), and optional `description`, `size_bytes`, `last_error`.

Curated `sima` clips are known catalogue entries that may be `remote` until
`add_video` downloads them. `user` videos are physically present, so they list as
`downloaded`.

## Stream model

The insight service exposes up to **16 input slots** (`mediasrc`), each with an
`index` (**1–16**, 1-based), a `file` (the assigned video), and a `state` (a slot
is considered running when `state == "playing"`). Pipeline **output** channels
are a separate, **0-based** namespace (`0–79`) that shares the same
`?channel=N` viewer endpoint — see *Channel namespaces* below before quoting any
WebRTC address. Playback addresses are derived from the Studio server IP (fetched
from the service, never `localhost`):

- **RTSP:** `rtsp://<server-ip>:8554/src<index>`
- **WebRTC:** `https://<server-ip>:8081/offer?channel=<index>`
- **Output UDP base:** `udp://<server-ip>:9000` (per-channel offset applied by
  the pipeline; `list_output_streams` returns the base + live egress stats)

## Tools → backend

### `list_videos`
- Backing: the videos domain listing (curated catalogue source merged with the
  media library), same data as `GET /videos`.
- Params: optional `vendor` (`sima`|`user`), optional `status`
  (`remote`|`downloading`|`downloaded`|`failed`). Read-only.
- Returns: `{ videos: [DefaultVideo] }` (filtered client-side by the tool).
- Resilience: a configured-but-unreachable curated catalogue does NOT fail the
  list — it degrades to the `user` videos only (the `sima` clips are omitted
  until it recovers). Only the Media Library being unreachable is fatal
  (`insight_unreachable`).

### `add_video`
- Params: optional `name`. Two modes keyed off `name`:
  - **With `name`** → the curated catalogue clip is resolved in the manifest,
    fetched, and uploaded into the library. Returns
    `{ added: <name>, source: "catalogue" }`. Errors: `video_not_found` (name
    not in the catalogue), `upstream_unavailable` (catalogue unreachable),
    `insight_unreachable` (Media Library upload failed).
  - **With NO arguments** → a request to upload a LOCAL file. The dispatcher does
    NO server work and returns `{ status: "awaiting_upload" }`. The chat frontend
    detects the `add_video` tool call with no `name` (off the `tool_call` frame,
    which BOTH provider paths emit) and renders a file-upload widget; the browser
    uploads directly to `POST /video/upload/media` (the backend never receives
    the bytes through this tool). After the upload the frontend sends a new
    `user_message` naming the file — there is no clarification pause, so this
    works on both the in-process (anthropic) and subscription (claude-code) paths.
- Because it is a normal EXPOSED tool (not a meta tool), the claude-code CLI can
  call it over MCP — which is why the no-arg upload works there too.

### `remove_video`
- Params: `name` (required). Requires confirmation (destructive).
- Backing: media delete (`POST {insight}/api/delete-media`).
- Returns: `{ removed: <name> }`.
- Errors: `invalid_tool_params` (no `name`), `video_not_found` (name not in the
  Media Library — the backend checks membership before proxying the delete),
  `insight_unreachable`, `insight_operation_failed`.

### `start_stream`
- Params: `video` (required — a library name or an `rtsp://` URL); optional
  `index` (1–16). When `index` is omitted the tool assigns the **lowest free
  slot** (the lowest index not currently `playing`).
- Sequence: list slots → pick slot → assign the video → start → read server IP.
- Returns: `{ index, video, rtsp, webrtc }` with the fully-formed addresses.
- Errors: `video_not_found` (a non-`rtsp://` `video` not in the Media Library —
  checked before proxying; `rtsp://` passthrough URLs skip this check),
  `insight_operation_failed` (all 16 slots in use, or the service rejected
  assign/start), `insight_unreachable`.

### `stop_stream`
- Params: `index` (stop one slot) OR `all: true` (stop every slot). Requires
  confirmation (destructive).
- Returns: `{ stopped: <index> }` or `{ stopped: "all" }`.
- Errors: `invalid_tool_params` (neither `index` nor `all`),
  `insight_unreachable`, `insight_operation_failed`.

### `list_input_streams`
- Params: none. Read-only.
- Returns: `{ streams: [ { index, file, rtsp, webrtc } ] }` — only the slots that
  are currently `playing`.
- Errors: `insight_unreachable`.

### `list_output_streams`
- Params: none. Read-only.
- Returns: `{ server_ip, udp_base, webrtc_base, egress }` where `udp_base` is
  `udp://<server-ip>:9000`, `webrtc_base` is `https://<server-ip>:8081/offer`,
  and `egress` is the live egress-stats object from the service.
- Errors: `insight_unreachable`.

**This is the richest diagnostic surface in the toolset**, not just an address
lookup. `egress` is insight `GET /api/egress/stats` passed through verbatim (the
Studio backend does not model it — see `videos/stream_client.rs`), so the shape
below is **observed, upstream-owned, and may drift**; treat
`sima-use-neat-insight` as the authority and tolerate missing fields.

Roughly:

```jsonc
{
  "active_ttl_ms": 10000,          // how long after a send a channel stays `active`
  "channels": [
    { "channel": 0, "active": true, /* per-channel send rates */ }
  ],
  "peers": [
    {
      "id": 33,
      "channel": 0,                // NOTE: not always present on every peer
      "browser": {
        "video": {
          "active": false,             // is the <video> element PRESENTING frames
          "last_frame_age_ms": 122000, // large on an `active` channel = stalled
          "frames_per_second": 0,
          "freeze_count": 202,
          "pli_count": 562           // rising PLIs + freezes = loss / corrupt RTP
        }
      },
      "metadata": { "dropped_no_data_channel": 421 }
    }
  ]
}
```

Reading it:

- `channels[].active` tracks the **sender**, on a TTL (`active_ttl_ms`). It says
  insight sent something recently — **not** that anyone is watching or decoding.
- `peers[].browser.video.active` is the field that matches **what the user sees**.
  A channel can be `active: true` while every peer on it renders nothing.
- One visible tile ↔ one peer. Materially fewer peers than expected channels
  means those tiles never completed negotiation.

## Channel namespaces — inputs and outputs COLLIDE

Both are addressed as `?channel=N` on port 8081, and they are offset by one:

| | Range | Base | Addressed as |
| --- | --- | --- | --- |
| **Input slots** (`mediasrc`, the playing videos) | 1–16 | **1-based** | `https://<ip>:8081/offer?channel=<slot>` |
| **Output channels** (annotated pipeline results) | 0–79 | **0-based** | `https://<ip>:8081/offer?channel=<channel>` |

So `?channel=1` is input slot 1 **and** output channel 1 — different streams on
the same URL shape. Output channel `0` is the only index that does not sit on top
of an input slot.

When reporting addresses, always say which kind you mean, and never map an
output channel to an input slot by equality — the pipeline decides which slot
feeds which output channel, and the relationship is not guaranteed to be
`channel + 1`.

## Error envelope

All errors follow `{ "error": { "code": "snake_case_code", "message": "…" } }`.

The insight service returns HTTP 200 even on a logical failure, carrying
`{ success: false, error: "…" }` in the body — the backend inspects the body and
raises `insight_operation_failed` with that message. Transport-level failures
(no response, non-2xx) become `insight_unreachable`. Relay the `code`/`message`
to the user and suggest the next step (for "all slots in use", stop a stream
first).
