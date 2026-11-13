# Private staging pre-push repair

The immutable alpha source and `v0.1.0a1` tag remain at `a3da9c21715dade37fbe3a25529fa85fd17dc430`. This is a separate execution-policy repair, not new source approval or final release approval.

## Observed run

Recovery run `43464180864`, executing policy `39922d0ab2202ad2622f3fcc8ddd7284a4143b5c`, successfully qualified the source, adopted the original draft `444049704` without changing it, and produced validated source delivery. The full eight-job graph and full failure logs were retained. Both native installation builds passed their build step; both failed at the pre-push image-intent check. Registry login, pushes, image attestations, assembly and publication were skipped. Cleanup succeeded. The package job created a provenance attestation, then failed its SBOM attestation. No complete signed candidate exists; do not describe this as a run with no signing effects.

The package producer uses CycloneDX 7.4.0 `--output-reproducible`, whose implementation removes `serial_number`. The pinned actions/attest implementation requires a non-empty CycloneDX `serialNumber` and `specVersion`. The repair retains the normal schema-validated producer output with explicit CycloneDX 1.6 and validates the required fields before signing. Both clean package builds and their byte comparison remain unchanged; a reproducible SBOM is not asserted.

The native failures exposed only `release_candidate_unavailable`. Their exact underlying causes remain unproved. The repair emits bounded fixed refusal codes from the paired validators and a fixed execution stage, never arbitrary exception/provider text. Existing retained real-size native inventories pass a separate local handoff fixture; this is not a reproduction of the failed run's lost current inventory or a claim that the live native issue is fixed.

## Deliberate continuation, not a rerun

`recovery_preflight_run` is empty by default. Using it requires the policy-side `docs/legal/recovery-prepush-reconciliation.json`, exact original source/draft/run identities, exact previous policy and workflow bytes, a fresh complete identical job-and-step graph, positive failed pre-push guards and skipped registry operations, successful cleanup, a terminal single attempt, and complete dispatch history excluding all other intervening activity. The evidence record alone is not sufficient: live API metadata must still agree. Any rerun, missing step/job, later dispatch, graph change or unknown effect refuses continuation. Another failed continuation is not automatically covered by this record.

The version-2 reconciliation record stores SHA-256 of each exact UTF-8 provider step name rather than raw names, because GitHub expands runner paths in some names. Fresh live names are hashed by the same canonical projection before comparison; every step number, status, conclusion and identity remains bound. Renamed steps, malformed digests, raw names in records and legacy records are refused. Package environment-leak checks remain unchanged.

The original empty-draft check, source and policy seven-job qualification, owner-only release-stage approval, private-package checks, create-only intents, signed byte checks, and separate final release environment remain required. No draft/tag deletion or replacement, no broad retry and no bypass of final release approval is added.

The public package provenance from the failed run is retained rather than erased. Original source collection `43394238336` / `approved-upstream-sources-e97fc8ea` remains the owner-pinned input; no replacement originals are introduced.
