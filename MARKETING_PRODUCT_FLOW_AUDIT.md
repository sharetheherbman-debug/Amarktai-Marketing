# Marketing Product Flow Audit

## Current production flow

1. Login
2. Add Business (name-only, URL-only, or both)
3. Analyze Website (Firecrawl or fallback scraping path)
4. Generate content (single, all, creative, pack)
5. Review / approval / schedule draft
6. Run learning manually when scheduler is not configured

## Business lifecycle truth

- Add: `/api/v1/webapps/`
- Edit: `/api/v1/webapps/{id}`
- Delete: `/api/v1/webapps/{id}?confirm=true`
- Cleanup smoke/test business names: `/api/v1/webapps/cleanup-smoke`

Delete removes related generated records for current user and returns:

```json
{
  "deleted": true,
  "id": "…",
  "content_deleted": 0,
  "schedules_deleted": 0,
  "message": "Business removed."
}
```

## Content Studio production truth

- No hidden default business.
- Empty-state shown if no businesses remain.
- Creative suite sections exposed with truthful state labels.
- Generation metadata now includes provider/model/task/capability/degraded/asset-status fields.

## Provider truth

- Runtime state comes from readiness + provider-resolution.
- GenX invalid model is surfaced as `model_invalid`.
- Qwen state is surfaced as `fallback_available` when key exists.
- Hugging Face missing token is surfaced as `missing_token`.
- Firecrawl status is surfaced via readiness and debug test.
