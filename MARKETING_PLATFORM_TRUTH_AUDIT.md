# Marketing Platform Truth Audit

## Truth contract now enforced
A platform is treated as connected only when all are true:
1. Integration row exists
2. `is_connected=true`
3. `encrypted_access_token` exists
4. Access token decrypts
5. Token is not expired (if expiry exists)
6. Required scopes are present
7. Required target fields (page/channel/etc.) are present

## Platform status taxonomy
- `oauth_app_not_configured` → action `Configure OAuth app`
- `needs_connection` → action `Connect account`
- `generation_only` → action `Generation only`
- `ready_to_post` → action `Manage connection`

## Visibility rule
- All 12 platforms remain visible in catalog and Integrations UI
- Generation remains available even when posting is blocked
