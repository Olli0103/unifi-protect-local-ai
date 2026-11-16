# Default-image alpha distribution review

Scope: [the requested 0.1.0a1 alpha](../alpha-release.md), not a declaration
that all original issue #4 criteria or legal prerequisites are satisfied.

## Historical preparation evidence

The following predates the 2026-11-13 owner decisions and alpha staging attempt.
It remains useful evidence, but does not identify newly staged image bytes.

| Subject | Retained result | Limit |
| --- | --- | --- |
| Project license | Owner selected Apache-2.0; root license and package metadata agree | Does not establish rights of every contributor or firmware artifact |
| Project identity | Independent experimental local AI processor; no Ubiquiti affiliation | Compatibility naming is not manufacturer endorsement |
| Source/package contents | Existing full public-tree/package audits exclude firmware, models, private state/keys/traces/media | Automated content scanning is not protected-expression/ownership review |
| Default image notices | Original installed notices, CPython, native-library and Cryptography Rust material retained and delivered | Scanner SPDX completeness is not license clearance |
| Exact image/source candidates | Four e1970e4 default images mapped to 764 verified source files, 296 component/version pairs, 1,288,871,052 bytes | A named historical subject, not new alpha image bytes or proof of reproducible binary builds |
| Acquisition | Every one of those 764 retained original files has an exact HTTPS source URL, size and SHA-256 | Does not by itself supply recipients with complete corresponding source or establish redistribution approval |
| Native adoption | Actual isolated camera-free token-confirmed Mac adoption/restore recorded | Exact older guest/host subjects are named; not a blanket alpha/platform approval |

See the [source/image review](../source-inventory-review.md),
[third-party inventory](third-party-distribution.md),
[native-library notices](native-library-notices-20261106.json) and
[Cryptography Rust notice evidence](cryptography-rust-components-20261106.json).
The schema-1 `legacy_evidence` and schema-2 migration resets are historical;
they must not be presented as the status of the later owner-reviewed snapshot.
Automated tools do not generate an owner's or lawyer's sign-off.

## Owner-reviewed snapshot and actual staging outcome (2026-11-13)

The reviewed alpha source is `a3da9c21715dade37fbe3a25529fa85fd17dc430`,
tree `2c1995ce09a69d886c3ee9f11e5c3fb2fe437a2f`, public tag `v0.1.0a1`.
The [effective evidence record](release-evidence.json) binds input fingerprint
`ad5ac45a4c12e863241e93f3f1a9fdd422b58a8ddd25f1e3e7b4d152db4499cd`.

| Subject | Actual retained result | Boundary |
| --- | --- | --- |
| Rights, origin and risk | `Olli0103` accepted the bounded WP1/WP2/history/contribution review, license/development declarations and risk decision after 19 answers; all seven effective checks are `verified` | Exact-source preparation decision, not a legal guarantee, clean-room claim or proof of every historical access right |
| Source transition | Owner explicitly accepted the isolated test-fixture correction and resulting fingerprint | Does not approve later documentation, code or workflow changes |
| Source readiness and CI | Both non-audit artifact profiles passed for the reviewed fingerprint; all seven prerequisite main-CI jobs passed for `a3da9c2` | `release_approved` is source readiness, not final publication permission or product acceptance |
| Current image/source mapping | Current main-CI inventories cover four native image subjects; 270 native file comparisons and actual license/source notices passed against the unchanged 764-original-file manifest | Qualification subjects, not signed/staged registry images or binary reproducibility |
| Internal source bundle | Exact-main bundle independently read back: 778 archive members and all 872 project files, including 183 Python modules | Prepared and retained internally; not delivered as public release assets |
| Staging decision | Owner authorized source handoff, tag, signing and private staging; `publication.status` is `verified`; `release-stage` was approved for run `43402688428` | Final candidate publication, final `release` environment and public image visibility remain reserved |
| Actual staging effect | Private draft `444049704` was created with the original run/source marker; reservation then failed with exit 2 | No signed candidate; all downstream source/package/image/assembly/publication jobs skipped; no registry push by this run |
| Public delivery | Tag exists; the private draft has no uploaded assets, only GitHub's automatic source-archive links | No completed signed public release or recipient source/notice delivery through that release |

Retained owner-decision references (private supporting records stay outside Git):

- Preparation decision `owner-approval.json`, SHA-256
  `5734beef9e2919981b60c20593f23e5cd7c9f1691dc4aecfa860c28885c94950`.
- Private-staging authorization `staging-authorization.json`, SHA-256
  `af16bd163ec704cf252698249c8fbb49d0a74e592139c32fe174e5502d7d3dde`.
- Test-only source confirmation `test-transition-owner-confirmation.json`, SHA-256
  `268165786a517933cd1893008759c37cc9461e5d3892ab0102644bf3e9bb98ef`.

The approved upstream manifest is
`e97fc8ea5f02166fe9d7280c7b16dc5f3ceed911077ddb191c7e5cea7d38bdb8`;
its CI artifact is `approved-upstream-sources-e97fc8ea` from run `43394238336`.
The refreshed internal exact-main source archive is 1,343,856,640 bytes,
SHA-256 `361d6ada4626ecfb6e3cb341c4e1a09e71c3397770a0f47284e47f31e6bfb689`.
Its retained `independent-recipient-verification.json` verifies contents, not
public delivery; `current-native-and-notice-verification.json` records the
current image mapping. These are under retained case
`unifi-source-delivery-20261113-main-a3da9c2`.

[Staging run 43402688428](https://github.com/Olli0103/unifi-protect-local-ai/actions/runs/43402688428)
failed in [reserve job 131809304672](https://github.com/Olli0103/unifi-protect-local-ai/actions/runs/43402688428/job/131809304672).
The exact machine-readable refusal was redirected into an ephemeral runner file
and not retained. Its root cause is **undetermined**. Historical draft fields
passing a local production-validator fixture do not prove the earlier API
response or successful reservation. Case `unifi-staging-20261113` retains
`STATUS.md`, `CONTINUATION.json`, `failed-reservation-reconciliation.json`, the
original draft readback and the full failed-job log.

## Signed recovery and public source/package delivery (2026-11-16)

The preceding section describes the original 13 November attempt, not current
release availability. [Run 43920818331](https://github.com/Olli0103/unifi-protect-local-ai/actions/runs/43920818331)
completed on 16 November with unchanged artifact source/tag `a3da9c2` / `v0.1.0a1`
and executing policy `18f0ebd695ceccae861daed8c02aff1eba1aed9c`. It reused the
positively identified original draft `444049704`, without moving the tag,
deleting/recreating the release or adopting failed-run images.

- Fresh native Linux AMD64/ARM64 jobs passed all eight installed-source/state
  cases per architecture, with successful cleanup, inventories and signatures.
- Assembly verified upstream subjects, created separate AI Key/AI Port indices,
  signed the root candidate and passed the actual final consumer against it.
- The owner approved final environment `release`. The original release became
  [public prerelease v0.1.0a1](https://github.com/Olli0103/unifi-protect-local-ai/releases/tag/v0.1.0a1)
  at **18:29:24 UTC**, with 25 uploaded assets and exact size/provider-digest
  readbacks. The corresponding-source part and original notices are now release
  assets, not merely a prepared internal bundle.
- The delivered corresponding-source archive is the unchanged 1,343,856,640-byte
  subject/SHA-256 recorded above. The signed `release.json` SHA-256 is
  `0d7b28aaef155c43277d5129a9fe40369ff58213dc7ab63941f63111e6333eb3`.
  [The alpha record](../alpha-release.md) identifies image digests and checksums.
- Container images remain **private**, with two separate profile indices in one
  existing package under [bounded registry recovery](private-registry-recovery.md).
  No public visibility change or anonymous-pull verification occurred.

The registry incident in run `43865727276` remains a real earlier public phase;
downloads cannot be excluded. Its native cleanups failed, and those failures
remain failures. Its retained version is unchanged; new images/signatures and
cleanup evidence come only from fresh run 43920818331. Neither successful
recovery nor publication erases that incident.

## Remaining gates and successor-source boundary

- Keep the versioned GHCR destination private until a separate owner visibility
  decision. Visibility affects the entire shared package, including its retained
  incident version; verify anonymous pulls only after an authorized change.
- Preserve the successful release, immutable assets and original source tag.
  No attempt-2 rerun, duplicate publication or cleanup of historical evidence is
  authorized by this documentation update.
- Treat these documentation corrections as a new source input, not a retroactive
  edit of the tagged alpha. They invalidate the old fingerprint for a tree that
  includes them. Preserve the existing evidence record and tag; any successor
  release source needs exact-snapshot review, fresh qualification and the
  applicable identity/version decision before staging. No approval is silently
  transferred to it.

The nonblocking `research_record` remains `needs_evidence`: historical
firmware-access permission is not proven and no further firmware analysis is
authorized. No model weights ship; this is not a model-license approval.
The bounded owner rights/source decisions are real, but do not constitute a
lawyer's opinion, a legal guarantee, general platform/quality acceptance or issue
closure. This documentation correction authorizes no publication or signature.
