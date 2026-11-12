# Installed internal snapshot route — 12 November 2026

This is a static interface-provenance record for installed Protect 7.4.96, not legal clearance or a successful media test.

The same 11,893,109-byte backend, SHA256 `74407353b3106ff2174f3c460ba3b2ca2a98774da372e791ec7400824dc2a397`, was parsed on the owner console with original Acorn observation code. Only fixed interface names, offsets, module identities and structural assertions were exported. Vendor code was not evaluated or copied into the implementation.

## Exact composition

1. Module **761379** registers GET `/aiprocessors/snapshot/generate` at offset **4570087**, on the singleton created at **4561322**.
2. That exact singleton is exported under the name **aiprocessorsInternalRouter**, at **4576182**. It is not the module's default export; an earlier default-export assumption failed and was not accepted.
3. Internal-router module **44039** imports module 761379 and passes that named export as the first base-constructor argument at **4556637**. Its `init` declares prefix **/internal** through `setPrefix` at **4557219**.
4. The base router in module **815233** forwards all rest constructor arguments into `merge` at **3731857**. `merge` copies the child route table into its own table at **3732295**.
5. The prefix setter prepares `prefixExp`. Path handling removes that prefix expression at **3733298**, and matching uses the resulting relative path at **3732347**.

Together these establish the declared full GET path **/internal/aiprocessors/snapshot/generate** for this installed backend. The separate `buildSnapshotGenerateUrl` producer returns a relative suffix; it alone would not prove the full prefix.

[The structured record](interface-installed-router-20261112.json) binds the source revision, exact assertions and original-observer digests. A broad composition probe was interrupted; a bounded subtree replacement and the final named-export assertions completed under a 45-second process limit. Failed and diagnostic-only attempts remain private and are not counted as proof.

## Limits

No request was made to the snapshot route. This does not prove live image generation, authentication/parameter coverage, native delivery to the worker, other controller versions or the separate export-from-camera alias. No media, model request, firmware/private disassembly, device configuration change, rights approval, owner attestation, merge or publication occurred in this source-only check.
