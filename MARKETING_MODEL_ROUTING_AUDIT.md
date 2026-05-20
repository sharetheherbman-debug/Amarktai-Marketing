# Marketing Model Routing Audit

## What was broken
- GenX/Qwen/HF routing was implicit and scattered.
- No explicit capability routing endpoint existed.
- Qwen catalog support was far below the available model surface.

## What was restored
- Added provider router modules:
  - `backend/app/services/provider_decision_engine.py`
  - `backend/app/services/genx_router_client.py`
  - `backend/app/services/qwen_model_catalog.py`
  - `backend/app/services/qwen_router.py`
- Added route endpoint:
  - `POST /api/v1/capabilities/route`
- Capability responses now include platform support metadata through `backend/app/services/capability_catalog.py`.
- Content generation metadata remains persisted in `backend/app/api/v1/endpoints/content.py`.

## Current routing truth
- Budget/routine routing can select Qwen through `provider_decision_engine`.
- Multimodal/premium routing prefers GenX when configured.
- Hugging Face remains a truthful fallback.
- Template remains final fallback.

## Remaining gaps
- Full async job orchestration for every GenX/Qwen multimodal model is not yet wired end-to-end.
- The route decision is currently available via API, but not every generation path enforces it yet.

## Go-live status
- LIMITED: routing truth and capability endpoint restored, full multimodal orchestration still partial.
