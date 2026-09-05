---
name: edgematic-ros-capabilities
description: Use when the user wants to set up or open a host ROS 2 colcon workspace in EdgeMatic Studio and work on which capabilities its robot builds with — "clone the robot repositories", "set up the ROS workspace", "open this ROS workspace", "what capabilities does this build include?", "add/remove/turn off <capability>", "build the ROS workspace", "deploy it to the robot". Covers the agent tools clone_repository / open_ros_workspace / list_ros_capabilities / set_ros_capabilities / prepare_ros_build / cancel_ros_build, cloning the client repository and sima-core into one parent directory before opening it (and why that clone must never be improvised in a shell), the rule that the selection is only the bringup package's exec_depend entries, completing the third-party sources the workspace declares in its dependencies.repos files (with the revision each one pins) before any build, working out and naming the build script since prepare_ros_build has no default for it, searching a build log past its tail with get_build_status's match, the build handoff (Studio starts the build itself where a build channel is configured and otherwise hands the user a command to run, and watches the log either way — branch on the run_on the tool returns), and how to read the two build failures that really happen. Do NOT use for board-side ROS 2 Neat pipelines on a paired DevKit (run_ros_pipeline / ros2_topic_list / ros2_node_list — see ros2-neat-nodes), Foxglove/Flora rendering (see edgematic-foxglove-viz), board bring-up and flashing (see ros2-edgematic-integration), or EdgeMatic model-archive projects (build_project / run_pipeline — a DIFFERENT, non-ROS flow, see edgematic-build-deploy-run).
---

# ROS Workspace Capabilities, Build & Deploy

A **host-side ROS 2 workspace** is a directory on this machine holding two sibling
repositories: a **core** repository, which carries a `capabilities/` directory — that
is what identifies the workspace at all — and a **client** repository beside it. The
client's *bringup*
package declares which of the core's capabilities the robot is built with. When those two
repositories are not on disk yet, `clone_repository` is what puts them there — see step 0.

Studio drives this through five workspace tools, plus the general-purpose clone that puts the
repositories on disk in the first place. **Every specific name — the client directory,
the core directory, the bringup package, the container, the selection file, and every
capability — comes from the tools' output, never from this document and never from
memory.** Two installations do not agree on any of them.

**The ROS toolchain lives in a container Studio is not inside**, so who starts the build
depends on the installation — and `prepare_ros_build` tells you which happened in its
`run_on` field. Read it from the tool result; you have no view of the configuration
behind it. Where a build channel is configured, Studio asks that channel to start the
build inside the container and `run_on` comes back `"container"`. Where none is,
`prepare_ros_build` returns the *command*, the user runs it, and `run_on` comes back
`"host"`. Either way Studio watches the log the build writes and settles the build row
from it.

## The order

Follow it. Each step needs what the one before it returns.

0. **Clone both repositories into one parent** — `clone_repository` twice, sharing a single
   `parent`, and then step 1 on that same parent. Skip it only when the two repositories are
   already on disk side by side. See "Getting the two repositories onto disk" below, which
   also covers why the clone must not be improvised in a shell.
0b. **Complete the workspace's third-party sources** — see "Dependencies the workspace
   declares" below. Cloning the two repositories is NOT enough to build; do this before
   step 4 or the build fails on a package that was never fetched.
1. **`open_ros_workspace` `{ path }`** — the absolute host path the user named, or the parent
   step 0 cloned into. Detects the layout *before* registering anything, so a directory that
   is not a usable workspace is refused without leaving a project behind. Returns `project_id`,
   `client_dir`, `core_dir`, `bringup`, `selection_file` (relative to the workspace
   root), the catalogue (`available` / `capability_groups` / `selected` /
   `unknown_selected`) and `active_from`.
   **Then end the turn — see "Opening binds from the next turn" below.**
2. **`list_ros_capabilities` `{ project_id }`** — the same catalogue, re-read. Opening
   already returned it, so this is for a later turn or a re-check after an external edit.
   Writes nothing.
3. **`set_ros_capabilities` `{ project_id, capabilities }`** — only when the user wants
   the selection changed.
4. **`prepare_ros_build` `{ project_id, script }`** — opens a pending build row, starts the
   watcher, and returns `run_on`, `log_path` and `build_id` always, plus `command`
   **only when `run_on` is `"host"`**. On the container path that key is *absent*, not
   empty.
   **`script` is required and has no default** — see "Which script builds this project".
5. **Branch on `run_on`.** When it is `"host"`, show `command` to the user as a fenced
   `bash` block and ask them to run it on the host — the chat already renders a fenced
   block with a copy button, so nothing else is needed. When it is `"container"` there is
   no `command`: say that Studio started the build in the container, and go straight to
   step 6. Never render a fenced block with nothing in it.
   Both branches are the cross-compiler: `"container"` is Studio starting the build
   inside it, `"host"` is the user starting the same thing by hand. If the container
   turns out not to exist at all, that is **not** a cue to build on the robot instead —
   stop and ask the user, with the wording and the three answers
   `edgematic-ros2-portable-pipeline` carries. Installing the container
   (`edgematic-ros2-host-container`) is the fix; a device build is a decision only
   they can make.
6. **Poll `get_build_status` `{ project_id }`** until it is terminal, and read the result
   as described under "Watching the build". When a failure's cause is not in the returned
   `log_tail`, call it again with `match` — for example
   `{ project_id, match: "Could not find a package" }` — which searches the WHOLE log and
   returns the matching lines. The default tail is only the last few KB, and a colcon
   failure prints the missing package's name well above the line that reports the failure.
7. **Deploy** to the paired device with `deploy_to_device` once — and only once — the
   build reported an observed success.


## 0. Getting the two repositories onto disk

When the workspace is not on disk yet, put it there with `clone_repository` — **twice, into
one and the same `parent`** — and then open that parent. Unless the user named other
repositories, they are:

1. `clone_repository` `{ "repo": "sima-vertical-solutions/stiga", "parent": "<the parent>" }`
2. `clone_repository` `{ "repo": "sima-vertical-solutions/sima-core", "parent": "<same parent>" }`
3. `open_ros_workspace` `{ "path": "<that same parent>" }`

Three calls rather than one, and that is what the general shape of the clone tool costs:
`clone_repository` places any git repository in any allowed directory and knows nothing about
ROS, so **nothing inside it enforces the pair — the single shared `parent` value is the only
thing that makes the two clones siblings.** Pass a different `parent` to either call and you
get two directories that no workspace root contains, and the third call then has nothing to
detect. Pass the same one to both clones and to the open, and the layout is correct by
construction.

Leave `name` out. The destination folder name is derived from the repository itself, which is
already the name the workspace expects; send `name` only when the user asked for a different
folder. Re-running step 0 is safe: a destination that already exists is left untouched and
comes back as `outcome: "already_present"`, with nothing re-cloned. Submodules are reported
through `has_gitmodules` and never fetched — neither of these repositories uses them, so if
that comes back true, say so rather than acting on it.

**A wrong layout is refused legibly, and that is the compensating control for the clone tool
not guaranteeing one.** `open_ros_workspace` detects the layout *before* it registers
anything, so a directory that is not a usable workspace leaves no project behind, and its
refusal names exactly what it could not find — no child holding a `capabilities/`
directory, several children holding one, a missing `bringup` key, no sibling holding a
`capabilities` directory — with your own path spelling echoed back and everything else stated
relative to the workspace root. Read the sentence, fix the thing it names, and open again. Do
not go probing other directories to work out what happened.

### Choosing the parent

Pick it yourself, along with both folder names. The only thing you take from the user here is
a preference they actually stated; do not open a round of questions about where to put things.
Two constraints, and this document deliberately names no path, because neither of them is a
path it can know:

- The parent must sit **inside the directory Studio and the ROS container both mount at the
  same path** — the same premise the build command relies on (see "Always invoke the
  workspace's own build script"). A pair cloned outside it clones perfectly well and then fails
  at build time, visibly, with a failed `cd` as the whole log.
- The parent must **not be Studio's projects root itself**, which is also that mount. Studio's
  own managed projects sit directly in it, so opening it as a workspace is refused for
  containing them, and the repository pair has nowhere to sit that is not already inside
  somebody's project. A subdirectory of that root is the right shape.

`parent` does not have to exist already. The clone creates it when it is missing — **one
level only**, and only inside the directories Studio is allowed to write in: a single new
folder directly inside a directory that is already there gets created for you, while a path
with more than one missing directory in it still refuses. So name one and get on with it; do
not stop the flow to ask the user to make a directory by hand. The two constraints above are
what decide *which* folder — inside the shared mount, and not the projects root itself, which
is wrong for a reason that has nothing to do with whether it exists. If the call still
refuses with your path echoed back as not found, more than one directory in it is missing:
shorten it to one new folder inside a directory that is there, and call again.

### Never clone by hand

Do not perform the clone through a shell — not through run_command, and not through a
provider's own shell tool. Two concrete reasons, because a bare prohibition only invites a
cleverer improvisation:

1. **The credential.** `clone_repository` hands the token to git through a credential helper
   scoped to the one host, in the child's environment, so it never appears on a command line
   and never lands inside the cloned repository. A hand-written clone has two options and both
   are bad. Put the token in the remote URL and it is written into that repository's own
   config, where it survives the call, comes straight back out of `git remote -v`, and travels
   to anyone the tree is shared with. Leave it out and the clone simply fails on a private
   repository.
2. **Git-LFS.** These repositories keep the robot meshes in Git-LFS. Without the LFS filters
   configured, the clone reports success, `git status` comes back clean, and every mesh on
   disk is a hundred-odd bytes of pointer text where the geometry should be. That is a silent
   wrong result rather than an error, and it has been reproduced on the real repository.
   `clone_repository` configures the filters and then scans the finished checkout for pointer
   files, so it fails loudly exactly where a hand clone looks fine.

It matters most on `claude-code`, where the native shell is auto-approved outside the ask-first
posture — so the improvised clone is precisely the one that passes no gate on its way to disk.

### Ask for a token only when the tool asks for one

Call `clone_repository` with no `token` at all. Studio resolves the credential itself, from
its own configuration or from the one it stored the last time somebody supplied one, and when
it has one the parameter is never needed.

Ask **only** when the call comes back `clone_unavailable` with `requirement` set to `token`.
Then ask once, in one sentence, for a GitHub personal access token with read access to the
repository, retry the same call with it in `token`, and **tell the user it is stored and will
not be asked for again** — which is true: a token supplied this way is saved before the clone
runs and read back on every later call.

Never begin a workspace setup by asking for a credential. Most of the time there already is
one, and a flow that opens with a secret prompt is asking for a secret before it has shown
that it needs one.

The other two `requirement` values are not yours to repair. `git` and `git_lfs` mean the
runtime image is missing a binary; an operator has to install it, and retrying the call cannot
start succeeding. Report which one, and stop.

**When the clones are done and `open_ros_workspace` has returned, end the turn** — see
"Opening binds from the next turn". Step 0 does not change that rule; it only means more
happened before it.

## 1. A capability is a ROS PACKAGE, not a folder in `capabilities/`

`capabilities/` is not a flat list. It holds a mix of **domain** directories that group
several packages and packages that sit **flat**, and only the packages are selectable:

```text
capabilities/<domain>/<package>/package.xml        grouped under a domain
capabilities/<package>/package.xml                 flat — no domain
capabilities/<domain>/src/<package>/package.xml    grouped, nested behind `src`
```

So read the catalogue like this:

- **`available` is the authoritative set.** It lists package names, flat, and it is the
  only thing `set_ros_capabilities` accepts. If a name is not in `available`, sending it
  refuses.
- **`capability_groups` is the same packages, organised.** Each entry is
  `{ "domain": <name or null>, "packages": [{ "name", "selected" }] }`. Use it to answer
  "what is there?" in the shape the user recognises, and to say which domain a package
  came from. `domain: null` means the package sits flat and genuinely has no domain —
  do not invent one for it.
- **A domain is NOT a capability.** Never send a `domain` value in `capabilities`; it
  will refuse, and correctly. Nor is `src` — where a domain nests its packages behind
  one, the packages are reported under the DOMAIN and the `src` level never appears.
  A group with an empty `packages` list is a domain that offers nothing selectable —
  usually because it holds only third-party source trees rather than capability
  packages of its own.

**Most `unknown_selected` entries are normal.** The bringup package depends on plenty of
things that are not capabilities of the core repository — the client's own packages, a
separate sensor stack, packages imported by `vcs` — and in a real workspace they can
easily outnumber the recognised ones. That is not a fault to report or to fix; those
entries are preserved untouched. Only say something is wrong if a package the user
expected to be selectable is missing from `available`, and in that case check
`capability_groups` before concluding anything. Only those three layouts are
offered: a package nested behind any level other than a domain's own `src` is not,
and neither `src` nor a domain name is ever itself a capability.

## 2. The selection is ONLY the bringup package's `<exec_depend>` entries

Changing which capabilities the robot builds with means changing the bringup package's
`<exec_depend>` entries and **nothing else in that file**. `set_ros_capabilities` is the
only thing that may write it.

- **Never edit the manifest with `write_file`.** The selection tool uses a line editor
  that re-emits every line it does not own byte-for-byte; a general file write replaces
  the whole file and will silently reformat, reorder or drop what it did not understand.
- **`capabilities` is the COMPLETE desired set, not a delta.** A capability that is
  selected today and missing from the list is removed. To add one, send the current
  `selected` plus the new name.
- **Only names from `available` may be sent.** A name matching none of them refuses,
  naming every unknown name and the available set at once, and leaves the file untouched.
- **`unknown_selected` is not yours to manage.** Those are dependency entries of the
  bringup package that name no available capability — ordinary package dependencies.
  They are reported so you can see them, they are preserved verbatim in place, and they
  must **not** be echoed back in `capabilities` (they are not capabilities, so the call
  would refuse). Since `capabilities` is the complete set and covers only capabilities,
  leaving them out is exactly what keeps them.
- If the user asks about a capability that is not in `available`, say so and list what
  is. Do not invent one, and do not create a directory to make one exist.

### Undo restores the SELECTION, not the file

`set_ros_capabilities` returns `previous_selection` — the selection in force before the
write. Passing it straight back restores that selection, and that is all it restores.

A capability that was **removed** and is then brought back comes back in canonical form:
attributes such as `condition=` are gone, and the entry lands after the last surviving
entry rather than in its original position. Only the pure-addition direction is
byte-exact. **Tell the user this rather than promising a byte-exact undo**, and if the
entry mattered in its original spelling, say that reverting it is a job for their VCS.

## Dependencies the workspace declares

**Cloning the client and core repositories does not give you a buildable workspace.** The
third-party sources are declared, not vendored, and nothing fetches them for you. A build
attempted without them fails on a package that is simply absent — most often as
`Could not find a package configuration file provided by "<name>"`.

Where the declarations live, in the order to read them:

| File | Declares |
| --- | --- |
| `<core>/capabilities/*/dependencies.repos` | one file per capability — apriltag, py_trees, rtabmap and so on |
| `<client>/dependencies.repos` | the client's own mission dependencies |
| `<client>/manifest.repos` | the platform repositories — the client and the core you cloned yourself, and sometimes others nothing else declares |

Each is a `vcs` manifest: a `repositories:` map of `name → {type, url, version}`.

**What to do:**

1. Read those files (they are ordinary project files — `read_file`).
2. List `<client>/src/` and see which declared names are missing.
3. `clone_repository` each missing one into `<client>/src/`, **passing `ref` set to the
   manifest's `version`**.

**`manifest.repos` is where to look when a package is missing that no
`dependencies.repos` declares.** It names the platform repositories — usually the client
and the core you cloned yourself, but it can name more: the Stiga workspace declares
`sima-sensor-stack`, which carries `sensor_bringup`, `intel_realsense_d435`,
`imu_icm42688_spi`, `power_board_driver` and `sensor_manager`, and nothing else on disk
mentions them.

Fetch from it on that symptom rather than on sight. The capability manifests declare BUILD
dependencies, so taking all of them is right; `manifest.repos` mostly declares packages
needed at RUN time, and a repository's packages join the build graph the moment they are on
disk — so pulling one nothing needs lengthens every build and adds ways for it to fail.

**Do not scope this to the selected capabilities.** It is tempting and it is wrong: a
package outside the selection can still be pulled into the build graph by an ordinary
dependency — in the Stiga workspace `stiga_behavior` requires `apriltag_docking` whatever
the selection says. Take every declaration.

**`ref` is not optional in practice.** The manifests pin branches (`release/2.4.x`), tags
(`v1.2.1-devel`) and raw commits (`62a272ac…`). Omitting it clones the default branch,
which succeeds, builds, and ships a different revision than the one asked for — a failure
nothing downstream can notice.

A manifest may name a private repository (the Stiga workspace's `visual_odometry` names two).
Those need a credential; report them by name rather than silently skipping them.

## Which script builds this project

`prepare_ros_build` requires `script` — the build script to run, relative to the client
repository — and there is **no default**. Work out what this project actually uses:

1. Look for an executable script at the client repository's root (`build.sh` is the common
   name, but it is only a convention).
2. Failing that, read its `README` for the documented build command.
3. If there is no script at all, **write one** into the client repository with `write_file`
   and pass its name. A three-line script that sources the ROS environment and runs
   `colcon build` is a perfectly good answer.

Pass the path as it sits relative to the client repository — `build.sh`,
`scripts/compile.sh`. Absolute paths and `..` are refused.

## 3. Always invoke the workspace's own build script — never compose a colcon command

`prepare_ros_build` builds a command that changes into the client repository inside the
container and runs the script you named, verbatim. When `run_on` is `"host"` that command
is in the result: present it, and do not write your own. When `run_on` is `"container"`
there is no command to present — Studio already ran that same script through the channel,
in the same container — and the rule against composing one of your own is if anything
stronger, because there is nothing to correct.

Both paths in that command — the directory it changes into and the log it writes — are
the paths **Studio** resolved, handed to the container untranslated. That is correct
because the workspace is cloned under the directory Studio and the ROS container both
mount, at the same path. A workspace cloned outside that shared mount is what breaks it,
and it breaks visibly: the `cd` fails, its message is the whole log, and the build
reports a non-zero exit. If you see that, say the workspace is not under the shared
mount — do not rewrite the path.

**The reason, because a bare prohibition just invites a cleverer improvisation:** the
workspace's `build.sh` carries roughly fifteen tuned flags. Among them are worker caps
that stop a parallel build from exhausting memory and getting OOM-killed part-way
through, `--packages-ignore` entries that keep Qt-based GUI packages out of an image
destined for a headless robot, and a set of `-DWITH_*=OFF` switches. A hand-written
`colcon build` drops all of them. The two failures that follow are concrete: the build
dies to the OOM killer with a log that looks like a compiler crash, or a GUI package is
dragged onto a robot that has no display and no business running it.

So:

- **Do not** compose, "simplify", or extend a colcon invocation.
- **Do not** reflow, re-quote or split the returned `command` — the case where `run_on`
  is `"host"` and there is one to return. Everything after
  `bash -lc` is one quoted word on purpose: the redirect and the exit marker are
  evaluated **inside** the container, which is the only place the log path means what
  Studio thinks it means. A command the user's own shell rewrote writes its log
  somewhere Studio cannot see, and the build reads as one that never started.
- **Changing which packages are built is a selection change**, not a different build
  command — that is exactly what `set_ros_capabilities` is for.

When `run_on` is `"host"`, present it like this, with the tool's own string substituted
verbatim:

````
```bash
<the command string prepare_ros_build returned, unchanged, on one line>
```
````

When `run_on` is `"container"` this template does not apply: there is no `command`, and a
fenced block with nothing substituted into it reads to the user as a broken tool. Say what
happened instead, with no fenced block at all — for example:

> Studio started the build in the ROS container. I'm watching the log at `<log_path>` and
> will report the outcome.

## 4. Payload rules come from `deploy.yaml`, never from memory

What gets shipped to the robot and where it lands is declared by the workspace's own
`deploy.yaml` — keys such as `bundle_libs`, `runtime_pip`, `upstream_setups`, `models`,
`remote_dir` and `ros_domain_id`. Consult that file with `read_file`, at its path
relative to the project, before you make any claim about the payload.

Never state a destination directory, a domain id, a library list or a model set from
memory or from another installation. A wrong `ros_domain_id` in particular decides which
robots hear each other, so a guessed value fails on hardware and not in Studio. If the
workspace declares a key you do not handle, say that it is declared and unhandled rather
than dropping it silently.

### What the deploy carries, and what it does not

By default `deploy_to_device` ships the staged `install/` tree plus whatever `models`
names. It does **not** carry `bundle_libs`, `runtime_pip`, `upstream_setups` or
`sys_config`, and the result says so in `skipped_deploy_keys`.

Read that field. It is the difference between "the deploy failed" and "the deploy
succeeded and the robot cannot start": a node that links RealSense or GTSAM, or imports a
vendored Python package, fails at load with nothing pointing back at the deploy.

When those keys matter, **assemble the payload yourself**: build a directory inside the
workspace holding the `install/` tree beside whatever else the manifest declares, and pass
its path as `payload`. That directory is shipped exactly as it stands — it replaces
staging rather than adding to it, so it must be complete. The result then reports
`payload` instead of `skipped_deploy_keys`, because staging did not run and its omissions
are not a fact about your directory.

Do not reach for the client's own `deploy.sh`. It refuses to run inside a container, and
Studio is inside one — there is nowhere to execute it from.

### After a deploy, look at the board

`ros2_topic_list` and `ros2_node_list` ask a paired device what it is running. Both take a
`domain`, and **passing it is not optional in practice**: ROS 2 discovery is partitioned by
domain id, the workspace declares its own, and querying the wrong one returns an EMPTY
LIST and exits successfully. That is indistinguishable from a board running nothing, so an
omitted domain does not fail — it misleads, and you will go looking for a fault that is
not there.

Take the value from `ros_domain_id`, which both `prepare_ros_build` and `deploy_to_device`
report. Never guess it, and never carry one over from another workspace.

## Watching the build

What `prepare_ros_build` set in motion depends on `run_on`. With `run_on: "host"` Studio
started nothing, and the row sits `pending` until the user actually runs the command.
With `run_on: "container"` the build is already running, and the row still sits `pending`
until it writes something. Either way the first output flips it to `building`. Poll
`get_build_status` and read `status`, `last_error` and `log_tail`.

**A build that merely goes quiet is recorded as UNCONFIRMED, not as success.** If the log
stops growing without the command's exit marker ever landing, the row goes terminal as
`failed` with a `last_error` beginning `ros_build_unconfirmed:`. The watcher observed
that output stopped — **not** that the process exited zero. There are three ways to arrive
here, and this side cannot tell them apart: a command handed over and never pasted, a
build that died without writing its marker, and — on the container path — a build channel
that answered `2xx` and started nothing at all. Never report an unconfirmed build as a
success, never deploy on the strength of one, and say plainly what happened. Then ask for
whatever witness the path actually has: when `run_on` was `"host"`, ask the user what
their terminal showed; when it was `"container"` there is no user terminal to ask about,
so the log is the only witness — quote its tail, and say the build channel itself is the
operator's to check. The other two prefixes are distinct on purpose:
`ros_build_failed:` is an **observed** non-zero exit, and `ros_build_timed_out:` means
the build never reached either terminal condition.

The build also holds the project's device-action slot until it reports, so a build,
deploy or run started meanwhile is refused. That refusal is correct — surface it rather
than working around it.

**Call `cancel_ros_build` `{ project_id }` on any of three triggers.** They are not tied
to one `run_on` value — the first belongs to the host path, the second to the container
path, and the third happens on both:

1. **The user declines the command.** `run_on` was `"host"`, you showed the command, and
   they decide not to run it.
2. **`prepare_ros_build` refused with `ros_build_env_unavailable`.** The configured build
   channel answered and refused, so a `pending` row is open with nothing behind it.
3. **A build was abandoned part-way**, on either path — or a prepare is stale and you
   want a fresh one.

Otherwise that slot stays held until the build deadline expires — up to two hours — and
build, deploy and run keep refusing with nothing to release them. Cancel settles the row
and frees the slot; the result says `cancelled`, or `nothing_to_cancel` when there was
nothing left to call off (which is not an error and needs no repair).

**On both paths it stops the watch, not the build.** With `run_on: "host"` Studio never
started the command, so if the user's build is still running, say so and ask them to
interrupt their own terminal. With `run_on: "container"` Studio *did* start the build and
it keeps running in the container — cancelling releases the slot and stops the watching,
and there is nothing here that stops that build.

## The two failures that actually happen

Diagnose in this order instead of retrying.

1. **A CMake error within seconds of the build starting** — a `find_package` that cannot
   find something, a missing development package. This is not the workspace: **the
   container the build ran in lacks a build dependency.** Report it, name the thing CMake
   could not find, and stop. Do **not** retry, do not edit `CMakeLists.txt`, and do not
   try a different build command — the remedy is on the container image, which is outside
   Studio's reach and the user's to fix.
2. **`EDGEMATIC_BUILD_EXIT=128` with no other output at all.** This is the git
   bind-mount trap, not a compiler failure: git refuses to operate in a workspace whose
   files are owned by a different uid than the one running inside the container
   ("dubious ownership"), and `build.sh` silences that call's stderr, so the log explains
   nothing. Name the cause, and tell the user the fix is to make git trust that directory
   or to align the ownership. Re-running it unchanged produces the identical empty log.

Anything else: quote the tail of the log rather than paraphrasing it, and do not conclude
"the workspace is broken" from a build the watcher never saw finish.

## Opening binds from the next turn

`open_ros_workspace` returns `active_from`, and on the CLI provider it says the opened
workspace becomes the conversation's project only from the **next** turn. The project a
tool call is scoped to is fixed when the turn starts, so a project-scoped call made right
after opening reaches the **previous** project.

So after a successful open: report what was found — the client and core directories, the
bringup package, the available capabilities and what is selected today — and **end the
turn**. The user's next message picks up in the workspace. Do not call
`list_ros_capabilities`, `set_ros_capabilities` or `prepare_ros_build` in the same turn
as the open, and never carry a `project_id` you invented rather than one a tool returned.

## Refusals, and what each one means

Every refusal names what it found and echoes the path exactly as it was given. Relay it;
do not guess around it.

- **The clone has no credential** — `clone_unavailable` with `requirement` set to `token`.
  This is the one clone prerequisite the user can supply; ask once, retry with it in `token`,
  and say it is stored. `git` or `git_lfs` in that same field means a missing binary in the
  runtime image: an operator's job, and retrying cannot help.
- **The clone destination is occupied by a project** — the folder would overlap a workspace
  Studio manages. Choose a different parent; do not delete anything to make room.
- **Not a usable workspace** — no child holds a `capabilities/` directory, or several
  do. Ask the user for the right directory; do not go looking for one by probing paths.
- **Recognised, but incomplete** — the client repository has no `deploy.yaml`, or its
  `bringup` key is missing. This one is worth reading carefully: the workspace WAS
  recognised, and what is named is the file to supply. Do not report it as "not a ROS
  workspace".
- **Unknown capability** — every unrecognised name is listed together with `available`,
  and the file was not touched. Correct the list and call again.
- **A line the editor will not own** — the manifest holds an `<exec_depend>` spread over
  several lines, or an unterminated comment. Refusing is deliberate: it is safer than
  rewriting a file it cannot model. Explain it and let the user tidy that line.
- **The workspace directory is missing** — the folder moved or its mount is not attached.
  This is not a "retry" condition; it is a state to explain.
- **The device slot is held** — a build, deploy or run is already active for that project.
