# NFS setup reference

## Who sets up NFS

The **host** sets up NFS, outside the container — Studio never does. Studio runs
*inside* the Neat SDK container with no host privileges and no `nfsd` kernel, so
it can only **verify** that NFS is ready and then use the already-mounted folder.

One host command arranges everything:

```bash
# on the HOST, before entering the container:
sima-cli sdk setup --devkit <devkit-ip>     # or: --devkit auto
sima-cli sdk neat                            # enter the container → Studio runs here
```

`sima-cli sdk setup --devkit` installs the host NFS server, writes the export,
and mounts it on the DevKit at `/workspace`. Plain `sima-cli sdk setup` (without
`--devkit`) configures **no** NFS — the `--devkit <ip>` (or `--devkit auto`) flag
is required for the NFS transport.

## What you do when NFS isn't ready

When a user pairs (or deploys to) an NFS device that isn't set up, the tool
returns a 422:

- **`nfs_host_setup_required`** — no workspace mounted on the DevKit. The
  error's `message` already contains the exact, copy-paste-ready command with the
  real IP, e.g. `sima-cli sdk setup --devkit 192.168.91.131`. **Surface that
  message verbatim** and tell the user to run it on the host (outside the
  container), then retry pairing.
- **`nfs_workspace_mismatch`** — a workspace is mounted, but it is not the one
  Studio writes to. This is an operator/config issue, not something re-pairing
  fixes; explain that the mounted workspace must be the SDK `/workspace` Studio
  uses.

## At deploy time

If an NFS-paired device has left the shared LAN, deploy returns
**`nfs_unavailable`** (503). Tell the user the device is off the network and
offer to switch it to the SCP transport and retry (the error carries a
switch-to-SSH fix hint).

## Transport is a device property

NFS vs SCP is chosen at pairing time (`transport_kind`) and stored on the device.
`deploy_to_device` auto-selects it — there is no per-deploy transport option. To
change transport, `PATCH /devices/{id}` with `{"transport_kind": "ssh"|"nfs"}`;
the switch is in place and re-pairing is not required.
