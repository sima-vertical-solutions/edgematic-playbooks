# Device API reference

The agent device tools call these backend surfaces in-process (never over HTTP).
This reference documents the underlying contract so you know exactly what each
tool does, what it needs, and how it can fail.

## Device model

A `Device` row carries: `id` (UUID), `name`, `host` (IP or hostname),
`ssh_user`, `pubkey_fingerprint`, `status` (`paired` / `unreachable` /
`unauthenticated`), `transport_kind` (`ssh` or `nfs`, default `ssh`),
`last_reachable_at`, `paired_at`, `created_at`, `updated_at`. A device **never**
carries a password — the password is used once at pairing and discarded.

## Tools → backend

### `list_devices`
- Backing: `GET /devices` → `{ devices: [Device] }`, newest-first by `paired_at`.
- Params: none. Read-only.

### `add_device`
- Backing: `POST /devices` (pairing). Params: `name`, `host`, `user`,
  `password` (all required); `transport_kind` (`ssh`|`nfs`, default `ssh`);
  `force` (default `false`).
- Sequence: duplicate-host guard → cross-instance owner-marker guard (unless
  `force`) → SSH key install (`ssh-copy-id` via `sshpass`) → NFS readiness check
  when `transport_kind == nfs` → owner claim → persist. Returns
  `{ device, pubkey_fingerprint }`.
- Errors: `invalid_device_host` / `invalid_device_name` (400),
  `device_already_exists` / `device_in_use_by_other` (409),
  `nfs_host_setup_required` / `nfs_workspace_mismatch` (422),
  `device_pairing_failed` (502), `device_unreachable` (503).

### `remove_device`
- Backing: `DELETE /devices/{id}` (with `?force=`). Params: `device` (name or
  id); `force` (default `false`). Best-effort clears the on-device owner marker,
  then deletes the row. Requires confirmation (destructive).
- Errors: `device_not_found` (404), `device_in_use` (409 — has deploy/run
  history; retry with `force: true`).

### `get_device_status`
- Backing: `GET /devices/{id}/status`. Params: `device` (name or id). Live
  one-shot SSH read of build / cpu / memory (+ thermal / disk / uptime when
  available). Does not touch the database.
- Errors: `device_not_found` (404), `device_unreachable` (503).

### `deploy_to_device`
- Backing: `POST /projects/{id}/deploy`. Params: `project_id` (UUID), `device`
  (name or id). Transport is auto-selected from the device's `transport_kind`:
  - **NFS**: no copy — the project already lives under the shared exported
    workspace the DevKit mounts; the tool records the remote dir after a
    reachability probe.
  - **SSH**: tar the workspace → scp → remote extract under
    `/data/simaai/applications/<project-id>/`.
- Preconditions: project exists, device exists + `paired`, latest build green.
- Errors: `project_not_found` / `device_not_found` (404),
  `device_not_paired` / `project_not_built` (409), `deploy_failed` (502),
  `device_unreachable` (503), `nfs_unavailable` (503 — NFS device left the LAN;
  offers a switch-to-SSH fix).

## Name resolution

`remove_device`, `get_device_status`, and `deploy_to_device` accept the `device`
field as EITHER a UUID or a device name. A name is resolved against the current
device list; an unknown name returns `device_not_found`. When a name is
ambiguous or unknown, call `list_devices` and confirm with the user.

## Error envelope

All errors follow `{ "error": { "code": "snake_case_code", "message": "…" } }`.
Relay the `code`/`message` to the user; for `nfs_host_setup_required` surface the
`message` verbatim (it embeds the ready-to-run host command).
