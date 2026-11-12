# Installed Protect UI interface consumers — 11 November 2026

The owner's current Protect installation reports **7.4.96**. The served static frontend asset is `/app-assets/protect/swai-7.4.26.js`, SHA-256 `47e53c031316db7a17545fb753ac78fc43158de355b8a2630d6fd175c81c91c8`. The filename is not the Protect version.

The existing signed-in browser fetched the asset without changing settings or accepting new terms. Fixed capability consumers were inspected. No manufacturer source expression, device identifier, credential, media or payload is reproduced here.

## Findings

| Inventory key | Installed UI use | Context |
| --- | --- | --- |
| `wire_atom:supportAiSummary` | The installed Protect UI recognizes the capability name supportAiSummary. | AI-feature-kind to capability-name mapping, with an enabled-member consumer. |
| `wire_atom:supportFaceEnhancement` | The installed Protect UI recognizes the capability name supportFaceEnhancement. | Processor featureFlags property access, with an enabled-member consumer and feature-specific UI availability/settings. |
| `wire_atom:supportFaceRecognition` | The installed Protect UI recognizes the capability name supportFaceRecognition. | AI-feature-kind to capability-name mapping, with an enabled-member consumer. |
| `wire_atom:supportLicensePlateRecognition` | The installed Protect UI recognizes the capability name supportLicensePlateRecognition. | AI-feature-kind to capability-name mapping, with an enabled-member consumer. |
| `wire_atom:supportRecognizeAnything` | The installed Protect UI recognizes the capability name supportRecognizeAnything. | AI-feature-kind to capability-name mapping, with an enabled-member consumer. |
| `wire_atom:supportRetroactiveProcessing` | The installed Protect UI recognizes the capability name supportRetroactiveProcessing. | Processor featureFlags property access, with an enabled-member consumer and feature-specific UI availability/settings. |
| `wire_field:supportAiSummary` | The installed UI consumes the supportAiSummary capability property. | AI summary feature mapping and the featureFlags.aiFeatureFlag summary availability selector. |
| `wire_field:featureFlags` | The installed UI consumes featureFlags as the capability container. | Processor feature gating for face enhancement and retroactive-processing controls. |
| `wire_field:enabled` | The installed UI consumes enabled as a boolean-like capability gate. | Enabled-property consumers under the stated featureFlags capability properties. |

## Limits

This supports the property spellings and stated current UI consumer contexts. It does not establish backend wire-schema completeness, default values, task support, feature quality or every enabled/version field in the implementation. No proprietary source expression is reproduced.

These are not the earlier unqualified literal-count matches. The capability-name mapping and property access are an independent consumer in the installed UI, not merely values sent by our emulator and echoed in bootstrap.

See the [structured record](interface-installed-ui-20261111.json). This is provenance evidence, not rights or release approval.
