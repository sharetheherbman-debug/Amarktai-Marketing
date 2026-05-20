# Marketing Product Flow Audit

## Dashboard route audit

| Route | Visible in nav | Production-ready | Notes |
| --- | --- | --- | --- |
| `/dashboard` | Yes | Yes | Command center with readiness, first-run checklist, Add Business CTA, selected business actions, and recent content |
| `/dashboard/businesses` | Yes | Yes | Business list with empty state, analyze action, detail links, and Add Business CTA |
| `/dashboard/businesses/new` | CTA only | Yes | Business-first create flow supporting name-only, URL-only, or both |
| `/dashboard/businesses/:id` | From list/selector | Yes | Business detail with analysis summary and generation actions |
| `/dashboard/content` | Yes | Yes | Business-aware Content Studio with empty state, selectors, generate, and generate-all |
| `/dashboard/scheduler` | Yes | Yes | Truthful scheduler with real scheduled content and clean empty state |
| `/dashboard/analytics` | Yes | Partial | Analytics page remains available; production flow does not depend on it |
| `/dashboard/integrations` | Yes | Yes | Editable home for provider keys and social OAuth readiness |
| `/dashboard/settings` | Yes | Yes | Minimal settings/status page without duplicate provider/platform editors |

## Exact happy path

1. Login
2. Add Business (name-only, URL-only, or both)
3. Analyze Website
4. Generate Content
5. Review / Schedule

## Flow truths enforced

- UI copy uses production wording (no user-facing beta labels)
- Content generation requires a real business profile
- Social OAuth is presented as posting-only readiness
- Missing OAuth and non-implemented posting are shown as disabled, truthful states
- Scheduler view only shows real scheduled content or truthful empty state

## Remaining production blockers

- GenX provider failing or missing in runtime
- Firecrawl provider failing or missing in runtime
- OAuth app credentials not configured for posting
- Automatic posting worker/runtime not configured
