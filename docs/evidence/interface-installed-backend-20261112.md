# Installed Protect backend interface use — 12 November 2026

Protect version: **7.4.96**. Installed backend: `/usr/share/unifi-protect/app/service.js`, **11,893,109 bytes**, SHA-256 `74407353b3106ff2174f3c460ba3b2ca2a98774da372e791ec7400824dc2a397`. Parsed on the owner's console with Node 24's bundled Acorn 8.18.0.

The owner explicitly authorized the pending Debug ToS/EULA acceptance. Only original read-only observation code was run; the manufacturer's program was parsed, not executed. No manufacturer source expression or credential/identifier/media value is reproduced.

## Findings

| Inventory key | Reviewed interface use |
| --- | --- |
| `wire_atom:ResetAIPortStreams` | The installed controller uses ResetAIPortStreams as an explicit control-dispatch case or control-call argument. This establishes the protocol name, not support for every possible payload or a new native execution. |
| `inventory:ResetAIPortStreams` | Same reviewed installed controller protocol-name use as the wire_atom entry. |
| `wire_atom:EventAIPortStatus` | The installed controller uses EventAIPortStatus as an explicit control-dispatch case or control-call argument. This establishes the protocol name, not support for every possible payload or a new native execution. |
| `inventory:EventAIPortStatus` | Same reviewed installed controller protocol-name use as the wire_atom entry. |
| `wire_atom:EventFeatureFlagsUpdated` | The installed controller uses EventFeatureFlagsUpdated as an explicit control-dispatch case or control-call argument. This establishes the protocol name, not support for every possible payload or a new native execution. |
| `wire_atom:EventSmartAudio` | The installed controller uses EventSmartAudio as an explicit control-dispatch case or control-call argument. This establishes the protocol name, not support for every possible payload or a new native execution. |
| `wire_atom:EventSmartMotion` | The installed controller uses EventSmartMotion as an explicit control-dispatch case or control-call argument. This establishes the protocol name, not support for every possible payload or a new native execution. |
| `wire_atom:GetSystemStats` | The installed controller uses GetSystemStats as an explicit control-dispatch case or control-call argument. This establishes the protocol name, not support for every possible payload or a new native execution. |
| `wire_atom:StartService` | The installed controller uses StartService as an explicit control-dispatch case or control-call argument. This establishes the protocol name, not support for every possible payload or a new native execution. |
| `wire_atom:ubnt_avclient_features` | The installed controller uses ubnt_avclient_features as an explicit control-dispatch case or control-call argument. This establishes the protocol name, not support for every possible payload or a new native execution. |
| `wire_atom:ubnt_avclient_timeSync` | The installed controller uses ubnt_avclient_timeSync as an explicit control-dispatch case or control-call argument. This establishes the protocol name, not support for every possible payload or a new native execution. |
| `wire_atom:setInfo` | The installed controller passes setInfo as the command argument to its control-call path. No settings command was sent during this review. |
| `inventory:/api/1.2/manage` | The installed controller constructs an HTTPS management URI with this exact path. |
| `wire_atom:/api/1.2/manage` | The installed controller constructs an HTTPS management URI with this exact path. |
| `inventory:/api/info` | The installed controller constructs an HTTPS information URI with this exact path. This is a static route observation, not a new successful information request. |
| `wire_atom:/internal/aiprocessors/image/` | The installed AI-processor task builder constructs this image-input route prefix with a task-specific suffix. |
| `wire_atom:/internal/aiprocessors/image/enhanced` | The installed AI-processor task builder records this exact enhanced-image callback path. |
| `wire_atom::7968/on_demand_inference` | The installed controller task builder records this target URI. Its presence does not establish inference quality or permission for a new task. |
| `wire_field:thumbnailMs` | The installed task schema accepts thumbnailMs as an optional array of numbers and the AI-processor task builder emits that field. |
| `wire_field:timeTag` | The installed query-result schema accepts an optional string timeTag, and its query handling consumes that result property. |
| `wire_field:isStreaming` | The installed EventAIPortStatus case checks for this payload field and consumes it as a boolean-like readiness value. |
| `wire_field:isSmartDetectReady` | The installed EventAIPortStatus case checks for this payload field and consumes it as a boolean-like readiness value. |
| `wire_field:isAudioEventReady` | The installed EventAIPortStatus case checks for this payload field and consumes it as a boolean-like readiness value. |
| `wire_field:timeStamp` | The installed camera-control event handling consumes the timeStamp envelope property. This does not prove every accepted timestamp encoding or the synthetic event's downstream persistence. |
| `wire_field:mac` | Installed getInfo/adopt consumers read the mac information field. No identifier value was collected. |
| `wire_field:poeType` | Installed getInfo consumers read the poeType information field. This does not establish a particular emulated value. |
| `wire_field:version` | The installed getInfo consumers read the outer version field. Separately, the installed AI-processor capability schema defines enabled as boolean and version as string, and its per-capability defaults use version v1. This covers both the outer and nested capability contexts; it does not certify a particular emulated firmware version or native feature support. |
| `wire_atom:username` | The installed controller constructs username in the management payload: top-level username/password and nested mgmt containing token, hosts and protocol=wss. Only names and shapes were inspected; no credential or host values were read. |
| `wire_atom:password` | The installed controller constructs password in the management payload: top-level username/password and nested mgmt containing token, hosts and protocol=wss. Only names and shapes were inspected; no credential or host values were read. |
| `wire_field:password` | The installed controller constructs password in the management payload: top-level username/password and nested mgmt containing token, hosts and protocol=wss. Only names and shapes were inspected; no credential or host values were read. |
| `wire_atom:mgmt` | The installed controller constructs mgmt in the management payload: top-level username/password and nested mgmt containing token, hosts and protocol=wss. Only names and shapes were inspected; no credential or host values were read. |
| `wire_field:mgmt` | The installed controller constructs mgmt in the management payload: top-level username/password and nested mgmt containing token, hosts and protocol=wss. Only names and shapes were inspected; no credential or host values were read. |
| `wire_atom:hosts` | The installed controller constructs hosts in the management payload: top-level username/password and nested mgmt containing token, hosts and protocol=wss. Only names and shapes were inspected; no credential or host values were read. |
| `wire_field:hosts` | The installed controller constructs hosts in the management payload: top-level username/password and nested mgmt containing token, hosts and protocol=wss. Only names and shapes were inspected; no credential or host values were read. |
| `wire_atom:protocol` | The installed controller constructs protocol in the management payload: top-level username/password and nested mgmt containing token, hosts and protocol=wss. Only names and shapes were inspected; no credential or host values were read. |
| `wire_field:protocol` | The installed controller constructs protocol in the management payload: top-level username/password and nested mgmt containing token, hosts and protocol=wss. Only names and shapes were inspected; no credential or host values were read. |
| `wire_atom:token` | The installed controller constructs token in the management payload: top-level username/password and nested mgmt containing token, hosts and protocol=wss. Only names and shapes were inspected; no credential or host values were read. |
| `wire_field:token` | The installed controller constructs token in the management payload: top-level username/password and nested mgmt containing token, hosts and protocol=wss. Only names and shapes were inspected; no credential or host values were read. |
| `discovery_tlv:0x17` | Wireshark's public UBDP specification identifies type 23 (0x17) as Default and decodes one-byte or four-byte big-endian values. The public discovery guide describes IsDefault as a boolean. This supports the default-state field, not an AI-specific device identity. |
| `discovery_tlv:0x10` | The installed discovery parser's SYSTEM_ID case reads a little-endian unsigned 16-bit value and assigns the resulting system identifier to sysid. Public UBDP documentation assigns System ID to type 16 (0x10). This profile follows the actual installed parser, not Wireshark's generic big-endian interpretation. |
| `wire_field:sysid` | The installed discovery parser produces a sysid metadata field from the SYSTEM_ID value. This supports the field name and system-identifier context, not a particular emulated ID or a claim that every getInfo response requires it. |
| `aiport_status:0` | The installed control-response handler explicitly distinguishes statusCode zero from nonzero. Zero is the comparison sentinel used by this project's normal replies. This does not establish success semantics for every command, or prove a new native response was accepted. |
| `wire_field:statusCode` | The installed control-response handler consumes the statusCode property and explicitly compares it with numeric zero. The field is a control-envelope discriminator, not an HTTP response status in this context. |
| `wire_atom:x-token` | The installed control-connection header parser reads x-token in the same handler as x-ident, x-mode and x-adopted, with ucp4 handling. This is a static header-consumer observation, not a claim that x-token is always required or that a token-bearing reconnect was newly tested. |
| `wire_field:enableSmartDetect` | The installed AI-Port-aware control-settings payload constructor includes enableSmartDetect alongside isPayloadForAiPort and region/zone settings. This establishes the setting field and context, not every boolean value or a newly accepted setting change. |
| `wire_field:smartDetect` | The installed feature normalizer reads smartDetect and tests supported feature names with array-membership operations. This supports the feature-list field and context, not every locally advertised detection type or AI Port event acceptance. |
| `wire_field:motionDetect` | Public unifi-cam-proxy camera-control feature declarations advertise motionDetect as a list containing enhanced, and send that feature container in hello/parameter-agreement messages. The installed feature normalizer also consumes motionDetect. This supports the shared feature-list spelling and enhanced-motion value; it is not a fresh AI Port EventFeatureFlagsUpdated acceptance test. |
| `wire_atom:ChangeNvrSettings` | The installed controller defines ChangeNvrSettings under its CHANGE_NVR_SETTINGS command-name constant. This establishes a named controller control operation, not a claim that the local diagnostic label implements it or that it was sent during this review. |
| `wire_atom:OnvifStreamControl` | The installed AI Port controller defines OnvifStreamControl under its ONVIF control-operation constant. This establishes the control-operation name, not complete command semantics or a fresh native stream-control trial. |
| `wire_field:timestamp` | The installed controller transport send path constructs timestamp beside id and type in the message envelope; the same transport class exposes request/response send methods. A separate case-history timestamp object was explicitly excluded. This establishes the transport-envelope field context, not new native execution or proof that every unrelated timestamp field has the same meaning. |

## Limits

- The input was the currently installed Protect 7.4.96 backend, not an AI Key/AI Port firmware package, old research tree or downloaded vendor bundle.
- Static AST use proves only the stated interface spelling, schema or construction. It is not a native execution, rights approval, or proof that every emulator default/optional field is required.
- Manufacturer expressions, functions and source snippets are not included. Offsets identify the independently projected source context and are not copied algorithm descriptions.
- No adoption, pairing, inference, media request, restart, credential rotation or device-setting write was performed.

The generic Wireshark System ID decoding is big-endian, whereas the owner's installed Protect SYSTEM_ID parser explicitly uses little-endian. The mapping follows that concrete installed profile and retains the cross-implementation difference. Unsupported names and paths not found in this installed version remain unresolved; absence alone is not a proof that a working historical feature may be removed.

## Public references

- https://github.com/wireshark/wireshark/blob/fe168fe75ceda882ef00271041ee8e53d7ab5dad/epan/dissectors/packet-ubdp.c — Read protocol constants and decoding semantics only; no source copied, linked or executed.
- https://jrjparks.github.io/unofficial-unifi-guide/protocols/discovery.html — Read published protocol description only.

- https://github.com/keshavdv/unifi-cam-proxy/blob/cc6d3fc7cdae9f1dfce575627089632aec696403/unifi/cams/base.py#L106-L112 — Read the feature-list declaration and its transmission at lines 254 and 273 only. No implementation copied or executed.

See the [structured, scope-limited record](interface-installed-backend-20261112.json). No release-evidence status or reviewer was changed.
