---
name: edgematic-netron-view
description: Use when the user asks to see, show, open, view, inspect or visualize a model's graph, layers or architecture in Edgematic Studio — "show me a netron view of the current model", "open resnet50 in Netron", "what does yolov8.onnx look like", "show me the model graph" — and ALSO the moment a model has just been attached or uploaded in chat, to offer the user a look at its graph before anything else is decided about it. Covers opening a model the user attached in chat straight from the absolute path its attachment message states, locating a model file in the project workspace by the name the user typed or the one the conversation establishes when they say "the current model", widening to every .onnx in the project and asking the user to choose when nothing matches, opening the Netron viewer on the file that was found, and offering the view as a quick-action button rather than opening it unasked. Only uncompiled .onnx models can be opened — either a file in the project workspace or a model attached in chat. Offering or opening a view is the whole of this skill — a request to compile or quantize a model belongs to edgematic-model-compile even when that same model was just attached. Do not use for compiled .sima / *_mpk.tar.gz artifacts (Netron cannot read them), for a running pipeline's live video or detections (see edgematic-view-streams and edgematic-foxglove-viz), or for the pipeline canvas.
---

# Edgematic Netron View

## Overview

**Netron** is the model-graph viewer bundled with Edgematic Studio. Opening a
model in it adds a tab to the user's editor column showing that model's layers
and topology.

Say **Netron** to the user. The shipped file-explorer menu item already reads
*Show in Netron view* in every locale, and it is the word the user types when
they ask for this.

Two tools serve this flow, and no others:

| Tool | What it does |
| --- | --- |
| `find_project_files` | Searches a project's whole working directory. `pattern` is a case-insensitive **substring of the project-relative path**, not a glob — a literal star matches only a file whose name contains one. Use `extension` for a file type (`onnx`, with or without the leading dot). Give at least one of the two; supply both to require both. Optional `path` limits the search to one directory's subtree. |
| `open_netron_viewer` | Opens one model as a viewer tab. Give **exactly one** of `path` (project-relative, for a file in the project's working directory) or `model_path` (the absolute path of a model attached in chat). Both, or neither, is refused. It is a display action — it returns nothing about the model itself. |

**The rule that outranks everything else here: a path you hand to the viewer
comes from a search result or from the user. Never construct one, never
complete a name into one, never guess a directory or an extension.** Opening
the wrong model looks exactly like opening the right one, so a guess is not a
cheap mistake.

## A model reaches you one of two ways

- **Attached in chat.** The conversation carries a message of the form:

  ```
  I've attached the model "resnet50" at /absolute/path/to/resnet50.onnx.
  ```

  That path *is* the model. Handle it at step 0 and do not search.

- **A file in the project's working directory.** Found by searching — steps 1
  to 7.

## Procedure

### 0. Did the user attach a model?

If this conversation contains an attachment message like the one above and the
user is referring to that model — including when they say "the current model",
"this model" or "it" and that attachment is the most recently established model
in the conversation — call `open_netron_viewer` with `model_path` set to **that
exact path, copied character for character** from the attachment message.

- Do **not** search first. The path is already in front of you; re-deriving it
  costs a round and can land on a different file.
- Do **not** pass it as `path`. That parameter is project-relative and is for a
  file in the project's working directory.
- If the call fails, **report the exact path you tried, and stop.** Never
  substitute a different model. Never offer a similarly-named one unless the
  user names it themselves. Never fall through to the search ladder below as a
  way of "finding it anyway" — that ladder resolves *project* files, and using
  it here would open a file the user did not attach.

If the user is asking about a project file rather than about the attachment, or
no attachment message appears in this conversation, continue at step 1.

**If the attachment is the newest thing in the conversation and the user has
not asked to see it,** do not open anything. Answer whatever they actually
asked, and — when the attached file is an uncompiled `.onnx` — end the reply
with an offer to view it; see *Offering the view* below. An attachment is the
moment a look at the graph is most useful and least often asked for, which is
what an offer is for; opening a tab they did not ask for takes over their
editor column instead. An attached archive gets no offer: the paragraph below
says why.

**If the attached model is a `.tar.gz` archive,** the viewer refuses it and
states both the reason and the recovery. Relay that sentence to the user as it
was given. Do not unpack the archive, do not look for an `.onnx` inside the
project to open in its place, and do not retry the call with `path`.

**If the user refers to a model they attached but no attachment message is
visible in this conversation** — a long session can drop older messages, and
the path goes with them — say exactly that, and ask them to re-attach the model
or to give you its path. Do **not** search the project for a file with a
similar name and open that: it would be a different model from the one they
mean.

### 1. Determine the target name

Use the name the user typed. For "the current model", "this model" or "it",
infer the model most recently established **in this conversation** — a file the
user opened, a model just compiled, downloaded or deployed, a name from an
earlier turn. If nothing in the conversation establishes one, skip to step 4.

### 2. Search

Call `find_project_files` with that name as `pattern` and `onnx` as
`extension`.

### 3. Act on the count

- **Exactly one match** — open it (step 5), and tell the user which file was
  opened.
- **More than one match** — present the list and ask which one they mean. **Do
  not guess, and do not pick for them.**
- **Zero matches** — go to step 4.

### 4. Widen

Call `find_project_files` with `onnx` as `extension` and no `pattern`.

- **Exactly one match** — that is "the current model". Open it, and say which
  file it was.
- **More than one match** — present the list and ask which one they mean.
- **Zero matches** — tell the user the project contains no ONNX file, and name
  what would produce one (compiling a model, or downloading one) **without
  doing it unasked**.

### 5. Open

Call `open_netron_viewer` with the project id and the chosen project-relative
path as `path`.

### 6. Never invent a path

Every path you pass to the viewer was returned by a search or typed by the
user. If you do not have one, ask — an invented path either fails or, worse,
succeeds on the wrong file.

### 7. Read the truncation flag before you conclude "none"

A search result carries `truncated`. When it is `true` there may be more
matches than the ones you were shown, so **say so** rather than reporting that
nothing exists. Narrow the search first — a `path` to search under, or a
tighter `pattern` — and search again.

## Offering the view

A reply can end with a **quick-action button** the user clicks. One button type
opens the Netron viewer directly, with no further turn:

```quick-actions
[{"type":"netron","label":"Show in Netron","path":"models/yolov8n.onnx"}]
```

**The button is an OFFER.** Emitting it opens nothing; the click does. So emit
it *instead of* calling the viewer tool, never as well — doing both takes over
the editor column and then offers to do it again.

Give **exactly one** model reference. Both, or neither, and the whole block
degrades to plain text: the user reads the JSON instead of clicking a button,
and no error says why.

- `path` — project-relative, for a file in the project's working directory.
  Copy it from a search result, exactly as the rule above requires. An absolute
  path is rejected.
- `modelPath` — the absolute path of a model attached in chat, copied character
  for character from the attachment message. This is the form to use right after
  an upload: Studio resolves the path against the models it holds, and refuses
  the button if nothing matches, so a path it does not recognise never reaches
  the viewer.
- `userModelId` together with `filename` — for a model attached in chat whose
  `user_model_id` an earlier `open_netron_viewer` result already returned. Use
  `modelPath` when you have only the attachment message.

Offer the button whenever a look at the graph would help and the user has not
asked for one: a model was just attached, a search turned up exactly one model,
or the work you just finished produced or referenced one. When they *did* ask,
open it — an offer in answer to a request reads as a refusal.

**Never offer it for a `.tar.gz` or a `.sima` artifact.** Netron reads model
graphs, not compiled packages, so the button would fail on the click. An offer
that cannot work is worse than no offer.

### The button for a model that was just attached

This is the common case: the user uploads a model, their message states its
absolute path, and the reply should end with the button rather than make them
ask a second time. Use `modelPath`, copied character for character from that
message:

```quick-actions
[{"type":"netron","label":"Show in Netron view","modelPath":"/abs/path/from/the/message.onnx"}]
```

Do not retype the path, do not tidy it, and do not search for the model first —
the path in the message is the only handle either of you has on that file, and
an approximation is how a different model gets opened.

If the attachment message is no longer in view, ask for the path. Do not offer
the button for a model you cannot name.

## What cannot be opened

- **Compiled SiMa artifacts** — a `.sima` file, or a compiled `*_mpk.tar.gz`
  package. Netron reads model graphs, not compiled packages. Never pass one to
  the viewer; say that the compiled artifact cannot be viewed and that the
  uncompiled model can.
- **A model uploaded as a `.tar.gz` archive.** The viewer refuses it with a
  reason and a recovery — relay both.

Only an uncompiled `.onnx` model opens: a file in the project's working
directory, or a model attached in chat.

## Reporting back

- Always name the file you opened. "Opened the model" with no filename leaves
  the user unable to tell a right answer from a wrong one.
- When you asked the user to choose, wait for their choice. A list plus an
  opened tab reads as though the question was rhetorical.
- When a call is refused, relay the refusal's own reason and recovery rather
  than paraphrasing it into "that did not work".
