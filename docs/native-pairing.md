# Preserve camera settings during native AI Port pairing

Protect 7.3.74 and 7.4.96 can reset a camera's selected smart-object/audio types
and add a zone class when it is re-paired. Recording remaining active is not
proof that detection settings survived. This is controller behavior observed
with an existing G5 camera, not an instruction to enable new camera processing.

The explicit host operator `python -m aikey.native_pairing` snapshots and verifies
one already authorized G3–G5 camera transition. It is separate from the Admin
site's **local capture** allowlist: the site still receives no native write
credentials, and this command does not add local processing permissions, adopt
a processor, move a camera between ports, change a model or trigger a test alarm.
No ONVIF or AI-series admission is inferred.

## Scope and prerequisites

- Select the exact connected camera and adopted/connected Port, and retain their
  original pairings. A camera owned by another Port, unknown version, full Port,
  stopped recording or ambiguous bootstrap is refused before a write.
- Own an exclusive maintenance window for that camera. The native API has no
  demonstrated atomic compare-and-set operation; repeated fresh comparisons do
  not lock out another Protect user. Do not edit settings in another client
  during the operation. This is not a general concurrency guarantee.
- Supply private native-account username/password files with actual permission
  for this camera operation and the existing reviewed HTTPS web trust/leaf files.
  An Integration API key, browser cookie export or device management token is not
  a replacement. The standalone CLI does not provide interactive MFA enrollment;
  an authentication challenge/refusal stops rather than borrowing a browser jar.
- Create one private, canonical **persistent authority directory per controller**
  outside device mounts. Reuse it for subsequent operations; never choose a new
  directory to bypass an unresolved attempt. Its lock serializes cooperating
  invocations. Preserve its private snapshots/history; none belong in Git.

## Preview, apply and readback

Use real private paths and the selected native IDs, not these placeholders:

```sh
python -m aikey.native_pairing \
  --controller PRIVATE_CONTROLLER_IPV4 \
  --camera SELECTED_CAMERA_ID --port SELECTED_PORT_ID --target paired \
  --username-file /private/native-user --password-file /private/native-password \
  --trust-file /private/protect-web-trust.json --cert-file /private/protect-web-leaf.pem \
  --state-dir /private/pairing-authority
```

Without `--apply`, this only observes and reports a preview revision or unchanged
state. Add `--apply --exclusive-camera-maintenance` for the explicit transition.
Use `--target unpaired` for a removal from that same Port. Nothing silently
unpairs a camera to make a new pairing fit. An already satisfied target is a
no-write result, not a new adoption or lifecycle test.

Before the first effect the journal records the controller-origin/certificate
binding, original protected configuration, expected pairing delta and operation
identity. Each effect is durably requested before network I/O. HTTP 200 or 207 is
not effect evidence: a fresh complete bootstrap must show the exact expected
pairing/configuration. Only the observed empty object/audio-list reset and an
unchanged or added `face` zone class can be repaired. The guard restores only
`smartDetectSettings` and `smartDetectZones`; unrelated settings, geometry,
recording, another camera or another Port changing causes refusal. A second
fresh comparison precedes repair, followed by exact final readback and active
recording/connection checks. Supported raw versions are deliberately exact.

Successful older operations are archived, not overwritten or erased. Unknown
effects, cancellation, lost responses, failed restore or changed settings leave
an unresolved journal and block another apply. Keep the actual state and inspect
it; do not delete the journal, blindly rerun the request, restore an old device
state or relax the controller pin.

`--reconcile` uses the same identity/target/credential arguments and performs
**zero native writes**. It can accept an already verified expected state or a
prepared no-effect state; the original failure remains recorded. It does not
finish a partial settings repair. That needs separately reviewed recovery of
the retained exact snapshot, not automatic replay permission.

## Evidence boundary

The source tests bundle the actual pinned TLS paths, reset restoration, successful
unpair/no-op, concurrent-drift refusal, cancellation, malformed/private records,
wrong-controller binding, redirects, false acknowledgements and lost responses.
The real 7.4.96 camera test also ran this source transaction engine through the
existing authorized browser session, with a separate credential-free TLS pin
check. No cookies, native credentials, footage or private IDs are published.
That test adapter is distinct from the standalone credential-file transport.

[Native lifecycle evidence and precise limits](evidence/native-pairing-20261111.md)
records the original reset and guarded recovery separately. The native Protect
UI by itself still resets settings; this operator does not patch the controller.
A successful settings transaction is not universal onboard-class accuracy,
continuous video at every timestamp, a camera firmware update test or an
unqualified parity claim for all Protect versions.
