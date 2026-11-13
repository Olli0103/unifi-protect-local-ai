# Private candidate package-metadata credential repair

The original v0.1.0a1 source and tag remain a3da9c21715dade37fbe3a25529fa85fd17dc430. The original private draft remains 444049704. No public release, final environment approval, image visibility change, rerun or new release dispatch is part of this repair.

Run 43483598001 passed both native image intent checks and both registry logins. Both push-image steps failed with the fixed code `release_metadata_unavailable`. Neither complete staged-image handoffs nor a complete candidate were produced. The previous wrapper discarded the HTTP status; this record does not invent a 403, claim that login was a push, or infer historical zero registry effects from a failed step. The reviewed third graph is pinned in `docs/legal/recovery-package-read.json`, chained to the two previous exact graphs. Unknown later dispatches and reruns remain rejected.

## Required credential

GitHub's package REST documentation requires a classic PAT (or supported OAuth token) with `read:packages` for package metadata. The managed repository OAuth identity currently reports `gist`, `read:org`, `repo` and `workflow`, not `read:packages`. The current workflow credential did not produce the required positive package catalogue observation.

Create a short-lived classic PAT for Olli0103 with only `read:packages`, then store it directly in this repository's Actions secrets as `RELEASE_PACKAGES_READ_TOKEN`. No token belongs in an issue, PR, chat, file or source tree. The repair does not generate, extract or transfer a credential.

The separate package-read transport authenticates `/user` and requires Olli0103's numeric owner identity before reading the complete container package catalogue. It never falls back to the workflow credential, never sends the read credential to another host or write command, and reports only fixed error codes and bounded HTTP status numbers. The workflow token remains the registry login/write and repository credential. Native build, scanner and cleanup shells and signing actions do not receive the new secret.

A new read-only qualification step checks catalogue access before private staging or native builds. Absence is accepted only from a successful complete owner-authenticated catalogue; existing destinations must still be private and linked to this repository. All immediate pre-/post-push privacy checks remain.

## Qualification

319 affected release tests passed, including exact three-run graph replay, unknown-effect rejection, missing/wrong-owner credentials, host/command restrictions, fixed diagnostics and workflow wiring. These are fixture checks, not proof that a real PAT exists or that private staging succeeded. A fresh exact-head CI and final independent gate remain required before merge. The final candidate and public approval remain separate.

Documentation: https://docs.github.com/en/rest/packages/packages
