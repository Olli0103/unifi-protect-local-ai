# Native Mac adoption and current adopted-state archive restore

Bounded progress for [#45](https://github.com/Olli0103/unifi-protect-local-ai/issues/45)
and [#24](https://github.com/Olli0103/unifi-protect-local-ai/issues/24),
not completion of their multi-slot, camera or full-host requirements.

## Subject and result

On Apple Container **1.6.1** and Protect **7.4.96**, one camera-free test AI Port
completed genuine native enrollment, a normal configuration-only container
recreation, and a cold archive restore into a separate state directory.
The newly accepted native record remained the same through the successful
recreation and restore. It was adopted, provisioned and connected during a
fresh uncached controller read while the restored guest was running.

Host operator source: `e1970e4c214fb45a16e2307d4eeda26fc5ddde07`.
The guest retained the previously qualified **181-module** image built from
`e8cbb6acbeb6129ec0b96b77bee97850ed3b176b`; this is not an image rebuild,
a signed release or a claim that its source equals the host operator tree.

The installed helper's one-slot address/name/certificate perimeter was not
expanded. All ordinary lifecycle and restore starts used the existing actor
and its fixed PF helper without another administrator dialog. Root-private
policy bytes were not independently readable by the unprivileged operator;
this is not a byte-level attestation of that private file.

## Retained failed enrollment and exact reset scope

The first regular native Adopt action was attempted with the passive
five-field configuration. Protect displayed adoption, but local token-confirmed
adoption was absent. Adding the documented bounded factory-enrollment window
after that attempt produced a connected/provisioned native display and a
credential rotation, still without genuine saved local adoption. Neither
observation is counted as successful enrollment. Clean-transition checks
refused before mutation; no adopted marker, peer check or pin was bypassed.

The owner then explicitly approved removal/reset of **only that incomplete,
owned, camera-free test registration**. Its guest was absent and pairings were
zero. An uncached controller read proved the old record absent before any
state reset. Failed state and credential bytes were archived and retained.
This approval did not authorize forgetting production processors or later
forgetting the genuinely accepted test registration.

A fresh documented factory window was present **before** the next first
native Adopt. The MAC, certificate, controller pin and fixed address stayed
unchanged, but the initial failed native record was replaced. Management-token
pending state, pinned WebSocket confirmation, saved adopted state with pending
token removed, and native adopted/provisioned/connected state jointly passed.
Do not claim that the experiment retained its initial failed native record.

## Ordinary operation without the temporary window

Only the temporary `factory_enrollment_until` setting was removed. The normal
actor recreated the container against the **current adopted state**, not the
pre-enrollment credential snapshot. Local adoption and native readiness passed;
the accepted record and cryptographic identity were unchanged. A private
lifecycle probe's old assumption that the slot must remain unadopted caused
one retained inspection refusal; the probe was corrected to compare actual
saved adoption with source readiness without weakening identity/config/pin
checks. No product behavior or unit tests were added for this harness repair.

## Isolated restore before native cutover

1. Stop only the owned guest and remove only its PF mapping. Cold-archive its
   complete current **11-file** device state, verify the archive and every
   member byte/hash, and separately retain host authority/journal state.
2. Extract into a distinct private directory. Validate configuration, adoption,
   management-credential record, TLS/key pair and exact files with DNS and
   sockets denied before the component check. **Zero network attempts** occurred.
3. Keep the original cold directory unchanged. Only after the isolated check
   passes, remove the stopped original container; never start two copies of
   one device identity.
4. Rebind only the reviewed manifest's state-directory/volume source and
   derived revision. The address, MAC, certificate, image, ordinary
   configuration and fixed helper authority remain unchanged.
5. Start through the normal source actor. Verify actual pinned guest identity,
   local adoption/control connection and a **fresh uncached live controller**
   read before stopping: same accepted native record, adopted/provisioned/
   connected, **zero camera pairings**.
6. Stop normally, remove the owned mapping, and fully verify a new 11-file
   cold backup **after** that final native readback. Update the ordinary private
   starters to the restored current state; retain older archives as historical
   inputs, not as the latest credential set.

Restored files matched the archive before startup. A controller reconnect
changed stored management-credential hash bytes; the username stayed unchanged,
but **effective password equality is unknown**. No plaintext was extracted or
replayed. An unchanged-password claim or restoration of an old credential
snapshot over the accepted identity would be incorrect.

## Final readback and limits

- Owned slot: stopped; its PF mapping removed; genuine adoption retained;
  no paired cameras. The failed old record remains absent.
- Three other Mac container configurations and final states unchanged.
- Original production projection unchanged: **four Ports, one Key, nine
  pairings, eleven cameras' selected recording/detection/zone settings**.
- No production camera/provider/model/index change, new IP/root scope,
  iCloud project write or new public/private-media upload.

This is a camera-free **AI Port device-state** restore, not AI Key/PostgreSQL/
index recovery, paired-camera recording continuity, multi-slot creation/removal,
whole-host/controller restore, alias persistence across boot, physical power
loss, ENOSPC, sustained soak/pilot, or independent human review. The original
compound issue criteria remain open. Private archives, identifiers, credentials,
media and operator paths are excluded from this public evidence.

Sanitized private aggregate SHA-256:
`ca1bea0df2c55c74eea075891251bc7c3dc141dc173d02c4334c85b52e06fd69`.
A digest provides a retained byte identity, not independent human attestation.
