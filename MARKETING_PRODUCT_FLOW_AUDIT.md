# Marketing Product Flow Audit

## Dashboard route audit

| Route | Visible in nav | Beta-ready | Notes |
| --- | --- | --- | --- |
| `/dashboard` | Yes | Yes | Command center with readiness, first-run checklist, Add Business CTA, selected business actions, and recent content |
| `/dashboard/businesses` | Yes | Yes | Business list with empty state, analyze action, detail links, and Add Business CTA |
| `/dashboard/businesses/new` | CTA only | Yes | Business-first create flow supporting name-only, URL-only, or both |
| `/dashboard/businesses/:id` | From list/selector | Yes | Business detail with analysis summary and generation actions |
| `/dashboard/content` | Yes | Yes | Business-aware Content Studio with empty state, selectors, generate, and generate-all |
| `/dashboard/scheduler` | Yes | Partial beta-ready | Review/schedule destination remains in flow; not rewritten here |
| `/dashboard/analytics` | Yes | Partial beta-ready | Kept visible for beta reviewers |
| `/dashboard/integrations` | Yes | Yes | Only editable home for provider keys and social OAuth |
| `/dashboard/settings` | Yes | Yes | Minimal settings/status page without duplicate provider/platform editors |
| `/dashboard/approval` | No | Partial beta-ready | Hidden from primary nav; reachable from Content Studio approval action |
| `/dashboard/webapps` | No | Alias only | Redirect/legacy alias to Businesses |
| `/dashboard/webapps/new` | No | Alias only | Redirect/legacy alias to Add Business |
| `/dashboard/webapps/:id` | No | Alias only | Legacy alias to Business detail |
| `/dashboard/webapps/edit/:id` | No | No | Legacy maintenance route hidden from normal beta flow |
| `/dashboard/engagement` | No | No | Hidden from normal beta flow |
| `/dashboard/tools` | No | No | Hidden from normal beta flow |
| `/dashboard/leads` | No | No | Hidden from normal beta flow |
| `/dashboard/groups` | No | No | Hidden from normal beta flow |
| `/dashboard/blog` | No | No | Hidden from normal beta flow |
| `/dashboard/admin` | No | No | Hidden from normal beta flow |

## Hidden or removed from normal beta navigation

- Platforms
- Engagement
- AI Tools
- Leads
- Groups
- Blog
- Admin
- Legacy webapps management paths
- Approval Queue remains accessible only from workflow actions, not the primary nav

## Exact happy path

1. Login
2. Dashboard shows **Add Business** immediately if no business exists
3. User adds a business with name only, URL only, or both
4. Dashboard and Businesses route expose the selected business clearly
5. User clicks **Analyze Website** when a URL exists or proceeds with manual profile data when it does not
6. User opens **Content Studio** and generates content for one platform or all launch platforms
7. User reviews the generated drafts and moves to **Calendar / Scheduler** or **Approval Queue**

## Flow truths enforced by this pass

- User-facing copy says **Business**, not **Webapp**
- Content generation requires a real business profile and no longer assumes a hidden default
- Social OAuth is presented as posting-only, not generation-only
- Readiness is shown as degraded beta vs full readiness
- Settings no longer duplicates provider/social credential forms
- Integrations owns provider keys and social posting connections
- Unsupported active platform cards are removed from active Integrations UI

## Remaining full go-live blockers

- GenX provider test failing or missing
- Firecrawl provider test failing or missing
- Social posting OAuth not configured for the platforms that need posting
- Automatic posting worker not verified/active
