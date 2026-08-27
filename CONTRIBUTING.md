# Contributing to Edgematic Playbooks

This repository holds the coding-agent skills that ship with Edgematic Studio.
A skill is prose an agent reads mid-task, so the bar is the same as for a public
API: unambiguous, current, and free of anything that only works on the author's
machine.

## Skill Layout

Every skill lives under `skills/<skill-id>/`.

Required:

- `SKILL.md` — the body the agent reads
- `playbook.yml` — the install manifest

Optional:

- `references/` — supporting documents the skill links to, read on demand
- `agents/openai.yaml` — per-agent interface metadata (display name, short
  description, default prompt)

Use a `kebab-case` id prefixed with `edgematic-`, and keep three names in
agreement: the directory name, `playbook.yml`'s `id`, and `SKILL.md`'s
frontmatter `name`. `sima-cli` derives the installed skill id from the manifest
and installs into `<agent skills home>/<id>/`, so a mismatch installs a skill
under a name the Studio agent was never told about.

## SKILL.md

Open with YAML frontmatter carrying `name` and `description`, then the body:

```markdown
---
name: edgematic-device-ops
description: Use when pairing or managing SiMa DevKits from the Edgematic Studio chat — listing, adding, or removing devices, checking live status, or deploying over SCP or NFS. Do not use for model compilation or Neat Library application development.
---

# Edgematic Device Ops

## Overview
...
```

The `description` is the routing signal — it is how an agent decides whether to
open this skill at all. Write it as *when to use this*, and state what it is
**not** for; overlapping descriptions across skills are what make an agent read
the wrong one. Keep it to a single sentence or two.

Body rules:

- Lead with the workflow, in the order the agent must perform it.
- Name real endpoints and real tools. A route that no longer exists costs the
  agent a wasted round, or worse returns the SPA fallback's `200` with HTML and
  reads as success.
- Only name agent tools the Studio MCP bridge actually exposes. A skill that
  tells the model to call an unexposed tool sends the CLI providers into a
  `-32601` transport error.
- No local absolute paths, no hardcoded board IPs, RTSP hosts, or ports beyond
  the documented defaults, and no credentials.
- Push long tables and full schemas into `references/` and link them. The body
  is re-read often; the references are not.
- Use the official product names: Edgematic Studio, Neat Library, Neat
  Development Environment, Model Compiler, LLiMa.

## playbook.yml

```yaml
id: edgematic-device-ops
name: Edgematic Device Ops
version: 0.1.0
agents: [codex, claude]
description: Manage SiMa DevKits and deploy pipelines from the Edgematic Studio chat — list, add (pair), and remove devices, check live device status, and deploy over SCP or NFS.
compatibility:
  env_types: [host, sdk]
  min_cli_version: 2.1.0
```

- `agents` must be a subset of `[codex, claude]` — those are the only agents
  `sima-cli` installs for. A skill targeting neither fails to install.
- `compatibility.env_types` gates the skill by environment. A skill outside the
  current environment is skipped silently, not reported as an error, so widen it
  deliberately.
- Bump `version` when the body changes materially. `sima-cli playbooks list`
  shows it beside the upstream commit.

## Repository Root

Do not add `SKILL.md`, `AGENTS.md`, `playbook.yml`, `playbook.yaml`,
`skill.yaml`, `rule.yaml`, or `manifest.json` at the repository root, or inside
any directory that is not itself a skill.

`sima-cli` treats the first directory holding one of those files as a single
playbook root and stops descending. One at the root would install this whole
repository as one giant skill and every real skill would disappear from the
install. `README.md`, `LICENSE`, and `CONTRIBUTING.md` are safe.

## Validating a Change Locally

Run the structural checks first — same script CI runs, no dependencies:

```bash
python3 .github/scripts/validate_skills.py
```

It checks that every skill has a `SKILL.md` and a `playbook.yml`, that the id,
directory name and frontmatter `name` agree, that `agents` lists both `codex` and
`claude`, and that no skill-root marker has appeared at the repository root.

Then install from the working tree into throwaway homes, so a broken draft cannot
overwrite the skills you actually use:

```bash
export SIMA_CLI_HOME=$(mktemp -d) CLAUDE_HOME=$(mktemp -d) CODEX_HOME=$(mktemp -d)
sima-cli playbooks install ./skills/edgematic-device-ops --force
sima-cli playbooks list
```

Check the install summary: `detected` counts the skills found, `valid` the ones
that passed validation, and `discarded` the ones dropped — a non-zero
`discarded` prints the reason, most often malformed YAML frontmatter. Then read
the installed copy under `$CLAUDE_HOME/skills/<id>/` and confirm the files you
expected are there.

To validate the whole repository the way the bundle installer does:

```bash
sima-cli playbooks install . --force
```

## What CI Cannot Check Here

`validate_skills.py` checks the *shape* of a skill. It cannot check the two
things most likely to be wrong in the prose:

- that every agent tool a skill names is one the Studio MCP bridge exposes — a
  skill naming an unexposed tool sends the CLI providers into a `-32601`
  transport error
- that every endpoint a skill documents still exists — a dead route sends the
  model to a 404, or worse to the SPA fallback's `200`-with-HTML, which reads as
  success

Both need Studio's live tool catalog and OpenAPI document, which live in the
`edgematic-studio` repository. Its backend suite checks this repo out and runs
those two tests against it on every run, so a skill that names a stale tool or
route fails **there**, not here. Expect that signal to arrive from the Studio
side, and say in your pull request which Studio version the change tracks.

## Pull Requests

Title the pull request with the Jira key: `VP-1234: <one sentence>`. Keep one
skill's change per pull request where practical, and say in the body which
Studio version the change tracks.
