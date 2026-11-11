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

## Accounting and limits

These five entries are resolved as **project-defined/non-vendor**, not counted as five new device observations. Their registry source_class is public_documentation because this file specifies the project's own choices; fact_kind explicitly prevents confusing that with independent manufacturer documentation.

A controller might reject or ignore a chosen refusal code. That behavior remains a compatibility question, and this document does not certify it. None of these choices licenses third-party material, clears past research actions or approves a release.

The [structured record](interface-project-decisions.json) lists exact source locations and classification flags. No runtime code, existing status identifier or synthetic example is changed.
