# Reviewed interface retirements — 12 November 2026

These are removals from the unmerged branch, not changes to deployed devices. They do not remove historical Git evidence or grant legal approval.

## Diagnostic-only names

The following 13 names occurred only in fixed-name diagnostic classification tables. They had no functional handler and were absent from the owner’s currently installed Protect backend. Their removal changes named counters to the existing bounded unknown/fingerprint path; unsupported-command result codes and active handlers remain unchanged.

- `wire_atom::7968/anything`
- `wire_atom::7968/vlm_inference`
- `wire_atom:ChangeAvclientEventSettings`
- `wire_atom:ChangeEventSettings`
- `wire_atom:GetAvclientState`
- `wire_atom:GetFeatures`
- `wire_atom:GetIspSettings`
- `wire_atom:GetUiStreamPoints`
- `wire_atom:GetVideoSettings`
- `wire_atom:UpdateFeatureFlags`
- `wire_atom:getDbCredential`
- `wire_atom:setClientCertificate`
- `wire_atom:setDbCredential`

## Unused optional fields

- `tagHierarchy`: the query path did not use the optional flag to change results. Its special validation is removed rather than inventing semantics for the flag. Required query text is still validated; existing model and other opaque query metadata remain accepted without interpretation by this helper.
- `failed`: the description-result helper accepted this optional extension, but production result producers did not emit it. Standard description payloads are unchanged; the unobserved extension is now rejected.

Tests cover known positive requests/results, preserved model/opaque query metadata, rejection of the unsupported result extension, unsupported-command status, diagnostic privacy, a closed fingerprint window and bounded fingerprints in an authorized window. This does not establish new native execution or compatibility with every historical controller.

The remaining unsupported active paths and contexts are retained as `needs_observation`; working features were not deleted solely to reduce the count.

See the [structured retirement record](interface-retirements-20261112.json).
