# MARKETING LOGIN REJECTION CRASH AUDIT

**Date:** 2026-05-20  
**Repo:** sharetheherbman-debug/Amarktai-Marketing  
**Severity:** P0 – Production regression  

---

## Root Cause: Login Crash After Content Rejection

### 1. AuthProvider cleared session on ALL errors

**File:** `app/src/components/auth/AuthProvider.tsx`

**Before (bug):**
```typescript
authFetch<AuthUser>('/users/me', undefined, stored)
  .then(...)
  .catch(() => {
    clearSession();   // ← triggered on ANY error, including 500
    setToken(null);
    setUser(null);
  })
```

**After (fixed):**
```typescript
fetch('/api/v1/users/me', { headers: { Authorization: `Bearer ${tok}` } })
  .then(async (res) => {
    if (res.ok) { /* keep session */ }
    else if (res.status === 401 || res.status === 403) {
      clearSession(); // only on real auth failure
    }
    // 500/network errors → keep session, user lands in dashboard
  })
  .catch(() => { /* network error — keep session */ })
```

**Impact:** Any transient server error (500, DB hiccup, OOM, restart) after the
rejection background task ran would trigger `clearSession()`, wiping the stored
token. The user appeared "logged out" but their account was intact.

---

### 2. Content Rejection Background Task: DB Connection Risk

**File:** `backend/app/api/v1/endpoints/content.py`

The old `reject_content` endpoint queued `_regenerate_content_after_rejection`
as a background task. This task:

- Created a new `SessionLocal()` in an async context
- Called sync SQLAlchemy queries in an async background task
- Could leave DB connections unclosed if an exception occurred before `finally`

**Fix:** Replaced with safer `_regen_after_rejection` that:
- Uses try/except/finally with guaranteed `regen_db.close()`
- Logs all errors but never propagates them
- Only runs when `regenerate=True` is explicitly passed

---

### 3. Dashboard Loading Was Not Isolated

**File:** `app/src/app/dashboard/page.tsx`

**Before:**
```typescript
const [readinessData, content] = await Promise.all([
  settingsApi.getReadiness(),
  contentApi.getAll(),   // if this 500s → catch sets readiness=null
]);
const libraryItems = await contentApi.listItems();  // never reached
```

**After (fixed):**
Each API call has its own try/catch. One failure cannot prevent others from loading.

---

### 4. Content Library Serialization Could Crash on Bad Row

**File:** `backend/app/api/v1/endpoints/content.py` → `list_content_items`

**Before:** `payload = [_content_item_payload(item) for item in rows]`  
A single malformed row raised an exception → 500 → dashboard crash → logout loop.

**After:** Each row is serialized in a try/except. Bad rows get a safe stub with
`degraded: true`. The list never returns a 500 due to a single bad record.

---

## Verification

- Login works before and after content rejection: ✅
- Dashboard loads even if content library has a bad row: ✅  
- `scripts/test_login_after_content_rejection.sh` added for gate testing

---

## What Remains

- Rate-limiting on `/users/me` to prevent brute-force token probing
- Structured error logging with request IDs for distributed tracing
