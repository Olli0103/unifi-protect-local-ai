# Native verifier interface attribution

## Scope

Reviewed on 12 November 2026. This record resolves two exact interface atoms using the owner's **3 November Protect 7.3.74** interoperability receipts and the recovered immutable **project** image deployed during those observations. It does not claim a fresh successful verifier request on Protect 7.4.96.

The [machine-readable evidence](interface-native-reverification-20261112.json) contains the source revision, module/function hashes, original receipt digests, safe aggregate results and limitations. The earlier [native object-routing acceptance record](native-object-routing-acceptance-20261103.json) is retained unchanged and hash-bound by the new record.

Machine-readable record SHA-256: `764b542b760b06c54181effb54535578fa3443349a887ea5b9915edf74721e1c`.

## Attributed facts

| Interface atom | Evidence |
| --- | --- |
| `:7788/v1/models/second_verifier_mlabel/inference` | The deployed worker's sole call to its reverification normalizer is guarded by equality with this exact target. Three completed native jobs use that normalizer's `reverify` operation and camera/event-derived identity. Each was joined to its exact native event, not merely to a nearby timestamp. |
| `/internal/aiprocessors/reverification` | The same normalizer rejects every other callback path. The sender posts to the admitted callback with redirects disabled and records the response status. All three matched jobs recorded HTTP 200; the corresponding native object confirmations/retypings persisted across two separate reads. |

## Byte and observation chain

1. The original installed-constructor receipt recorded a SHA-256 digest of the deployed `_normalize_reverification` method, separately from the native job/event receipts.
2. The original 3 November participant record and process read-back identify the same immutable project image. The process started on 2 November and remained running without a restart through the subsequent 3 November read-back.
3. On 12 November that exact image was still available. Only the project's own `worker.py` and `device.py` were copied from a stopped, network-disabled probe container. The probe was never started and was removed afterward; all 80 existing container projections were unchanged.
4. Both copied modules are byte-identical to the public project revision recorded by the image. The recovered normalizer's source-segment digest exactly matches the original installed-constructor digest. Its exact-target caller, callback-path guard, job identity constructor and callback sender were reviewed together.
5. The original three completed job receipts recorded HTTP 200. The original two native detail reads joined all three jobs by `SHA256(reverification:camera:event)`, checked exact event identity and thumbnail clocks, and observed one confirmation and two retypings. The second read was 73.914 seconds later. The collectors performed no setting writes or model requests.

This is **derived exact-path attribution** from actual historical observations plus deployed-byte guards, not a retained raw packet capture. Project constants alone, a generic health check, or an unrelated successful callback would not be sufficient. Private original receipts remain owner-retained and are identified only by digests in the public summary; external readers cannot independently replay that historical installation from this record.

## Separate 12 November test and cleanup

The owner-authorized synthetic camera/Port test on Protect 7.4.96 was repaired and admitted one artificial native event. No verifier job was observed in the bounded worker observation windows. That outcome does **not** establish either verifier path and is not used to close these facts.

Both temporary reservations, both synthetic native device records and both running fixture containers were removed. Fresh read-back confirmed Discovery off, the original eleven cameras, one Key and five Ports, unchanged selected identities/pairings/settings, all three original network configurations and the pre-existing users' fixed-IP/binding flags. All 80 pre-existing containers were unchanged. An automatically relearned, unreserved Network client-history row and the artificial event may remain; neither is an active test device or reservation. No historical event was replayed.

## Limits

No manufacturer AI Key/AI Port firmware, binaries, disassemblies or extracted functions were opened for this attribution. The recovered image is the independently authored project's image, not a manufacturer image. No media, credentials, raw requests, camera/event/job identities or query values are published.

This closes the two remaining **scoped interface-source observations**. It does not prove complete semantic provenance, classifier accuracy, hardware parity, clean-room development, rights approval, container-image compliance or public release clearance. Historical artifact rights/access records and the other legal/release work remain separate.
