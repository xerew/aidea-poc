# User Management & Content Creator Access Request — Design Spec

## Goal

Two related features shipped as one implementation:

1. **Admin user management** — admins can view all users and change their role (teacher / content_creator / admin) from a dedicated admin page.
2. **Content Creator access request** — any teacher can submit a request (with a message) to become a content creator; admins approve or deny from the same admin page; denied users see the reason on their profile and as a one-time dismissable banner.

---

## Data Model

### New model: `AccessRequest` (app: `hub`)

| Field | Type | Constraints |
|-------|------|-------------|
| `user` | `ForeignKey(User, CASCADE)` | related_name `access_requests` |
| `message` | `TextField` | required; why the user wants CC access |
| `status` | `CharField(20, choices)` | `pending` / `approved` / `denied`; default `pending` |
| `denial_reason` | `TextField` | blank=True |
| `denial_seen` | `BooleanField` | default `False`; set True when user dismisses banner |
| `created_at` | `DateTimeField(auto_now_add=True)` | |
| `reviewed_at` | `DateTimeField(null=True, blank=True)` | set on approve/deny |
| `reviewed_by` | `ForeignKey(User, SET_NULL, null=True, blank=True)` | related_name `reviewed_requests` |

**Constraint:** only one `pending` request per user (enforced in the serializer; old denied/approved requests remain in history).

**On approve:** `status → approved`, `user.profile.user_type → content_creator`, `reviewed_by`, `reviewed_at` — all in `transaction.atomic()`.

---

## Permissions

New `IsAdmin` permission class in `hub/views/permissions.py`:

```python
class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, 'profile')
            and request.user.profile.user_type == UserProfile.UserType.ADMIN
        )
```

---

## Backend API

### Admin — user management

| Method | URL | Permission | Request | Response |
|--------|-----|------------|---------|----------|
| `GET` | `/api/admin/users/` | `IsAdmin` | — | list of `{id, username, first_name, last_name, email, user_type, avatar_initials}` |
| `PATCH` | `/api/admin/users/<id>/role/` | `IsAdmin` | `{user_type}` | updated user object; 400 if invalid role |

An admin is **not** allowed to change their own role via the API (400 with `"You cannot change your own role."`).

### Admin — access requests

| Method | URL | Permission | Request | Response |
|--------|-----|------------|---------|----------|
| `GET` | `/api/admin/access-requests/` | `IsAdmin` | `?status=pending` (optional filter) | list of request objects with nested user info |
| `PATCH` | `/api/admin/access-requests/<id>/` | `IsAdmin` | `{action: "approve"}` or `{action: "deny", denial_reason: "..."}` | updated request; 400 if already reviewed or denial_reason missing on deny |

Approve logic (atomic, triggered by `action=approve`): set `status=approved`, `reviewed_by`, `reviewed_at`; set `user.profile.user_type = content_creator`.

Deny logic (triggered by `action=deny`): requires non-empty `denial_reason`; set `status=denied`, `denial_reason`, `reviewed_by`, `reviewed_at`; `denial_seen=False`.

### User-facing — access requests

| Method | URL | Permission | Request | Response |
|--------|-----|------------|---------|----------|
| `GET` | `/api/access-requests/mine/` | `IsAuthenticated` | — | latest request `{id, status, message, denial_reason, denial_seen, created_at}` or `null` |
| `POST` | `/api/access-requests/` | `IsAuthenticated` | `{message}` | created request (201); 400 if pending request already exists |
| `DELETE` | `/api/access-requests/<id>/` | `IsAuthenticated` (own) | — | 204; 400 if not pending |
| `PATCH` | `/api/access-requests/<id>/seen/` | `IsAuthenticated` (own) | — | 200; sets `denial_seen=True` |

---

## Frontend

### New files

| File | Purpose |
|------|---------|
| `frontend/src/pages/AdminPage.jsx` | Admin users + access requests page |
| `frontend/src/pages/AdminPage.css` | Styles |
| `frontend/src/hooks/useAccessRequest.js` | Fetches `/access-requests/mine/`; used by Layout (banner) and ProfilePage (section) |

### Modified files

| File | Change |
|------|--------|
| `frontend/src/App.jsx` | Add `AdminRoute` guard; add `/admin/users` route |
| `frontend/src/components/layout/Sidebar.jsx` | Add "Admin" nav item (Shield icon) for admins; remove "My Pathway" for admins (same pattern as content creators) |
| `frontend/src/components/layout/Layout.jsx` | Mount `useAccessRequest` hook; render denial banner |
| `frontend/src/pages/ProfilePage.jsx` | Add "Content Creator Access" section (teachers only) |

### Route guard

```jsx
function AdminRoute({ element }) {
  const { user } = useAuth()
  return user?.profile?.user_type === 'admin' ? element : <Navigate to="/" replace />
}
```

Route: `<Route path="/admin/users" element={<AdminRoute element={<AdminPage />} />} />`

### AdminPage — two tabs: "Users" and "Access Requests"

**Users tab:**
- Table: avatar initials chip, full name, username, email, role `<select>` dropdown
- Changing the dropdown calls `PATCH /admin/users/<id>/role/` immediately; shows inline success/error feedback
- The row for the currently logged-in admin is read-only (dropdown disabled, "You" badge)
- Sorted by: admins first, then content creators, then teachers; within each group alphabetically

**Access Requests tab:**
- Pending requests shown first (card layout): requester name + initials, message (expandable if long), submitted date, **Approve** and **Deny** buttons
- Deny button reveals an inline textarea for the denial reason + Confirm Deny button
- Approved/denied requests shown below in a collapsible "Past Requests" section (status badge, reviewer name, reviewed date)
- Empty state: "No pending requests"

### `useAccessRequest` hook

```
useAccessRequest() → { request, loading, submit, cancel, dismiss, refetch }
```

- Fetches `GET /access-requests/mine/` once on mount (called from `Layout`)
- `submit(message)` → POST; `cancel(id)` → DELETE; `dismiss(id)` → PATCH seen
- Shared via React Context (`AccessRequestContext`) so `Layout` (banner) and `ProfilePage` (section) read from the same fetch — no double requests. The provider wraps `Layout` only (not the whole app), so unauthenticated pages are unaffected

### Denial banner (Layout)

Rendered at the top of the main content area when `request?.status === 'denied' && !request?.denial_seen`:

```
⚠ Your Content Creator access request was denied: "[denial_reason]"  [×]
```

Clicking × calls `dismiss(id)` and hides the banner immediately (optimistic).

### Profile page — "Content Creator Access" section

Shown only when `user?.profile?.user_type === 'teacher'`.

| State | UI |
|-------|-----|
| `request === null` | Brief blurb + "Request Content Creator Access" button → inline textarea form |
| `request.status === 'pending'` | "Request pending" badge, submitted date, Cancel button |
| `request.status === 'denied'` | Red box with denial reason, "Request Again" button (resets to form; does not auto-delete old request — user submits a fresh one) |

---

## Migration

Migration `0018_accessrequest` — creates the `AccessRequest` table with all fields and constraints above.

---

## Tests

**Backend (`hub/tests/test_admin.py`):**
1. Non-admin cannot access `GET /admin/users/` → 403
2. Admin lists all users → 200, correct fields
3. Admin changes role → 200, profile updated
4. Admin cannot change own role → 400
5. Invalid role value → 400

**Backend (`hub/tests/test_access_requests.py`):**
1. Teacher submits request → 201, `status=pending`
2. Second submit while pending → 400
3. Teacher cancels pending request → 204
4. Cannot cancel non-pending request → 400
5. Admin approves → 200, `user_type=content_creator`
6. Admin denies with reason → 200, `status=denied`, `denial_reason` set
7. Teacher dismisses denial → 200, `denial_seen=True`
8. `GET /access-requests/mine/` returns latest request

---

## Out of scope (future)

- Email notifications on approve/deny
- Request history list visible to users (only latest shown)
- Pagination on admin users list
