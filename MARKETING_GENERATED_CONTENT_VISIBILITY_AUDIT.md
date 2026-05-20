# Marketing Generated Content Visibility Audit

## Contract
- Generated content must be visible immediately.
- Generated content must survive refresh and be queryable later.
- Pack outputs must persist and appear in content library lists.

## Implemented API Paths
- `GET /api/v1/content/items`
- `GET /api/v1/content/items/{id}`
- `GET /api/v1/content/webapp/{webapp_id}`
- `DELETE /api/v1/content/items/{id}?confirm=true`
- `POST /api/v1/content/items/{id}/schedule`
- `POST /api/v1/content/items/{id}/duplicate`
- `POST /api/v1/content/items/{id}/improve`

## UI Paths Using Persisted Data
- `/dashboard/content` (Content Studio + Content Library)
- `/dashboard/businesses/:id` (business-specific drafts, pack/media metadata, quick actions)
- `/dashboard` (recent generated items and media job counts)

## Gate Script
- `scripts/test_generated_content_visibility.sh` validates:
  1. generate content returns id
  2. item fetch by id
  3. business list includes generated item
  4. pack generation persists additional items
  5. delete removes item from list
