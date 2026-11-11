# Camera-free Apple lifecycle and recovery, 11 November 2026

Progress toward [#45](https://github.com/Olli0103/unifi-protect-local-ai/issues/45)
and [#24](https://github.com/Olli0103/unifi-protect-local-ai/issues/24).
Neither issue is closed by these observations.

## Qualified inputs

Host operator source: `3ec262213767233e017b40eac1dd8e3d16de414a`,
including the exact Protect 7.4.96 inventory qualification and unordered,
unique-name environment comparison. Apple container 1.6.1, Linux ARM64 guest.
The retained immutable guest image was built from
`e8cbb6acbeb6129ec0b96b77bee97850ed3b176b`; all 181 installed Python
modules were byte-compared with that source in the initial lifecycle run.
The two subsequent fixes are host-only and are not claimed to be in that image.

One separately prepared, persistent, unadopted slot had no paired streams,
model mount or inference configuration. It used an administrator-installed,
root-owned PF helper and exact one-slot policy. The ordinary caller used
`sudo -n`; the password cache was invalidated before the recovery matrix.
No helper, policy, camera, provider or production service was changed.

Private identities, addresses, certificates, controller responses and action
journals are retained outside this repository. This record contains no
installation commands or usable private settings.

## Initial actual lifecycle

The normal operator created and started its slot, then performed an idempotent
read-back, stop and restart. Its guest address changed while the persistent
identity, certificate pin and configuration stayed the same; the PF mapping
followed the newly observed guest. TLS own-CA/leaf-pin, configuration revision
and runtime health were read back. The slot remained unadopted.

Actual native creation first exposed reordered image environment entries.
The old comparison treated ordering as a configuration change. The host fix
compares unique names and exact values; duplicates, invalid names and changed
values remain refused. The failed create receipt was preserved and positively
reconciled before retry. No receipt was manually rewritten to permit a start.

## Additional bundled recovery matrix

These are real container/PF operations with deliberate faults injected into the
unprivileged caller, **not** a claim of physical power-loss qualification.

| Case | Observation |
| --- | --- |
| Host preflight refusal | Actor refused before start; rollback receipt had zero daemon actions. Existing stopped slot and identity retained. |
| Unhealthy runtime read-back | Actual start and PF mapping, followed by injected unhealthy responses. Actor removed only its own mapping and stopped only its own newly started container. All four action postconditions observed. |
| Lost PF apply acknowledgement | Mapping was actually applied, then the caller deliberately lost the acknowledgement. Receipt stayed uncertain; another apply was refused without changing that receipt. |
| Explicit settlement | Real PF verification and pinned health positively observed the requested state. Settlement performed zero daemon mutations and retained the original failure. No blind mutation retry. |
| Reuse after recovery | A subsequent ordinary apply and idempotent no-op succeeded. Final owned mapping removal and container stop were independently observed. Identity/configuration hashes still matched the initial values. |

The same prepared test identity and bounded installed permission were reused
throughout. No new administrator prompt was needed.

## Production comparison and limits

Fresh authenticated controller reads before and after the recovery matrix
matched on the selected projection: four preexisting adopted/connected Ports,
their nine pairing strings, one connected Key, and eleven camera identities and
connection states. This is a projection comparison, not a claim that every
controller field or counter is unchanged. The own discovered unadopted slot is
excluded from that preexisting-production comparison and reported separately.

Final state: test container stopped, own PF mapping removed, private identity
and installed test permission retained for reuse.

Still unqualified: host reboot/autostart and alias persistence; adopted
controller traffic; extra slots/camera additions and removals; recording
playback/continuity; NAS creation/removal; whole-host restore, power loss,
disk-full recovery, model quality and long-duration operation. No native
camera, face, ONVIF or release acceptance is inferred from this matrix.

This is same-agent execution evidence, not an independent human review.
