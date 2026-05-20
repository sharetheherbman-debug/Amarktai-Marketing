# Marketing Content Preview & Regeneration Audit

## New endpoints
- `POST /api/v1/content/preview`
- `POST /api/v1/content/items/{id}/regenerate`

## Response/metadata improvements
- Added preview fields: `preview_title`, `preview_summary`
- Added quality/variation fields:
  - `variation_seed`
  - `uniqueness_score`
  - `business_grounding_score`
  - `hashtag_relevance_score`
  - `creative_relevance_score`
  - `warnings`
- Regeneration links ancestry with `parent_content_id`

## Duplicate signal
- Similarity check against recent same-business+platform items
- Marks `needs_review_duplicate` when similarity is high
