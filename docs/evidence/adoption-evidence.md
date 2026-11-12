# AI Key adoption evidence

Static inspection on 2026-09-22 supports building an independent AI Key protocol implementation that uses Protect's normal administrator adoption flow. In the inspected path, trust comes from a controller-issued token and a pinned TLS certificate. No manufacturer-signed device certificate, hardware challenge, serial-number check, or MAC OUI check appears in that path. Acceptance by an unmodified running controller remains `needs_evidence`.

This finding covers adoption. It does not establish that a replacement can complete every AI job, populate Find Anything, or survive upgrades.

## Publication status

This is historical technical evidence, not legal clearance. Public availability of the packages does not establish authorized use or permission for disassembly. Analysis authorization, interoperability necessity, minimal scope, and the absence of copied protected expression remain `needs_evidence` in [provenance](../legal/provenance.md). The reported sequence of analysis and implementation is not evidence of an organizational clean-room separation. Do not open or reuse private firmware research for further development, and do not add firmware, disassemblies or extracted vendor functions to public artifacts. Private retention or deletion is a maintainer task, not performed by this change.

## Scope and reproducibility

Early research in September 2026 included static inspection, including disassembly, of selected AI Key 2.2.8 network binaries and reading of AI Port 5.1.12 configuration files. Those details have been removed from this repository. The interface facts used by the implementation are mapped to the maintainer's own Protect installation, observation of the maintainer's own UniFi devices, live interoperability trials or public documentation in [interface sources](../legal/interface-sources.md). No vendor code, binaries, keys or firmware are included.

**Mapping status: needs_evidence.** The mapping sentence in the requested notice above is a completion target, not a completed provenance attestation. WP2 must inventory the interface facts and explicitly retain unresolved observations. Historical public-controller package records are not silently relabelled as observations of the maintainer's installed version. This change grants no legal or release approval.

The retained controller observations below concern Protect 7.2.105
`service.js` (SHA-256
`a7370e9a1b35db67d56104268841b9c2ba16342befb750ffef6654ee2b07bfdb`).
They describe static controller-side behavior, not a new read of an installed
controller or a live adoption result. No vendor program was executed in the
historical investigation.

## Observed provisioning flow

Protect's ordinary adoption flow checks user permission and existing console
ownership, issues a MAC-bound token, supplies management configuration, and
verifies a connecting processor's certificate and token. The independent
implementation must retain its own identity, private key, configuration and
controller pin. Device-side implementation internals are no longer reproduced
here; source gaps are tracked in the interface map.

## Observed controller acceptance gates

Protect 7.2.105's `verifyUcpClient` supplies the following controller-side acceptance order:

| Gate | Observed behavior |
| --- | --- |
| Rate limit | Rejects an excessive connection rate. |
| TLS certificate | Requires a fingerprint obtained from `req.socket.getPeerCertificate()`. |
| Headers | Requires identity, subprotocol, type, and mode. Mode defaults to `"0"`. |
| Mode | Rejects every value except `"0"`. |
| Subprotocol | Accepts only `ucp4` or `updates`. |
| Model | Looks up the supplied sysid in device manifests, with a type-based fallback. Unknown device type fails. |
| Identity | Normalizes the supplied MAC and finds or creates the model's device record. |
| Initial UCP connection | Rejects a record that is not adopted when there is no token. |
| Known certificate | Accepts a matching stored device fingerprint. |
| Token | Validates token and MAC, then records adopted state and the TLS fingerprint. |
| Existing record without a fingerprint | An already-adopted record can receive its initial fingerprint here. This is observed legacy/state-handling behavior, not a proposed provisioning route. |
| Remaining cases | Rejects fingerprint mismatch. |

Normal token verification removes expired tokens, requires exact token equality and matching MAC when one is bound, and consumes a successful token. A valid reconnect with the same pinned fingerprint takes the earlier certificate branch, so token consumption is not a reconnect prohibition.

The enclosing `initWssServer` requests a client certificate and delegates
acceptance to `verifyUcpClient`, wired through `createClientVerifier`.
This inspected controller path uses token/fingerprint trust rather than proving
manufacturer CA issuance. A replacement still needs its own TLS certificate
and possession of the corresponding private key; header strings do not replace
that requirement.

Other retained controller-side function references:

| Function or data | Controller-side observation |
| --- | --- |
| `adoptDevices` | User create permission and device-ID lookup. |
| `adopt` | Management body, local device credentials, MAC-bound token and mode 0. |
| `getToken` | 32 random characters and one-hour expiry. |
| `verifyToken` | Expiry cleanup, token/MAC comparison and token consumption. |
| `verifyTokenAndAdopt` | Token validation followed by saved adopted state and fingerprint. |
| `isConsoleAuthorizedForDevice` | Existing console ownership check. |
| `getDeviceManifest` | Known sysid mapped to model class. |
| `AI_PROCESSOR_SYSIDS` | Includes `0xa5f0` mapped to `UP-AI-KEY`. |
| `normalizeMAC` | Separator removal and uppercase normalization. |
| `createClientVerifier` | UCP4 and updates connections routed to the verifier. |

The normal controller payload supplies mode 0; the inspected receiver rejects
mode 1. No device-side optional-key implementation detail is retained as a
source for the independent implementation.

## Inference and remaining evidence

An independent implementation can probably complete native adoption without a genuine AI Key hardware secret. This limited inference follows from the inspected controller TLS configuration and token/fingerprint verifier; removed device-side internals are not an independent source attestation. No missing cryptographic manufacturer credential has been found in that chain.

That statement does not prove that no other component ever validates device identity. Discovery, store/model validators, later device-information responses, license or capability handling, and newer versions were not exhaustively inspected. The code paths examined use a claimed model/sysid and normalized MAC; no OUI, serial, or hardware-attestation gate appeared there.

The normal prototype should use its own test identity and generated key, expose the required management endpoint, appear as a separate candidate device, and receive its token through an authorized administrator adoption action. Reusing a real device's identity, editing controller records, acquiring another device's token, or forging forwarded certificate headers is outside this validation path.

The smallest useful offline fixture would exercise fresh adoption with a synthetic controller-issued token, expiry and MAC mismatch rejection, token consumption, pinned-certificate reconnect, wrong-certificate rejection, no-token pre-adoption rejection, and mode-1 rejection. It must distinguish a fresh token branch from an already-pinned reconnect. Such a fixture validates our reconstruction only. The next interoperability evidence must come from an isolated controller test through the ordinary adoption flow, followed by required device-info/state exchanges and one real AI job. None of those live acceptance checks has run here.
