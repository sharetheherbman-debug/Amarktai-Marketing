# Marketing 12 Platform Audit

## Broken before restore
- Backend launch platform source of truth only exposed 8 platforms in `backend/app/services/platform_catalog.py`.
- Integrations UI only rendered 8 local cards in `app/src/app/integrations/page.tsx`.
- Content Studio only rendered 8 selector options in `app/src/components/dashboard/ContentStudio.tsx`.
- Business detail quick actions only rendered 4 platform generate buttons in `app/src/app/businesses/detail/page.tsx`.

## Restored
- Backend source of truth now defines all 12 in `backend/app/services/platform_catalog.py`.
- `GET /api/v1/integrations/platforms` now iterates the 12-platform catalog.
- Each platform response now includes `action_label` and `analytics_supported` fields.
- Platform posting truth now covers all 12 in `backend/app/services/posting_readiness.py`.
- Platform rules now cover Threads, Bluesky, Telegram, and Snapchat in `backend/app/services/social_rules.py`.
- Platform intelligence styles now cover all 12 in `backend/app/services/platform_intelligence.py`.
- Frontend shared source of truth now lives in `app/src/lib/platformCatalog.ts`.
- Integrations, Content Studio, and Business detail now use the shared 12-platform catalog.
- Content Studio now includes offer/product field forwarded to generation APIs.

## Endpoints verified in code
- `GET /api/v1/integrations/platforms`
- `GET /api/v1/platform-intelligence`
- `POST /api/v1/content/generate`
- `POST /api/v1/content/generate-all`
- `POST /api/v1/content/generate-pack`
- `GET /api/v1/capabilities`

## Remaining
- Posting is still truthful/degraded for several platforms; they appear as generation-only or OAuth-not-configured instead of fake-ready.

## Go-live status
- LIMITED: 12-platform generation visibility restored; posting remains platform-dependent and truthful.
