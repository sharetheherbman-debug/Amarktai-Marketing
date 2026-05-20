# Marketing Provider Reset Audit

## Implemented reset endpoints
- `DELETE /api/v1/settings/api-keys/{key_name}?confirm=true`
- `DELETE /api/v1/settings/api-keys?confirm=true`
- `POST /api/v1/settings/api-keys/reset-all`
- `DELETE /api/v1/integrations/{platform}?confirm=true`
- `POST /api/v1/integrations/reset-all`
- `POST /api/v1/settings/reset-provider-state`
- `POST /api/v1/settings/reset-launch-state`

## Safety rules enforced
- Owner-scoped only (current authenticated user)
- No user account deletion
- No secret values logged
- Count payloads returned: `keys_deleted`, `integrations_deleted`, `mappings_deleted`, `tests_cleared`

## Frontend reset controls
- Integrations page Danger Zone includes:
  - Reset all provider keys
  - Reset all social connections
  - Reset provider test state
  - Per-provider key removal
