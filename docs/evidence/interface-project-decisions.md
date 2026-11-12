# Local interface design decisions

These entries were caught by the broad source inventory but do not assert manufacturer requirements. This is the project's original public specification, not a device observation or an independently sourced manufacturer contract.

## Decisions

| Inventory key | Local decision |
| --- | --- |
| `aiport_status:501` | A locally selected unsupported-operation refusal code in the project's JSON control replies. It is not an HTTP response status here and is not claimed to have a manufacturer-defined meaning. |
| `aiport_status:5` | A locally selected fail-closed refusal code for invalid/unavailable control operations. The project does not claim that this number is the manufacturer's required error code, or that all controller versions interpret it identically. |
| `inventory:ubntbox` | The retained status profile string ubntbox-0.1.7-v1-info is a legacy project diagnostic identifier. Retaining its spelling avoids silently changing existing status consumers; it does not claim vendor implementation parity, vendor origin or independent observation of a binary. |
| `wire_atom:/internal/aiprocessors/descriptions/fixture-task` | An explicitly synthetic lab task path. The fixture suffix is invented by this project and is not a real controller task ID or an assertion of native endpoint acceptance. |
| `wire_atom:/internal/aiprocessors/image/fixture` | An explicitly synthetic lab image path. The fixture suffix is invented; this lab example neither carries camera media nor demonstrates native image-route acceptance. |
| `wire_atom:nvr` | A locally permitted optional management-metadata label for content-free diagnostic field counting and bounded string pass-through. It is not required to establish controller identity, TLS trust, adoption confirmation or credentials, and is not emitted as a required manufacturer control field. No claim is made that Protect sends or requires this optional alias. |
| `wire_atom:controller` | A locally permitted optional management-metadata label for content-free diagnostic field counting and bounded string pass-through. It is not required to establish controller identity, TLS trust, adoption confirmation or credentials, and is not emitted as a required manufacturer control field. No claim is made that Protect sends or requires this optional alias. |
| `wire_atom:consoleId` | A locally permitted optional management-metadata label for content-free diagnostic field counting and bounded string pass-through. It is not required to establish controller identity, TLS trust, adoption confirmation or credentials, and is not emitted as a required manufacturer control field. No claim is made that Protect sends or requires this optional alias. |
| `wire_atom:consoleName` | A locally permitted optional management-metadata label for content-free diagnostic field counting and bounded string pass-through. It is not required to establish controller identity, TLS trust, adoption confirmation or credentials, and is not emitted as a required manufacturer control field. No claim is made that Protect sends or requires this optional alias. |
| `wire_atom:mode` | A local optional zero-mode policy in this project's adoption API and state: an omitted mode is treated as zero; only numeric zero or string zero is accepted. The outbound x-mode header has its own separate source record and is not derived from an arbitrary supplied mode. This is a conservative local input restriction, not a claim that a manufacturer management payload must contain mode. |
| `wire_field:mode` | A local optional zero-mode policy in this project's adoption API and state: an omitted mode is treated as zero; only numeric zero or string zero is accepted. The outbound x-mode header has its own separate source record and is not derived from an arbitrary supplied mode. This is a conservative local input restriction, not a claim that a manufacturer management payload must contain mode. |

## Accounting and limits

These eleven entries are resolved as **project-defined/non-vendor**, not counted as device observations. The six added entries were manually reviewed in the diagnostic tables, Key adoption/state validator and AI Port management validator; they are optional local metadata/input-policy extensions, not newly observed manufacturer fields. Their registry source_class is public_documentation because this file specifies the project's own choices; fact_kind explicitly prevents confusing that with independent manufacturer documentation.

A controller might reject or ignore a chosen refusal code. That behavior remains a compatibility question, and this document does not certify it. None of these choices licenses third-party material, clears past research actions or approves a release.

The [structured record](interface-project-decisions.json) lists exact source locations and classification flags. This classification changes no runtime code, existing status identifier or synthetic example. Historical research remains disclosed separately; classifying an optional local API extension does not certify historical acquisition or knowledge provenance.
