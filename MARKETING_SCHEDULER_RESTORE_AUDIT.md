# Marketing Scheduler Restore Audit

## What was broken
- Live scheduler page at `app/src/app/scheduler/page.tsx` was only an upcoming list.
- Backend scheduler API at `backend/app/api/v1/endpoints/scheduler.py` only supported `POST /schedule` and `GET /upcoming`.
- No dedicated scheduler persistence table existed.
- Business detail and dashboard did not hand off to a real scheduler filter/state flow.

## What was restored
- Added persistent scheduler model: `backend/app/models/marketing_runtime.py::SchedulerItem`.
- Added scheduler runtime helper: `backend/app/services/scheduler_runtime.py`.
- Replaced scheduler API with real endpoints in `backend/app/api/v1/endpoints/scheduler.py`:
  - `GET /api/v1/scheduler/items`
  - `POST /api/v1/scheduler/items`
  - `GET /api/v1/scheduler/items/{id}`
  - `PUT /api/v1/scheduler/items/{id}`
  - `DELETE /api/v1/scheduler/items/{id}`
  - `POST /api/v1/scheduler/items/{id}/mark-posted`
  - `POST /api/v1/scheduler/items/{id}/mark-failed`
  - `GET /api/v1/scheduler/calendar`
  - compatibility: `POST /api/v1/scheduler/schedule`, `GET /api/v1/scheduler/upcoming`
- `POST /api/v1/content/items/{content_id}/schedule` now upserts real scheduler items.
- Dashboard now reads real upcoming scheduler items from `/api/v1/scheduler/upcoming`.
- Business detail and dashboard now open scheduler with the selected business filter.
- Scheduler UI now supports month/week/day/list modes, platform/business/status filters, selected item preview, and reschedule action.

## Schema repair
- `scripts/repair_live_schema.py` now creates `scheduler_items` when missing.

## Remaining
- Drag/drop rescheduling is not implemented.
- Bulk schedule from campaign pack is still via repeated item scheduling, not a dedicated bulk API.

## Go-live status
- LIMITED: real scheduler persistence restored, but advanced UX automation remains incomplete.
