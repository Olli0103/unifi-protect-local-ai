# Search, description and storage contracts

Static inspection on 2026-09-22. No firmware was executed and no device, network service or database was changed. This note describes shipped code, not a demonstrated working emulator.

**Finding:** Native descriptions and native semantic search have recoverable contracts. A caption alone does not satisfy semantic search. The inspected versions expose two distinct generations, and they must not be mixed.

## Evidence scope

Early research in September 2026 included static inspection, including disassembly, of selected AI Key 2.2.8 network binaries and reading of AI Port 5.1.12 configuration files. Those details have been removed from this repository. The interface facts used by the implementation are mapped to the maintainer's own Protect installation, observation of the maintainer's own UniFi devices, live interoperability trials or public documentation in [interface sources](../legal/interface-sources.md). No vendor code, binaries, keys or firmware are included.

**Mapping status: needs_evidence.** The mapping sentence in the requested notice above is a completion target, not a completed provenance attestation. WP2 must inventory the interface facts and explicitly retain unresolved observations. Historical public-controller package records are not silently relabelled as observations of the maintainer's installed version. This change grants no legal or release approval.

Retained static controller references concern Protect 7.2.105
`usr/share/unifi-protect/app/service.js`, SHA-256
`a7370e9a1b35db67d56104268841b9c2ba16342befb750ffef6654ee2b07bfdb`.
Module and function names identify historical controller-side observations.
Device-package paths, source ranges and internal implementation descriptions
are not retained as implementation evidence.

## 1. Two separate search profiles

| Contract | Older RAM / image search | New session description search |
|---|---|---|
| Stored semantic vector | `ramDetections.embedding vector(768)` | `smartDetectSessionsSearch.descEmbedding vector(384)` |
| Query encoder identifier | `clip-ViT-L-14` in Protect | `multilingual-e5-small` in Protect |
| Other vector | RAM `reidEmbedding vector(1024)` | Session member `reidEmbedding vector(512)` |
| Result ingress | Multipart `/internal/aiprocessors/recognize-anything` | JSON `/internal/aiprocessors/descriptions/:taskId` |
| Query request | UCP4 `NL_PARSE`, normally CLIP | UCP4 `NL_PARSE` with `model: multilingual-e5-small` |
| Main search | Image/text cosine similarity plus tags/labels | Description cosine similarity, optional BM25 fusion and reranking |

**Confirmed:** Protect 7.2.105 contains both paths. The session path is shipped production code and migrations, not the unrelated example database in `uaibd`. **Open:** whether the target Protect version enables this branch, what firmware matches it, and whether all advertised capabilities are active. Package presence does not establish runtime enablement.

### Older 768-dimensional path

Protect module `50407` names the CLIP query model. Module `3465` validates
image-query `imgEmbed` as exactly 768 floats. The RAM inference schema validates
optional frame `imgEmbed` as 768 and `reidEmbed` as 1024. The controller model
uses `vector(768)` and `vector(1024)`; module `18740` installs cosine and L2
indexes respectively, with `m=4` and `ef_construction=32`.

**Limit:** The controller's model name and vector width do not establish
encoder weights, tokenization or query preprocessing. Arbitrary
768-dimensional embeddings will not share the expected space. The short-query
prefix used by the implementation needs an independent source in WP2; removing
its old firmware citation does not validate it. A replacement must use a
compatible text/image pair and validate retrieval quality.

### New 384-dimensional session path

`P/migrations/aiprocessor/1781535214000_create-smartDetectSessions-search.js` creates:

- `smartDetectSessionsSearch`, keyed by `sessionId`, with `descEmbedding vector(384)`, label/camera/object-type arrays, and first/last timestamps.
- HNSW cosine index on `descEmbedding`, `m=16`, `ef_construction=64`, plus filter indexes.
- `smartDetectSessionObjects`, keyed by smart-detection object ID, with session/event/camera references, timestamps, thumbnail ID, `reidEmbedding vector(512)`, and model string.

`1790000000000_add-session-search-text.js` adds `description` and `labelText` text columns. No prototype table is used to infer this schema.

Module `50407` defines `E5_QUERY_EMBED_DIM=384`. `encodeSessionSearchQuery` requires an available external AI Key, requests `NL_PARSE` with `model: multilingual-e5-small`, and uses a 10-second timeout. It rejects a supplied model name whose prefix before `@` differs and rejects vectors of any other length. Missing model metadata is accepted. Encoder failure returns no results, not a CLIP fallback.

**Compatibility boundary:** The 768-dimensional and 384-dimensional paths
are distinct controller contracts. A source record for one profile does not
establish compatible encoder behavior for the other.

## 2. What a native session-description worker must do

The description endpoint is a callback for controller-created work, not an arbitrary event-ingest API.

1. The controller builds a session from native smart-detection objects. Module `72881` selects person, face, vehicle and animal representatives, forms an `open` or `close` pass, and creates a `generateDescription` task. Its stored arguments include `sessionId`, `cameraId`, `eventId`, `pass`, `promptProfile: session-v1`, and images or videos.
2. Module `42220` dispatches `devices.sendRequest` with command `RequestAI`, `targetUri: :7968/describe`, `timeoutMs: 30000`, a callback under `/internal/aiprocessors/descriptions/{taskId}`, and controller-owned media URLs. This preserves the existing camera and event identity.
3. Module `68823` exposes the callback with device middleware and body validation. It permits `description`, optional labels, optional `descEmbedding` array or null, optional failures, model and version. It sends HTTP 200 before asynchronous persistence. Therefore HTTP 200 is not an indexing receipt.
4. Module `31512` resolves `{taskId}` from `aiprocessorTasks`. It requires a stored smart-detection object ID, session ID, camera ID and pass of `open` or `close`. Unknown task IDs or tasks whose arguments were cleared return null and are dropped by `saveDescriptions`.
5. Module `60965` checks that deep understanding remains enabled for the camera, that the session exists, and that the returned description is nonempty. It sanitizes labels, creates/resolves label IDs, upserts the search-host row, tokenizes BM25 when available, updates the console session and marks the task done.

Module `20129` checks global deep-understanding enablement and whether all cameras or the specific camera are selected. There is also a development feature-flag path; its presence is not authority to enable or rely on it.

**For native search:** A nonempty description can be accepted with `descEmbedding:null`, but module `30435` filters out null `descEmbedding` in both dense and BM25 candidate queries. The worker therefore needs a compatible 384-dimensional description embedding and a matching query encoder. The callback schema itself does not enforce dimension or model compatibility; the PostgreSQL vector column and query path impose those requirements later.

The E5 checkpoint/tokenization/pooling/normalization/prefix details for generating document embeddings are **needs_evidence**. The controller's model identifier and width do not establish these details. A successful retrieval test with known positive and negative examples is required before claiming compatibility.

The old automatic caption path is separate: Protect module `24160`
updates `ramDetections.ramDescription` and notifies clients. This does not
create a session search embedding. Removed device-side sender details are not
a retained source for preprocessing or callback behavior.

## 3. Storage, SQL privileges and search extensions

Protect modules `65737`, `63092` and `12280` connect to port 5432 with TLS and server verification disabled, first trying the device's current password, then a provisioning fallback only after an invalid-password failure. Module `27299` runs migrations and search setup before registering its SQL connection. Module `33815` runs the controller's `migrations/aiprocessor` scripts and records migration metadata and source in the remote database. An emulator therefore needs a real compatible PostgreSQL service, privileges to apply these migrations, and required extensions, rather than merely a caption HTTP endpoint.

Module `4169` provisions optional `pg_tokenizer`, `vchord_bm25`, and `plpython3u` components. It reads `/usr/local/lib/e5-small/tokenizer.json`, creates `session_tok`, adds the BM25 column/index, and defines a rerank SQL function that calls `http://127.0.0.1:8123/rerank` on the search host. It revokes that function from PUBLIC and grants execution to the Protect role.

Module `30435` implements dense retrieval or dense plus BM25 reciprocal-rank fusion, optionally followed by reranking. When reranking is expected, missing hybrid objects or unavailable reranking can produce zero results. Without that requirement, it can degrade to dense-only search. The target feature flags and extensions remain **needs_evidence**.

## 4. Job lifecycle and retries

Controller modules `38701`, `90379`, and `74771` establish:

- Persistent task states: pending, queued, failed, failedRetry, done. Arguments are stored in `aiprocessorTasks.args` for retry.
- Description/embedding task timeout defaults to 180 seconds, with a positive configuration override. Other task types default to 30 minutes. The dispatch request timeout is separately 30 seconds.
- Completion clears task arguments. Nonretryable failure also clears them. A repeated description callback then fails the ledger validation; callbacks are not a general idempotent ingest operation.
- No free processor and some video-export failures are retryable. Unknown external failures and timeouts are marked nonretryable at this task level. A later session pass may be separate work.
- Video-export retry backoff is five minutes. Built-in AI-controller failure backoff is one minute, with a ten-minute maximum task age. These built-in rules do not establish external Key retry behavior.
- Failed-retry selection takes up to 30 latest distinct tasks. `retryTasks` is triggered from processor queue state, debounced to at most once per 60 seconds, and checks for an empty queue.
- Empty descriptions leave the session available for later retry but mark that task done. A failed search-host upsert leaves the console session unindexed for reconciliation.

**Recovery limit:** Module `66079` reconciles missing session search rows with a null description embedding; it does not regenerate the lost embedding. The code seen here cannot justify a promise of automatic full search-index recovery.

## 5. Excluded examples and next validation

Device-side sample databases, telemetry queues and removed implementation
internals are not evidence of Protect's production search persistence or retry
behavior. Retained controller-side observations remain version-specific.

Implement only the profile supported by the actual controller and firmware interface. Before device testing, establish its version, feature enablement, adoption/authentication contract, task dispatch, SQL migration requirements, and compatible model pair. A valid callback, persisted row, visible native description, positive search result, negative search result, and restart/retry behavior are separate acceptance checks. None has been demonstrated on a real device in this static investigation.
