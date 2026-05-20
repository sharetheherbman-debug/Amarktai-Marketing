# Marketing Learning Loop Audit

## Endpoints

- `POST /api/v1/learning/run-now`
- `GET /api/v1/learning/status`
- `GET /api/v1/learning/insights`
- `GET /api/v1/learning/insights/{webapp_id}`

## Inputs represented

- Analytics metrics records
- Generated content counts
- User-selected business context

## Outputs represented

- Per-run learning profile
- What worked / did not work
- Recommended changes for tomorrow
- Updated angles/timing/hooks/hashtag guidance
- Avoid/retry notes

## Scheduler truth

- Automatic daily scheduler is reported as not configured when worker wiring is absent.
- Manual run-now remains available.

## UX wording

- Insights are framed as performance-informed recommendations.
- No guaranteed follower/customer outcome language.
