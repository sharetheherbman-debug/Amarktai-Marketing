# Marketing Model Routing Audit

## Scope
- Content library persistence and visibility flow
- GenX/Qwen/HF routing signals surfaced from generation metadata

## Findings
- Content items now persist provider attempted/actual, model/task/capability, generation status, degraded flag, and reason in saved library payloads.
- Generate Creative and Generate Pack now return persisted `content_id` values and write saved items for non-text formats.
- Dashboard and business detail now show provider/model and degraded status directly from persisted data.

## Remaining Gaps
- Dedicated ProviderDecisionEngine service and explicit route endpoint still need full implementation.
- Per-user GenX model mapping endpoints/UI are still partial.
