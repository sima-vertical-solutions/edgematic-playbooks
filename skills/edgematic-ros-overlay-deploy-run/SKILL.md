---
name: edgematic-ros-overlay-deploy-run
description: Use when a host-built ROS 2 colcon overlay has to reach a board and actually RUN there — "deploy these capabilities to the robot", "start the nodes on the device", "the deploy succeeded but nothing publishes", "prove this capability works on the board", "why is node list empty". Picks up exactly where the capabilities skill stops (a green host build) and carries through deploy, reconciling what the deploy tool silently skipped, launching on the board, and proving with published data rather than with a status string. Covers the client repo's own deploy script as the authoritative spec when one exists AND the fallback checklist when it does not, the three ways to launch a node on a board and why only one of them usually works, and the four failures that make a healthy overlay look dead. Do NOT use for choosing which capabilities to select or for the host build itself (see edgematic-ros-capabilities), for the board-side yolov8_seg/neat pipeline (see edgematic-ros2-neat-nodes), for first-time board flashing (see edgematic-ros2-integration), or for EdgeMatic model-archive projects (build_project / run_pipeline — a different, non-ROS flow).
---

# Deploying and running a ROS 2 overlay on a board

The capabilities skill ends at a **green host build**. This one starts there and ends at
**published data on the board**. Everything between those two points is where the work
actually fails, and it fails quietly: `deploy_to_device` returns success, `run_ros_pipeline`
returns `started`, and the board publishes nothing.

**A deployed overlay that is not running is indistinguishable from a broken one.** Do not
end a turn at "deployed". Deploy, launch, and show data.

## The core rule

> **By default `deploy_to_device` copies the staged `install/` tree and NOTHING else.**

It does not install pip packages, does not ship native libraries, does not ship the client's
system-config file, does not source upstream stacks, and does not generate a run wrapper. Any
of those the project needs are **yours to do by hand, after the deploy**. Which ones the
project needs is what step 1 determines.

**But do not reach for `scp` first.** `deploy_to_device` takes an optional **`payload`**
argument: a directory, relative to the workspace root, shipped *instead of* the staged tree.
That is the supported way to close the gap — assemble a directory that mirrors the board's
remote layout, holding the staged `install/` plus everything the profile declares that
staging does not carry, and name it. Re-read the tool's own schema for the exact wording
before relying on this; do not assume the parameter set from memory (missing it is exactly
how a deploy ends up half-done).

```bash
cp -al .deploy-stage/install <payload>/install     # hard-link: no copy cost
cp -al .deploy-stage/models  <payload>/models
mkdir -p <payload>/sys_config && cp <the config the launch needs> <payload>/sys_config/
```

Then `deploy_to_device { project_id, device, payload: "<payload>" }`. Fall back to `scp`
only for things that must land **outside** the remote directory.

## The order

1. **Find the client repo's own deploy path — BEFORE deploying anything.** (Step 1.)
2. Select capabilities and build on the host (that is the capabilities skill).
3. `deploy_to_device`.
4. **Reconcile `skipped_deploy_keys`** against what step 1 told you. (Step 3.)
5. Compensate every skipped item by hand over SSH.
6. Launch, on the right DDS domain.
7. **Prove with data**, not with a status field.

## 1. Read the client's deploy path first — it is the specification

Before the first deploy, look for a deploy path the repository already owns. In the CLIENT
repo root and in `tools/deploy/` of BOTH repos:

```bash
ls <client>/deploy.sh <client>/deploy.yaml <client>/tools/deploy/ <core>/tools/deploy/ 2>/dev/null
grep -rln 'scp\|rsync\|ssh .*ros2 launch' <client> --include='*.sh' | head
```

**If such a script exists, read it end to end before you deploy.** It usually cannot be run
from here — a one-click deploy typically drives Docker and SSH from the *host* and refuses to
run inside a container (`if [ -f /.dockerenv ]; then exit 1`). That does not reduce its value:
**it is the checklist of everything the deploy needs, written by the people who own the
robot.** Read it as a spec and perform its steps by hand. Not reading it is how you end up
discovering its steps one production failure at a time.

A deploy profile (`deploy.yaml` or similar) typically names: the board SSH target, the remote
directory, the DDS domain, the bringup package, the system-config file, native libs to bundle,
pip packages to vendor, and upstream setup scripts the board provides. Read the values from
the file — **never from this document and never from memory.**

### When there is no deploy script and no profile

This is the common case outside a mature client repo, and it does **not** mean there is
nothing to do — it means nobody wrote the list down. Derive it from the workspace, in this
order. Each check is cheap; run all seven.

| # | Question | How to answer it | If yes |
|---|---|---|---|
| 1 | Python deps the board lacks? | `grep -rh '^import \|^from ' <overlay python sources>`, and the `pip`/`python3-*` entries in each `package.xml` | `pip3 install` on the board, or vendor into `install/lib/python*/site-packages` with `--no-deps` |
| 2 | numpy inside the overlay? | `ls install/lib/python*/site-packages/numpy*` | **Delete it.** A board pins numpy against its own scipy/cv2; an overlay numpy shadows it and a 2.x shadow breaks cv2's C-API at import |
| 3 | Native libs with an ABI newer than the board's? | on the board: `ldconfig -p \| grep <lib>` vs what the build linked | ship the build's copy into `<remote>/native_libs/` and prepend it to `LD_LIBRARY_PATH` |
| 4 | A config file the launch requires? | `grep -rn 'sys_config\|config_file\|params_file' <bringup>/launch/` | ship it, then **read the `DeclareLaunchArgument` to see what form it wants** — see "Config arguments are not always paths" below |
| 5 | Upstream stacks living outside the overlay? | on the board: `ls /usr/local/*/setup.bash /opt/ros/*/setup.bash` | `source` each one **before** the overlay in the run wrapper |
| 6 | Model artifacts / weights? | a manifest under `models/`, or `.elf`/`.pth`/`.onnx` in `.gitignore` | provision them separately; they are not in the `install/` tree |
| 7 | Which **DDS domain**? | see "Recovering the DDS domain" below — never assume 0 | export it in every launch *and* every introspection command |

### Recovering the DDS domain without a profile

The domain is the single value whose absence hurts most (it is failure 1 below), and it is the
one no other check asks about. Four independent sources, strongest first — stop at the first
that answers:

1. **The overlay's own activation script.** The same file step 4 tells you to source usually
   carries the fleet default:
   ```bash
   grep -n 'ROS_DOMAIN_ID' <core>/tools/deploy/setup_overlay.sh <remote>/setup_overlay.sh
   # export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-<N>}"  <- the :- default IS the fleet domain
   ```
2. **A run wrapper a previous deploy generated on the board** — `<remote>/run_*.sh` typically
   pins it verbatim.
3. **The environment of ROS processes already running on the board.** Note the form: a shell
   redirect runs *unprivileged* and is refused on root-owned processes, so `sudo cat` and pipe:
   ```bash
   for p in $(pgrep -f 'ros2|component_container'); do
     echo "$p: $(sudo cat /proc/$p/environ | tr '\0' '\n' | grep '^ROS_DOMAIN_ID=' || echo 'unset => 0')"
   done
   ```
4. **Sweep for traffic** when nothing declares it — cheap and conclusive:
   ```bash
   for d in 0 <candidates from the sources above> ; do echo "domain $d: $(ROS_DOMAIN_ID=$d timeout 6 ros2 topic list 2>/dev/null \
     | grep -vcE '^/(parameter_events|rosout)$') non-default topics"; done
   ```

Also read the deploy tool's own response — it commonly reports the domain it deployed under.
Sources disagree in practice: a board can host one stack on 0 and another on the fleet domain.
Trust the overlay's activation script over whatever happens to be running.

### How far this fallback has actually been taken

Path A (a client repo *with* a deploy script and profile) has been exercised end to end:
deploy, reconcile, compensate, launch, published data.

**Path B — this no-profile checklist — has been exercised once**, on a workspace whose profile
was hidden for the test. It independently derived **4 of the 6** items the real profile
declared, and correctly concluded that nothing needed bundling or vendoring for that
selection. Three blind spots are known and systematic:

- **Check 1 sees only what is built.** It greps the `install/` tree, so runtime deps of packages
  outside the current selection are invisible. Grep the *sources* (`src/`, `capabilities/`) too
  when the list is meant to cover the whole robot rather than this build.
- **Check 4 finds the mechanism, not the choice.** It will tell you which argument the launch
  wants and turn up every candidate config, but not which candidate is *this* robot. Ask.
- **The domain was the gap that prompted check 7** — the original six never asked.

Treat path B as a floor, not a substitute for a profile the client repo should own.

Then **write the answers down** — as a deploy profile in the client repo if the user wants it
kept, otherwise at minimum in the turn's reply, so the next run does not rediscover them.

## 2. Getting a shell on the board

Most of this skill needs one. Check, in order:

1. **Studio's own SSH key**, next to the server: `<studio data dir>/ssh/id_ed25519` (typically
   `.../edgematic-studio/data/ssh/`). `list_devices` gives the host and user.
2. `ssh -i <key> <user>@<host> 'id; sudo -n true && echo passwordless-sudo'`

Check this **before** telling the user you cannot do something on the board. If the key is
there and the host answers, you have a shell — use it. Reporting "I have no shell" without
running these two commands is a false claim, not a limitation.

If there genuinely is no key, say so, and hand the user exact copy-pasteable commands for the
built-in terminal rather than a description of what to type.

## 3. Reconcile `skipped_deploy_keys` — this is not a formality

`deploy_to_device` returns a `skipped_deploy_keys` list: the profile keys it read but does not
implement. **Every key in that list is a step you now owe by hand.** Walk them one by one and
say, per key, whether the selected capabilities need it.

- Needed → do it over SSH before launching.
- Not needed → say *why* it is not needed for this selection.

Never dismiss the whole list at once. "Not critical for our packages" is a conclusion you may
only reach per key, after checking what each selected package imports and launches. A skipped
config key is exactly how a launch dies with an empty-parameter parse error twenty minutes
later.

## 4. Launching — three ways, usually only one works

| Way | Reality |
|---|---|
| `run_ros_pipeline` | Runs a **board-side workspace of its own**, at a path baked into the server — *not* your deploy directory. It `cd`s there and, if that directory does not exist, dies on the first command. It returns `status:"started"` **before** anything is verified, so `started` proves only that a detached shell was spawned. Verify the path exists on the board before assuming this tool can reach your overlay. |
| `run_pipeline` | EdgeMatic model-archive projects only. Not a ROS overlay. |
| **SSH** | What actually works. Source the overlay, set the domain, launch. |

The SSH form:

```bash
sudo setsid bash -c 'source <remote>/setup_overlay.sh <remote>/install; \
                     export ROS_DOMAIN_ID=<domain>; \
                     exec ros2 launch <pkg> <pkg>.launch.py' \
     > /tmp/<pkg>.log 2>&1 &
```

**Use the overlay's own activation script when one exists** (`setup_overlay.sh`, shipped
beside `install/` by the core's deploy helper). A `--merge-install` tree bakes the *build-time*
prefix into `install/setup.bash`, so sourcing that directly on the board resolves the wrong
paths. The activation script exists precisely to rewrite the prefix — prefer it, and check its
permissions: a script left by a root-run deploy is often unreadable by the login user
(`chmod 0644` fixes it).

Not every package is launchable. Before you conclude a capability "fails to start", check that
it has anything to start: `ls install/share/<pkg>/launch/ install/lib/<pkg>/`. Message/service
definition packages and node *libraries* have no executable by design — that is not a failure.

## 4b. Config arguments are not always paths

A launch argument named `sys_config` / `config` / `params` may take a **file path** or a
**serialized JSON string** — and the two fail identically from the outside. Read the
declaration before guessing:

```bash
grep -A4 "DeclareLaunchArgument" install/share/<pkg>/launch/<file>.launch.py
```

A `description` reading *"JSON-serialised system configuration passed from parent launch
file"* means this launch is a **child**: the parent normally loads the YAML and hands the
JSON down. Launching the child directly gives it `''`, and it dies with a validation error
whose `input_value=''` is the tell. **`input_value=''` means nobody passed the argument — not
that a file is missing.** Do not diagnose it as a shipping failure.

Produce the JSON on the board with the project's own loader, so the same validation runs:

```bash
python3 -c "from pathlib import Path; from <config pkg> import load_config; \
            print(load_config(Path('<board path to the yaml>')).model_dump_json())"
```

then pass it: `ros2 launch <pkg> <file>.launch.py <arg>:="$(cat <the json>)"`.

Getting past this error does not mean the capability runs — it means you reached the *next*
blocker, which is the honest thing to report.

## 5. The four failures that make a healthy overlay look dead

1. **Domain mismatch.** Studio's `ros2_topic_list` / `ros2_node_list` wrappers run without
   `ROS_DOMAIN_ID`, i.e. they see **domain 0 only**. If the fleet runs on another domain, those
   tools return empty for perfectly healthy nodes. Introspect over SSH with the domain
   exported.
2. **Root-owned nodes, unprivileged subscriber.** Nodes launched under `sudo` publish into
   FastDDS shared-memory segments a normal user cannot open: `topic list` shows the topics,
   `topic echo` returns nothing. **Read with the same privilege you launched with.**
3. **`ros2 node list` lying.** Nodes started in detached `setsid` sessions frequently do not
   appear in graph discovery even while publishing at full rate. An empty `node list` is not
   evidence of a dead node. Trust `topic hz` / `topic echo`, or a diagnostics topic that
   enumerates nodes itself.
4. **Stale discovery after a stop.** Killed nodes leave their topic names in `topic list` for
   minutes. Confirm a stop with `ros2 topic info <t>` showing **zero publishers**, not with the
   name being gone.

## 6. Proof is published data

A capability is "working" when a message arrived. Not when deploy returned ok, not when the
process is in `ps`, not when the topic name appears.

```bash
ros2 topic hz <topic> --once      # or: timeout 5 ros2 topic hz <topic>
ros2 topic echo --once <topic>
```

Report the **rate and a sample payload**. If you launched as root, run these as root too
(failure 2). If the numbers have not arrived yet, say the run is unverified — do not
pre-announce it as live.

## 7. Stopping cleanly

Enumerate first, so you only kill what you started:

```bash
ps -eo pid,ppid,lstart,args | grep -E '<remote>/install|ros2 launch' | grep -v grep
```

Kill the **process tree** (`ros2 launch` spawns children): `SIGTERM` the group, wait a few
seconds, then `SIGKILL` what survives. Then verify by failure 4 above — zero publishers, not
absent names. Leave processes you did not start alone, and name them explicitly in the reply
so the user knows they were spared.

## 8. Never assert what a command would answer

Every wrong claim this skill exists to prevent had the same shape: an explanation built from
assumption when a two-second command was available. Before writing "X is not possible", "Y is
missing", or "Z is hardcoded to", run the command that settles it:

| Claim about to be made | Command that settles it |
|---|---|
| "I have no shell on the board" | `ls <studio data>/ssh/` and one `ssh ... id` |
| "package X is missing on the board" | `python3 -c 'import X'` / `ros2 pkg prefix X` |
| "the tool is hardcoded to <path>" | read the tool schema; `ls` the path on the board |
| "the deploy shipped everything" | the `skipped_deploy_keys` field it just returned |
| "the nodes are dead" | `ros2 topic hz`, not `ros2 node list` |

Board specifics — the host, the domain, the remote directory, which packages are present —
belong in **project memory**, not in this skill. This document is the procedure; it must stay
true for any core+client pair on any board.
