# View Streams — reference

## `count_streams`

Read-only agent tool. No parameters.

Returns:

```json
{ "count": 12, "channels": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11] }
```

- `count` — number of active **ingest** channels.
- `channels` — active channel indices (0..79), sorted.

Under the hood the Studio backend calls neat-insight `GET /api/ingest/stats`,
whose `channels` array has **one entry per currently-active ingest channel**, so
the length is the exact active-ingest-channel count. No per-channel probing /
binary search is needed. Channels are contiguous: if channel `n+1` is active,
`n` is too.

### What this number does NOT tell you

`/api/ingest/stats` measures the **device→insight** leg only. Whether any of
those channels reaches a browser, decodes, and renders is the **insight→browser**
leg, and it is measured separately by `/api/egress/stats` (exposed as
`list_output_streams`). The two are independent.

Consequences:

- `count_streams` returning `N` is **not** evidence that `N` tiles are visible.
- A user reporting fewer visible streams than `count` is not contradicting this
  tool — they are describing a leg it cannot observe. Do not rebut them with it.
- Diagnosis of a blank/frozen tile starts at `list_output_streams`
  (`peers[].browser.video.*`) and continues in `sima-use-neat-insight`.
- **No pipeline action (restart, rebuild, redeploy, stop) is a remedy for a
  browser-side symptom.**

Errors are the standard envelope `{ "error": { "code", "message" } }`:

- `insight_unreachable` (502) — the media/stream service didn't respond.
- `not_implemented` — the stream tooling isn't wired in this environment (no
  media handles).

## Post-deploy: `count` is 0 because the channels are not up YET

An output channel comes into existence only when the device pushes its first
annotated frame on it. Between `run_pipeline` returning `running` and that first
frame there is a real gap — model load plus first inference, observed at
**seconds to ~2 minutes** on a DevKit.

So immediately after a deploy, `count: 0` is a *timing* reading, not a verdict:

- Poll `count_streams` every ~10 s for up to ~2 minutes before concluding
  anything.
- Only a count still at 0 after that window is a pipeline problem — report it
  with `get_pipeline_status.log_tail`, which names the actual fault (missing
  model, unreadable source, bad config).
- **`start_stream` is never the remedy.** Input slots (1–16) and output channels
  (0–79) are separate namespaces; starting an input stream cannot bring an
  output channel into existence, and doing so only adds an unrelated stream.
- A count that comes up and then *shrinks* is a pipeline dying mid-run, not a
  display problem. Do not restart it to "retry" — report the loss and the log.

Stability, not mere presence, is the bar for emitting a grid: two `count_streams`
samples **10 s** apart with a non-shrinking channel set, backed by non-zero
`output_fps` in the run log. Ten seconds of held video is enough — don't stall
the reply watching a stream that is already proving itself. That ladder lives in
`edgematic-build-deploy-run`.

## The `edgematic-streams` block

The standard display format. Emit it as assistant text; the Studio UI parses it
at render time (it never reaches any tool) and renders a compact live grid as
the last message.

````
```edgematic-streams
{ "count": 12, "channels": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], "rows": 4 }
```
````

Body schema (JSON object):

| Field | Type | Notes |
| --- | --- | --- |
| `channels` | `number[]` | Preferred. Active channel indices (0..79). Deduped, sorted, out-of-range dropped by the UI. |
| `count` | `number` | Shorthand. Expanded to `0..count-1` when `channels` is absent. |
| `rows` | `number` | Optional, 1–4, default 4. Max grid rows; columns = `ceil(channels / rows)`. |

Rules:

- Prefer `channels` (verbatim from `count_streams`); fall back to `count` only if
  you lack the list.
- A malformed or empty block renders as plain text — only emit when `count > 0`.
- **Emit at most ONE block, as the LAST thing in the message.** The UI hoists the
  block out of the prose and renders the grid after every text segment, so its
  position in your message does not move the grid — but prose written after it
  will read out of order. When more than one valid block is present, the LAST one
  wins (a second block is treated as you correcting yourself).
- **One stream renders exactly like many** — a one-entry `channels` array is a
  one-tile grid with the same chrome. There is no single-stream mode.
- The grid re-renders on reload (replayed from the transcript). In a new chat,
  re-invoke the skill to re-emit the block.

## Lifetime — the last-turn rule (BEHAVIOURAL, not cosmetic)

**Only the last chat turn negotiates streams.** Earlier turns render idle tiles,
deliberately, so that a scrolled-back conversation does not reopen dozens of peer
connections.

This means a grid you emit stops showing video **as soon as the user sends their
next message** — the peers are torn down and the tiles go idle in place. It is
the single most common cause of "I could see the streams and then I couldn't",
and of "the /streams page works but chat doesn't" (the `/streams` route holds its
own sessions and is unaffected).

Therefore:

- Tell the user this when you emit the block.
- Re-invoke the skill to bring the grid back — that is the intended flow, not a
  workaround.
- When the streams must persist across messages, point at the durable viewer
  (`GET /api/viewer-url?mode=light&src=0,1,2,3`, documented in
  `sima-use-neat-insight`) or the `/streams` route.

## Rendering (for reference)

- Each tile is a recv-only WebRTC connection to `/video/offer?channel=<N>`
  (proxied to insight), the same primitive the Video Viewer uses.
- The grid shows up to 80 tiny tiles clamped to `rows` rows; a single grid-level
  "pop out" control opens the whole block in the workspace / the full `/streams`
  view. Tiles have no per-channel pop-out — the grid is the unit.
- One tile → one peer connection. If `list_output_streams` shows materially
  fewer peers than the channels you emitted, those tiles failed to negotiate;
  report that rather than inferring a pipeline fault.
