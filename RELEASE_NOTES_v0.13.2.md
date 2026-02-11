# Release Notes — v0.13.2: Auth UI Wiring

**Date**: 2026-02-10

## Overview

v0.13.2 wires two existing but unused authentication components into the frontend UI. Users can now sign in/up from the header and are redirected to login when accessing protected pages.

## Bug Fixes

### 1. UserMenu Added to Header

**Problem**: The `UserMenu` component (Sign In / Sign Up buttons for guests, avatar dropdown for logged-in users) was fully built at `components/auth/UserMenu.tsx` but never rendered anywhere in the app. Users had no visible way to access the login page.

**Fix** (`frontend/components/layout/Header.tsx`):
- Import and render `<UserMenu />` in the desktop header (right section, next to theme toggle)
- Render `<UserMenu />` in the mobile slide-down menu

**Before**: No login/signup buttons visible anywhere
**After**: "Sign In" / "Sign Up" buttons in header when logged out; avatar dropdown with Profile, Settings, Sign Out when logged in

### 2. ProtectedRoute on /projects Page

**Problem**: The `/projects` page fetched data from the API without checking authentication first. Unauthenticated users saw the page skeleton but got 401 errors from the backend, with no indication they needed to log in.

**Fix** (`frontend/app/projects/page.tsx`):
- Wrap entire page with `<ProtectedRoute>` component
- Unauthenticated users are now redirected to `/auth/login`
- Shows loading spinner while checking auth state
- In development mode (Supabase not configured), pages render without auth

**Before**: 401 API errors with no redirect to login
**After**: Automatic redirect to `/auth/login` → login → redirect back to `/projects`

## Files Changed

| File | Lines Changed | Description |
|------|---------------|-------------|
| `frontend/components/layout/Header.tsx` | +6 / -4 | Import UserMenu, add to desktop + mobile |
| `frontend/app/projects/page.tsx` | +4 / -1 | Import ProtectedRoute, wrap page |

## Auth Flow (Now Complete)

```
User visits /projects (unauthenticated)
  → ProtectedRoute detects no session
  → Redirect to /auth/login
  → User clicks "Sign In with Google" (or email/password)
  → Supabase OAuth → redirect back with #access_token
  → AuthProvider picks up session
  → ProtectedRoute allows access
  → /projects page loads with API calls including Bearer token
```

## Deployment

| Service | Platform | Action |
|---------|----------|--------|
| Frontend | Vercel | Auto-deploy on push to origin |
| Backend | Render (Docker) | **No backend changes** — no deploy needed |

## Verification Checklist

- [ ] Header shows "Sign In / Sign Up" when not logged in
- [ ] Clicking "Sign In" navigates to `/auth/login`
- [ ] `/projects` redirects to `/auth/login` when not authenticated
- [ ] After login, `/projects` loads with project list
- [ ] Header shows avatar dropdown when logged in
- [ ] "Sign Out" in dropdown clears session and returns to landing page
