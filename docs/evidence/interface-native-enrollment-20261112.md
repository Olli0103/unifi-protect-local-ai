# Isolated native enrollment interface observation — 12 November 2026

This is a narrow provenance record, not legal clearance or a release-image qualification.

## Setup and boundary

After all seven CI workflow jobs passed at `e4d8209fabc8af875132e34443adcbf06ec5c95a`, the owner-directed isolated tests used two separate fresh identities in sequence, generated private keys, camera-free/private state and existing local base images. All 183 own Python source modules were frozen and mounted read-only; the source/observer digests and fixed metadata are in [the structured record](interface-native-enrollment-20261112.json). This exact-module experiment does not qualify a rebuilt distributable image.

The temporary LAN address was outside DHCP, absent from controller inventory/reservations, and checked with two bounded duplicate-address probes. A former test address was found occupied and was not reused. No router/network setting was changed. The services had read-only roots, dropped capabilities, no published host ports, non-root users, no restart policy and ten-minute execution/enrollment limits. The disposable address probe alone used a raw-socket capability, sent two ARP probes and was removed.

Only allowlisted fixed routes, field names/types, booleans, counts and status codes were recorded. Request values, credentials, tokens, identifiers and media are absent from this public record. Private generated state and original receipts remain outside Git.

## Key HTTP route

Protect 7.4.96 originated one HTTPS **POST `/api/adopt`** to the new Key. The exact TCP peer matched the configured controller. The observed input fields were:

| Field | Type |
| --- | --- |
| username, password | string |
| protocol, token | string |
| hosts | array |
| mode | number |
| nvr, controller, consoleId, consoleName | string |

There were no other input fields. `protocol` was WSS and `mode` zero; no credential/token/host/identity value was retained. The local handler returned HTTP 200. Independently observed local adoption, a connected pinned control channel, matching time synchronization, one successful `changeUserPassword`, a stored rotated-credential hash and absence of a pending token corroborated the native CONNECTED/adopted state. The factory marker was absent. Three credentialed `/api/info` requests also returned 200.

All served AI capabilities were disabled, no worker/provider was started, no camera was attached, and `RequestAI` count remained zero. This closes only the exact `/api/adopt` route context, including the local lab's use of that same route string. It does not establish optional-field necessity, every historical controller version or every shared metadata context. The existing project-defined optional-policy records retain their scope.

## Port result and negative boundary

The independent fresh Port enrollment reached native and local adopted/CONNECTED state, one successful credential rotation, an agreed control channel, no paired cameras and zero stream starts/active streams. Protect originated HTTPS POST `/api/1.2/manage`, returning 200. It did **not** originate `/api/1.2/login` in this bounded trial. That missing route remains `needs_observation`; a successful enrollment through another route is not substitute evidence.

Neither enrollment test exercised snapshot generation/export, reverification callbacks or second-verifier inference. Those four contexts remain unresolved. No synthetic fixture or absence of a request is relabelled a native observation.

## Preservation and cleanup

Fresh before/after projections matched all eleven camera configuration/recording states, all existing processor identities/states and their pairings. All 80 original NAS container identities, images, PIDs, restart counts and statuses matched. No existing device was restarted or re-paired; no existing processing permission or camera setting was changed.

Only the positively identified test containers and native registrations were removed. Key UI removal first unadopted the test and cleared its host; a separately guarded deletion then removed that exact unadopted record. Final uncached, unique-query bootstrap reads confirmed both test identities absent. The temporary Docker network binding was absent. Private generated research state was retained, not deleted.

The first private boolean rotation check looked up a nonexistent `management_password_hash` field. A source-grounded correction checked `credential.hash` and its salt for presence, without exporting either value. The original mistaken projection and correction are retained separately; the successful native command was not inferred from that mistaken lookup.

These state snapshots are not proof of uninterrupted video at every timestamp. There was no camera-media retrieval, cloud/paid inference, model download, firmware fetch, private disassembly, rights approval, owner/reviewer attestation, merge or publication.
