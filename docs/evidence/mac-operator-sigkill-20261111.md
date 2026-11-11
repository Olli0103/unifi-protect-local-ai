# Native Mac operator death and explicit settlement

Progress toward #45/#24; neither broad issue is completed by this case.
Qualified host source: `c92686a2916afaa656f6500d63a000563d1ea9a2`.
The already installed immutable guest image remains the earlier qualified
181-module build; this run does not claim to deploy newer host modules inside it.

## Actual case

Only the existing, empty, unadopted test slot was selected. Its installed
root-owned fixed policy was not expanded. The normal source actor fetched
fresh pinned inventory, started that guest and called its actual privileged PF
adapter. Immediately after the helper returned verified success, but before the
actor could publish its acknowledgement, the process sent itself **SIGKILL**.
The parent collected return code -9; this is not a mocked exception or lost
stdout substituted for process death.

The original durable receipt remained `prepared`, ending in
`transport_apply/requested`; the activation reservation remained prepared.
Native container inspection observed the guest running. Exact image/config,
identity files and the operation-owned PF mapping matched. A normal `--apply`
returned `apple_pending_reconciliation_required`, without changing the original
receipt or issuing a new daemon mutation.

The ordinary source `--reconcile` then verified the actual mapping, fresh
own-CA/exact-leaf health, activation and identity. It returned `all_running`
without a container create/start/stop. The original requested action and
operation identity remained in its settled receipt. The killed process never
caught an application exception, so its `failure` was still null: that unknown
is preserved rather than inventing an exception history. The separate parent
signal/kill-point evidence supplies the observed death.

After positive settlement an explicitly journalled scoped cleanup removed only
that mapping and stopped only that slot. A further ordinary apply, pinned
inspect and normal stop all passed. Original private state-file bytes were
unchanged, apart from the expected activation reservation lifecycle. Three
other Mac container configurations/states were unchanged. The final own slot
is stopped, with no PF mapping, no adoption, no camera or model.

## Production and limitations

Fresh Protect reads before/after retain the exact four production Ports, one
Key, nine pairings and eleven cameras' selected recording/detection/zone fields.
The whole-inventory comparison initially differed because discovery re-added
the exact own test MAC. A separate exact-MAC projection confirmed that extra
row is disconnected, unadopted and has zero pairings; excluding only that row
returns the original production hash. The initial differing observation is
retained, not replaced with a claim that the entire inventory never changed.

A separate 32-MB external HFS+ image was prepared for a bounded ENOSPC case.
macOS refused both mount attempts with `Permission denied`; no test filesystem
was mounted and no permissions were widened. **Disk-full remains untested.**
The initial invalid create syntax and failed mounts are retained separately.

This is one source-operator crash boundary on one empty slot, not physical
power loss, host boot/address persistence, multi-slot scaling/removal, an
adopted-camera continuity test or whole-host restore. It uses the same agent's
execution; it is not independent human review. All private receipts and the
unmounted test image remain outside the repository on nonsynchronized external
storage. No productive service, camera setting or iCloud project path changed.
