# Retired experimental route surfaces — 12 November 2026

This is a reviewed compatibility-scope change against commit `4ef709dd81ca38ddd2de07864b7ed278306e8871`, not a new native observation, legal clearance or rights approval. No deployed service was changed.

## Login

The candidate's experimental `POST /api/1.2/login` issued `AISESSION` cookies but no production code consumed those cookies. Management verifies the request-body credential independently. The fresh camera-free Protect 7.4.96 trial used [manage, not login](interface-native-enrollment-20261112.md). This does not prove older controllers never use login.

The route, handler and unused cookie store were removed. Requests now receive **404**, including after a valid credential rotation and during the bounded factory enrollment window. Older clients requiring login are outside this candidate's current compatibility scope. The [Protect 7.2.105 historical description](ai-port-firmware-contract.md) remains; retirement does not erase prior research.

Management authentication, peer/window checks, private credential persistence and successful-rotation acknowledgement are retained. The management verifier and management handler are independently compared with the prior branch.

## Legacy snapshot alias

`/internal/aiprocessors/snapshot/export-from-camera` existed only as an accepted media-path constant, without a production producer or a qualified current route binding. Its removal narrows the worker allowlist: such jobs are rejected during normalization, before media/model/callback I/O.

The separately [installed-router-qualified](interface-installed-router-20261112.md) `/internal/aiprocessors/snapshot/generate` remains, as do image/video paths, callback paths and existing verification features. The old alias is not reclassified as observed.

## Validation boundary

Before the runtime change, the new retirement assertions failed in four cases while ten other targeted cases passed. Local integration regressions use synthetic credentials and localhost fake media/model/callback services. They check both relative and absolute media URLs, actual supported snapshot execution, credentialed management and the factory boundaries.

The private branch-qualification record carries subsequent exact test counts and build/source/secret-scan results. Earlier enrollment evidence remains bound to its original experiment bytes; this change is not a new native image test. No production restart, camera reassignment, media request, model request, release metadata approval, merge or publication was performed by this retirement.

Machine-readable record: [interface-retired-experimental-routes-20261112.json](interface-retired-experimental-routes-20261112.json).
