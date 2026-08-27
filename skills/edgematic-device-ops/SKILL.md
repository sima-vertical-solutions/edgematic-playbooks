---
name: edgematic-device-ops
description: Use when the user asks to manage SiMa DevKits or deploy from the Edgematic Studio chat — listing devices, adding/pairing a device, removing a device, checking device status, or deploying a project to a device over SCP or NFS. Covers collecting missing fields inline, reporting device/pairing/deploy errors clearly, and guiding NFS host setup. Do not use for Neat Library C++/Python application development, model compilation, canvas/graph editing, or web-ui React work.
---

# Edgematic Device Ops

## Overview

Manage paired SiMa DevKits and trigger deployments from chat. You do this
through the agent's device tools, which call the Edgematic Studio backend
in-process. The user speaks in natural language ("show my devices", "add
Edge-01 at 192.168.1.10", "deploy to Edge-01"); you translate that into the
right tool call, collecting any missing information first and reporting the
outcome clearly.

## Tools

| Tool | Purpose | Notes |
| --- | --- | --- |
| `list_devices` | List every paired device (newest first) | Read-only. |
| `add_device` | Pair a DevKit (installs the backend SSH key) | Needs `name`, `host`, `user`, `password` — ask via `ask_user` for any missing field. Requires confirmation. |
| `remove_device` | Unpair a device | `device` = name or id; optional `force` to also drop deploy/run history. Requires confirmation. |
| `get_device_status` | Live status (build / cpu / memory …) for one device | `device` = name or id. |
| `deploy_to_device` | Deploy a built project to a device | `project_id` + `device` (name or id). Transport is auto-selected. |

Full request/response and error-code detail: `references/device-api.md`.

## Workflow

1. **Understand the intent** — list, add, remove, status, or deploy.
2. **Adding a device (see *Adding a device*).** Gather `name`, `host`/IP, `user`,
   and `password` with `ask_user` for any missing field (transport only if the
   user raised it), then call `add_device`. Never invent a host.
3. **Resolve devices by name.** `remove_device`, `get_device_status`, and
   `deploy_to_device` accept a device *name* or *id* in the `device` field, so
   you can pass what the user said ("Edge-01"). If the name is ambiguous or
   unknown, call `list_devices` first and confirm which one.
4. **Confirm the destructive action.** `remove_device` prompts for confirmation
   before running — make sure the device is the one the user means.
5. **Report the result** as a short, formatted summary (device list as a table;
   remove/deploy/status as a one-line confirmation with the device name).

## Adding a device (pairing)

Pairing installs an SSH key using the device password. Collect the details and
pair directly from chat:

1. Gather `name`, `host`/IP, `user`, and `password`, asking with `ask_user` for
   any field the user did not supply (ask about `ssh`/`nfs` transport only if the
   user brings it up — otherwise leave the default). Never invent a host.
2. Call `add_device`. It requires confirmation, so the user approves the pairing
   before it runs.
3. After it succeeds, call `list_devices` to show the new device.

## Key rules

- **Deploy transport (SCP vs NFS) is a property of the device, not a deploy
  option.** There is ONE `deploy_to_device` tool; it automatically uses NFS for
  an NFS-paired device and SCP otherwise. "Deploy via NFS" means "the target
  device is NFS-paired". To change transport, switch it in place with
  `PATCH /devices/{id}` and body `{"transport_kind": "ssh"|"nfs"}` (a no-op when
  it is already on that transport) — do NOT unpair and re-pair, and do not look
  for a transport argument on deploy.
- **A device must be built and paired before deploy.** Deploy fails with a clear
  precondition error if the latest build isn't green or the device isn't paired.
- **Don't ask for permission — but `force: true` is a CHOICE, not a permission.**
  Every gated tool here is already governed by the runtime approval policy, which
  prompts (or doesn't) according to the user's posture, so never stack your own
  "shall I?" on top. A `force: true` retry is different: it is a second, more
  destructive call the user did not ask for (it takes a DevKit away from another
  Edgematic instance, or drops deploy/run history). Report the error, offer the
  forced retry as an option, and let the user decide — that is choosing between
  real alternatives, which stays your job under every posture.

## Error handling

Every tool surfaces a typed error `{code, message}`. Relay it clearly and, where
useful, suggest the next step. Do not paraphrase away the actionable detail.

| Error code | Meaning | What to tell the user |
| --- | --- | --- |
| `device_unreachable` | Device offline / TCP handshake failed | Device is offline — check it's powered on and on the network, then retry. |
| `device_pairing_failed` | SSH bootstrap failed (usually wrong password) | Pairing failed — likely wrong credentials; re-enter the username/password. |
| `device_already_exists` | Host already paired | That host is already paired — no action needed (or remove it first). |
| `device_in_use_by_other` | DevKit claimed by another Edgematic instance | In use by another instance. Report it and OFFER the `force: true` retry — never take it over on your own initiative. |
| `nfs_host_setup_required` | NFS chosen but no workspace mounted | Surface the message **verbatim** — it contains the exact `sima-cli sdk setup --devkit <ip>` command to run on the host. See `references/nfs-setup.md`. |
| `nfs_workspace_mismatch` | Mounted, but wrong workspace | Operator/config issue — the mounted workspace isn't the one Studio writes to. |
| `nfs_unavailable` | NFS device left the LAN at deploy | Device is off the shared network; offer to switch it to SCP and retry. |
| `device_in_use` | Removing a device with deploy/run history | Removing it also drops that history — offer the `force: true` retry and let the user pick. |
| `project_not_built` / `device_not_paired` | Deploy precondition unmet | Build the project first / pair the device first, then deploy. |

## Boundaries

- Do not edit device credentials via chat — to change them, remove the device
  and add it again (password re-entered when adding).
- No bulk operations (e.g. "remove all devices") — act on one device at a time.
- Do not discover devices via chat — pairing is by explicit host/IP.
- This skill is about *operating* devices, not building applications or editing
  the pipeline graph.

## References

- `references/device-api.md` — tools + underlying endpoints, request/response
  shapes, and the full error-code table.
- `references/nfs-setup.md` — the NFS host-setup contract and the exact
  instructions to surface when NFS isn't configured.
