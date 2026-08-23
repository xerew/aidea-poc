# User Management & Content Creator Access Request Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an admin user-management page (role promotion/demotion) and a teacher-initiated Content Creator access request flow with admin approve/deny and in-app denial notification.

**Architecture:** A new `AccessRequest` model stores requests with status/denial fields. Six new backend endpoints cover user listing, role patching, request submission/cancellation/dismissal, and admin review. The frontend introduces an `AccessRequestContext` shared between `Layout` (denial banner) and `ProfilePage` (CC access section), plus an `AdminPage` with two tabs (Users, Access Requests).

**Tech Stack:** Django 5.1, DRF, React 19, react-router-dom v7, lucide-react, Axios

## Global Constraints

- Backend runner: `cd backend && .venv\Scripts\python.exe manage.py ...`
- Frontend lint: `cd frontend && npm run lint` — clean after every task
- Backend tests: run `cd backend && .venv\Scripts\python.exe manage.py test hub --verbosity=1` after every task — all must pass
- `IsAdmin` permission: `user.profile.user_type == 'admin'`
- An admin cannot change their own role (HTTP 400: `"You cannot change your own role."`)
- Approve is atomic: `AccessRequest.status → approved` + `UserProfile.user_type → content_creator` in one `transaction.atomic()`
- Deny requires non-empty `denial_reason`; sets `denial_seen = False`
- Only one pending request per user at a time (serializer enforces this)
- Icons: `lucide-react` only
- No extra features beyond spec

---

## File Map

| File | Change |
|------|--------|
| `backend/hub/models/access_request.py` | New — `AccessRequest` model |
| `backend/hub/models/__init__.py` | Export `AccessRequest` |
| `backend/hub/views/permissions.py` | Add `IsAdmin` |
| `backend/hub/serializers/admin.py` | New — all admin + access request serializers |
| `backend/hub/views/admin.py` | New — admin user management + request review views |
| `backend/hub/views/access_requests.py` | New — user-facing access request views |
| `backend/hub/views/__init__.py` | Export new views |
| `backend/hub/urls.py` | Add 8 new routes |
| `backend/hub/tests/test_admin.py` | New — 5 tests |
| `backend/hub/tests/test_access_requests.py` | New — 8 tests |
| `frontend/src/context/AccessRequestContext.jsx` | New — shared hook + provider |
| `frontend/src/components/layout/Layout.jsx` | Wrap with `AccessRequestProvider`; add denial banner |
| `frontend/src/components/layout/Layout.css` | Add `.denial-banner` styles |
| `frontend/src/pages/AdminPage.jsx` | New |
| `frontend/src/pages/AdminPage.css` | New |
| `frontend/src/App.jsx` | Add `AdminRoute` guard + `/admin/users` route |
| `frontend/src/components/layout/Sidebar.jsx` | Add "Admin" nav item |
| `frontend/src/pages/ProfilePage.jsx` | Add `ContentCreatorAccessSection` |
| `frontend/src/pages/ProfilePage.css` | Add `cc-*` and textarea styles |

---

### Task 1: `AccessRequest` model + migration

**Files:**
- Create: `backend/hub/models/access_request.py`
- Modify: `backend/hub/models/__init__.py`

**Interfaces:**
- Produces: `AccessRequest` model importable as `from hub.models import AccessRequest`
- Fields: `id`, `user` (FK→User), `message`, `status` (`pending`/`approved`/`denied`), `denial_reason`, `denial_seen`, `created_at`, `reviewed_at`, `reviewed_by` (FK→User null)

- [ ] **Step 1: Create `backend/hub/models/access_request.py`**

```python
from django.contrib.auth.models import User
from django.db import models


class AccessRequest(models.Model):
    class Status(models.TextChoices):
        PENDING  = 'pending',  'Pending'
        APPROVED = 'approved', 'Approved'
        DENIED   = 'denied',   'Denied'

    user          = models.ForeignKey(User, on_delete=models.CASCADE, related_name='access_requests')
    message       = models.TextField()
    status        = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    denial_reason = models.TextField(blank=True)
    denial_seen   = models.BooleanField(default=False)
    created_at    = models.DateTimeField(auto_now_add=True)
    reviewed_at   = models.DateTimeField(null=True, blank=True)
    reviewed_by   = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_requests',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} — {self.status}'
```

- [ ] **Step 2: Export from `backend/hub/models/__init__.py`**

Add the import line and add to `__all__`:

```python
from .access_request import AccessRequest
```

Add `'AccessRequest',` to `__all__`.

- [ ] **Step 3: Generate + verify the migration**

```
cd backend
.venv\Scripts\python.exe manage.py makemigrations hub --name access_request
```

Expected: creates `backend/hub/migrations/0018_access_request.py`.

- [ ] **Step 4: Apply migration**

```
cd backend
.venv\Scripts\python.exe manage.py migrate
```

Expected: `Applying hub.0018_access_request... OK`

- [ ] **Step 5: Smoke-test the model**

```
cd backend
.venv\Scripts\python.exe manage.py shell -c "from hub.models import AccessRequest; print(AccessRequest._meta.fields)"
```

Expected: prints list of fields including `status`, `denial_reason`, `denial_seen`.

- [ ] **Step 6: Commit**

```
git add backend/hub/models/access_request.py backend/hub/models/__init__.py backend/hub/migrations/0018_access_request.py
git commit -m "feat: add AccessRequest model"
```

---

### Task 2: `IsAdmin` permission + admin user management API + tests

**Files:**
- Modify: `backend/hub/views/permissions.py`
- Create: `backend/hub/serializers/admin.py`
- Create: `backend/hub/views/admin.py`
- Modify: `backend/hub/views/__init__.py`
- Modify: `backend/hub/urls.py`
- Create: `backend/hub/tests/test_admin.py`

**Interfaces:**
- Produces: `GET /api/admin/users/` (IsAdmin), `PATCH /api/admin/users/<id>/role/` (IsAdmin)
- Produces: `IsAdmin` permission class in `hub.views.permissions`
- `AdminUserSerializer` fields: `id`, `username`, `first_name`, `last_name`, `email`, `user_type`, `avatar_initials`

- [ ] **Step 1: Write failing tests in `backend/hub/tests/test_admin.py`**

```python
from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from hub.models import UserProfile


def make_user(username, user_type, password='pass1234'):
    u = User.objects.create_user(username=username, password=password, email=f'{username}@test.com')
    UserProfile.objects.create(user=u, user_type=user_type, avatar_initials=username[:2].upper())
    return u


class AdminUserListTest(APITestCase):
    def setUp(self):
        self.admin  = make_user('admin1',   UserProfile.UserType.ADMIN)
        self.teacher = make_user('teacher1', UserProfile.UserType.TEACHER)

    def test_non_admin_cannot_list_users(self):
        self.client.force_authenticate(self.teacher)
        res = self.client.get('/api/admin/users/')
        self.assertEqual(res.status_code, 403)

    def test_admin_lists_all_users(self):
        self.client.force_authenticate(self.admin)
        res = self.client.get('/api/admin/users/')
        self.assertEqual(res.status_code, 200)
        ids = [u['id'] for u in res.data]
        self.assertIn(self.admin.id, ids)
        self.assertIn(self.teacher.id, ids)
        self.assertIn('user_type', res.data[0])
        self.assertIn('avatar_initials', res.data[0])


class AdminUserRoleTest(APITestCase):
    def setUp(self):
        self.admin   = make_user('admin2',   UserProfile.UserType.ADMIN)
        self.teacher = make_user('teacher2', UserProfile.UserType.TEACHER)

    def test_admin_changes_role(self):
        self.client.force_authenticate(self.admin)
        res = self.client.patch(
            f'/api/admin/users/{self.teacher.id}/role/',
            {'user_type': 'content_creator'}, format='json',
        )
        self.assertEqual(res.status_code, 200)
        self.teacher.profile.refresh_from_db()
        self.assertEqual(self.teacher.profile.user_type, 'content_creator')

    def test_admin_cannot_change_own_role(self):
        self.client.force_authenticate(self.admin)
        res = self.client.patch(
            f'/api/admin/users/{self.admin.id}/role/',
            {'user_type': 'teacher'}, format='json',
        )
        self.assertEqual(res.status_code, 400)

    def test_invalid_role_returns_400(self):
        self.client.force_authenticate(self.admin)
        res = self.client.patch(
            f'/api/admin/users/{self.teacher.id}/role/',
            {'user_type': 'superuser'}, format='json',
        )
        self.assertEqual(res.status_code, 400)
```

- [ ] **Step 2: Run tests — expect 5 failures**

```
cd backend
.venv\Scripts\python.exe manage.py test hub.tests.test_admin --verbosity=2
```

Expected: 5 errors/failures (endpoints do not exist yet).

- [ ] **Step 3: Add `IsAdmin` to `backend/hub/views/permissions.py`**

Append to the existing file (keep `IsTeacher` and `IsContentCreator` unchanged):

```python
class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, 'profile')
            and request.user.profile.user_type == UserProfile.UserType.ADMIN
        )
```

- [ ] **Step 4: Create `backend/hub/serializers/admin.py`**

```python
from django.contrib.auth.models import User
from rest_framework import serializers

from hub.models import AccessRequest, UserProfile


class AdminUserSerializer(serializers.ModelSerializer):
    user_type       = serializers.CharField(source='profile.user_type')
    avatar_initials = serializers.CharField(source='profile.avatar_initials')

    class Meta:
        model  = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email',
                  'user_type', 'avatar_initials']


class AdminUserRoleSerializer(serializers.Serializer):
    user_type = serializers.ChoiceField(choices=UserProfile.UserType.choices)


class AccessRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model  = AccessRequest
        fields = ['id', 'status', 'message', 'denial_reason', 'denial_seen', 'created_at']
        read_only_fields = ['id', 'status', 'denial_reason', 'denial_seen', 'created_at']


class AccessRequestAdminSerializer(serializers.ModelSerializer):
    username        = serializers.CharField(source='user.username',                read_only=True)
    first_name      = serializers.CharField(source='user.first_name',              read_only=True)
    last_name       = serializers.CharField(source='user.last_name',               read_only=True)
    avatar_initials = serializers.CharField(source='user.profile.avatar_initials', read_only=True)

    class Meta:
        model  = AccessRequest
        fields = ['id', 'username', 'first_name', 'last_name', 'avatar_initials',
                  'message', 'status', 'denial_reason', 'created_at', 'reviewed_at']
```

- [ ] **Step 5: Create `backend/hub/views/admin.py`**

```python
from django.contrib.auth.models import User

from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import AccessRequest, UserProfile
from hub.serializers.admin import (
    AccessRequestAdminSerializer,
    AdminUserRoleSerializer,
    AdminUserSerializer,
)
from hub.views.permissions import IsAdmin


ROLE_ORDER = {
    UserProfile.UserType.ADMIN:           0,
    UserProfile.UserType.CONTENT_CREATOR: 1,
    UserProfile.UserType.TEACHER:         2,
}


class AdminUserListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        users = (
            User.objects
            .select_related('profile')
            .filter(profile__isnull=False)
        )
        serializer = AdminUserSerializer(users, many=True)
        data = sorted(
            serializer.data,
            key=lambda u: (ROLE_ORDER.get(u['user_type'], 9), u['first_name'], u['last_name']),
        )
        return Response(data)


class AdminUserRoleView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        if pk == request.user.id:
            return Response({'error': 'You cannot change your own role.'}, status=400)
        try:
            user = User.objects.select_related('profile').get(pk=pk)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=404)
        serializer = AdminUserRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.profile.user_type = serializer.validated_data['user_type']
        user.profile.save()
        return Response(AdminUserSerializer(user).data)


class AdminAccessRequestListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        qs = AccessRequest.objects.select_related('user__profile').all()
        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return Response(AccessRequestAdminSerializer(qs, many=True).data)


class AdminAccessRequestReviewView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        from django.db import transaction
        from django.utils import timezone

        try:
            req = AccessRequest.objects.select_related('user__profile').get(pk=pk)
        except AccessRequest.DoesNotExist:
            return Response({'error': 'Not found.'}, status=404)

        if req.status != AccessRequest.Status.PENDING:
            return Response({'error': 'This request has already been reviewed.'}, status=400)

        action = request.data.get('action')

        if action == 'approve':
            with transaction.atomic():
                req.status      = AccessRequest.Status.APPROVED
                req.reviewed_by = request.user
                req.reviewed_at = timezone.now()
                req.save()
                req.user.profile.user_type = UserProfile.UserType.CONTENT_CREATOR
                req.user.profile.save()

        elif action == 'deny':
            denial_reason = request.data.get('denial_reason', '').strip()
            if not denial_reason:
                return Response({'error': 'denial_reason is required when denying.'}, status=400)
            req.status        = AccessRequest.Status.DENIED
            req.denial_reason = denial_reason
            req.denial_seen   = False
            req.reviewed_by   = request.user
            req.reviewed_at   = timezone.now()
            req.save()

        else:
            return Response({'error': 'action must be "approve" or "deny".'}, status=400)

        return Response(AccessRequestAdminSerializer(req).data)
```

- [ ] **Step 6: Export new views from `backend/hub/views/__init__.py`**

Add to the existing import block (add a new import line):

```python
from .admin import (
    AdminAccessRequestListView,
    AdminAccessRequestReviewView,
    AdminUserListView,
    AdminUserRoleView,
)
```

Add all four names to `__all__`.

- [ ] **Step 7: Add routes to `backend/hub/urls.py`**

Add to the imports block:

```python
    AdminAccessRequestListView,
    AdminAccessRequestReviewView,
    AdminUserListView,
    AdminUserRoleView,
```

Add to `urlpatterns` (before the authoring section):

```python
    # Admin
    path('admin/users/',                        AdminUserListView.as_view(),           name='admin-users'),
    path('admin/users/<int:pk>/role/',          AdminUserRoleView.as_view(),           name='admin-user-role'),
    path('admin/access-requests/',              AdminAccessRequestListView.as_view(),  name='admin-access-requests'),
    path('admin/access-requests/<int:pk>/',     AdminAccessRequestReviewView.as_view(), name='admin-access-request-review'),
```

- [ ] **Step 8: Run the 5 admin tests — expect all to pass**

```
cd backend
.venv\Scripts\python.exe manage.py test hub.tests.test_admin --verbosity=2
```

Expected: 5 tests, 0 failures.

- [ ] **Step 9: Run full suite — no regressions**

```
cd backend
.venv\Scripts\python.exe manage.py test hub --verbosity=1
```

Expected: all tests pass.

- [ ] **Step 10: Commit**

```
git add backend/hub/views/permissions.py \
        backend/hub/serializers/admin.py \
        backend/hub/views/admin.py \
        backend/hub/views/__init__.py \
        backend/hub/urls.py \
        backend/hub/tests/test_admin.py
git commit -m "feat: add IsAdmin permission + admin user management endpoints"
```

---

### Task 3: Access request API (user-facing + admin review) + tests

**Files:**
- Create: `backend/hub/views/access_requests.py`
- Modify: `backend/hub/views/__init__.py`
- Modify: `backend/hub/urls.py`
- Create: `backend/hub/tests/test_access_requests.py`

**Interfaces:**
- Consumes: `AccessRequest` from `hub.models`, `AccessRequestSerializer` + `AccessRequestAdminSerializer` from `hub.serializers.admin`
- Produces:
  - `GET /api/access-requests/mine/` → `{id, status, message, denial_reason, denial_seen, created_at}` or HTTP 200 with `null`
  - `POST /api/access-requests/` → 201 with request object
  - `DELETE /api/access-requests/<id>/` → 204
  - `PATCH /api/access-requests/<id>/seen/` → 200

- [ ] **Step 1: Write failing tests in `backend/hub/tests/test_access_requests.py`**

```python
from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from hub.models import AccessRequest, UserProfile


def make_user(username, user_type, password='pass1234'):
    u = User.objects.create_user(username=username, password=password, email=f'{username}@test.com')
    UserProfile.objects.create(user=u, user_type=user_type, avatar_initials=username[:2].upper())
    return u


class AccessRequestMineTest(APITestCase):
    def setUp(self):
        self.teacher = make_user('t1', UserProfile.UserType.TEACHER)

    def test_mine_returns_null_when_no_request(self):
        self.client.force_authenticate(self.teacher)
        res = self.client.get('/api/access-requests/mine/')
        self.assertEqual(res.status_code, 200)
        self.assertIsNone(res.data)

    def test_mine_returns_latest_request(self):
        req = AccessRequest.objects.create(user=self.teacher, message='I want access')
        self.client.force_authenticate(self.teacher)
        res = self.client.get('/api/access-requests/mine/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['id'], req.id)
        self.assertEqual(res.data['status'], 'pending')


class AccessRequestSubmitTest(APITestCase):
    def setUp(self):
        self.teacher = make_user('t2', UserProfile.UserType.TEACHER)

    def test_submit_creates_pending_request(self):
        self.client.force_authenticate(self.teacher)
        res = self.client.post('/api/access-requests/', {'message': 'I want to create courses'}, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['status'], 'pending')
        self.assertTrue(AccessRequest.objects.filter(user=self.teacher).exists())

    def test_second_submit_while_pending_returns_400(self):
        AccessRequest.objects.create(user=self.teacher, message='First request')
        self.client.force_authenticate(self.teacher)
        res = self.client.post('/api/access-requests/', {'message': 'Second request'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_cancel_pending_request(self):
        req = AccessRequest.objects.create(user=self.teacher, message='Cancel me')
        self.client.force_authenticate(self.teacher)
        res = self.client.delete(f'/api/access-requests/{req.id}/')
        self.assertEqual(res.status_code, 204)
        req.refresh_from_db()
        self.assertEqual(req.status, AccessRequest.Status.PENDING)
        # it was deleted not updated
        self.assertFalse(AccessRequest.objects.filter(pk=req.id).exists())

    def test_cannot_cancel_approved_request(self):
        req = AccessRequest.objects.create(
            user=self.teacher, message='Already approved', status=AccessRequest.Status.APPROVED,
        )
        self.client.force_authenticate(self.teacher)
        res = self.client.delete(f'/api/access-requests/{req.id}/')
        self.assertEqual(res.status_code, 400)


class AdminAccessRequestReviewTest(APITestCase):
    def setUp(self):
        self.admin   = make_user('adm1', UserProfile.UserType.ADMIN)
        self.teacher = make_user('t3',   UserProfile.UserType.TEACHER)
        self.req = AccessRequest.objects.create(user=self.teacher, message='Please approve me')

    def test_admin_approves_request_and_promotes_user(self):
        self.client.force_authenticate(self.admin)
        res = self.client.patch(
            f'/api/admin/access-requests/{self.req.id}/',
            {'action': 'approve'}, format='json',
        )
        self.assertEqual(res.status_code, 200)
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, 'approved')
        self.teacher.profile.refresh_from_db()
        self.assertEqual(self.teacher.profile.user_type, 'content_creator')

    def test_admin_denies_request_with_reason(self):
        self.client.force_authenticate(self.admin)
        res = self.client.patch(
            f'/api/admin/access-requests/{self.req.id}/',
            {'action': 'deny', 'denial_reason': 'Not enough courses planned.'}, format='json',
        )
        self.assertEqual(res.status_code, 200)
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, 'denied')
        self.assertEqual(self.req.denial_reason, 'Not enough courses planned.')
        self.assertFalse(self.req.denial_seen)

    def test_teacher_dismisses_denial(self):
        self.req.status = AccessRequest.Status.DENIED
        self.req.denial_reason = 'Not ready'
        self.req.save()
        self.client.force_authenticate(self.teacher)
        res = self.client.patch(f'/api/access-requests/{self.req.id}/seen/')
        self.assertEqual(res.status_code, 200)
        self.req.refresh_from_db()
        self.assertTrue(self.req.denial_seen)
```

- [ ] **Step 2: Run tests — expect 8 failures**

```
cd backend
.venv\Scripts\python.exe manage.py test hub.tests.test_access_requests --verbosity=2
```

Expected: 8 failures (views do not exist yet). Note: the cancel test asserts the record is deleted (not status-updated) — `delete()` removes the row.

- [ ] **Step 3: Create `backend/hub/views/access_requests.py`**

```python
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from hub.models import AccessRequest
from hub.serializers.admin import AccessRequestSerializer


class AccessRequestMineView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        req = request.user.access_requests.first()  # ordered by -created_at per model Meta
        if req is None:
            return Response(None)
        return Response(AccessRequestSerializer(req).data)


class AccessRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.access_requests.filter(status=AccessRequest.Status.PENDING).exists():
            return Response({'error': 'You already have a pending request.'}, status=400)
        message = request.data.get('message', '').strip()
        if not message:
            return Response({'error': 'message is required.'}, status=400)
        req = AccessRequest.objects.create(user=request.user, message=message)
        return Response(AccessRequestSerializer(req).data, status=201)


class AccessRequestDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            req = request.user.access_requests.get(pk=pk)
        except AccessRequest.DoesNotExist:
            return Response({'error': 'Not found.'}, status=404)
        if req.status != AccessRequest.Status.PENDING:
            return Response({'error': 'Only pending requests can be cancelled.'}, status=400)
        req.delete()
        return Response(status=204)


class AccessRequestSeenView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            req = request.user.access_requests.get(pk=pk)
        except AccessRequest.DoesNotExist:
            return Response({'error': 'Not found.'}, status=404)
        req.denial_seen = True
        req.save()
        return Response(AccessRequestSerializer(req).data)
```

- [ ] **Step 4: Export new views from `backend/hub/views/__init__.py`**

Add to the imports block:

```python
from .access_requests import (
    AccessRequestDetailView,
    AccessRequestMineView,
    AccessRequestSeenView,
    AccessRequestView,
)
```

Add all four names to `__all__`.

- [ ] **Step 5: Add routes to `backend/hub/urls.py`**

Add to the imports from `.views`:

```python
    AccessRequestDetailView,
    AccessRequestMineView,
    AccessRequestSeenView,
    AccessRequestView,
```

Add to `urlpatterns` (in the admin section, after the admin routes):

```python
    # Access requests (user-facing)
    path('access-requests/mine/',         AccessRequestMineView.as_view(),   name='access-request-mine'),
    path('access-requests/',              AccessRequestView.as_view(),       name='access-request'),
    path('access-requests/<int:pk>/',     AccessRequestDetailView.as_view(), name='access-request-detail'),
    path('access-requests/<int:pk>/seen/', AccessRequestSeenView.as_view(), name='access-request-seen'),
```

- [ ] **Step 6: Run the 8 access request tests — expect all to pass**

```
cd backend
.venv\Scripts\python.exe manage.py test hub.tests.test_access_requests --verbosity=2
```

Expected: 8 tests, 0 failures.

- [ ] **Step 7: Run full suite — no regressions**

```
cd backend
.venv\Scripts\python.exe manage.py test hub --verbosity=1
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```
git add backend/hub/views/access_requests.py \
        backend/hub/views/__init__.py \
        backend/hub/urls.py \
        backend/hub/tests/test_access_requests.py
git commit -m "feat: add user-facing access request endpoints"
```

---

### Task 4: Frontend — `AccessRequestContext` + Layout denial banner

**Files:**
- Create: `frontend/src/context/AccessRequestContext.jsx`
- Modify: `frontend/src/components/layout/Layout.jsx`
- Modify: `frontend/src/components/layout/Layout.css`

**Interfaces:**
- Produces: `AccessRequestProvider` (wraps Layout), `useAccessRequest()` hook
- `useAccessRequest()` → `{ request, loading, submit, cancel, dismiss, refetch }`
- `request` shape: `{id, status, message, denial_reason, denial_seen, created_at}` or `null`
- Denial banner: shown when `request?.status === 'denied' && !request?.denial_seen`

- [ ] **Step 1: Create `frontend/src/context/AccessRequestContext.jsx`**

```jsx
import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import PropTypes from 'prop-types'
import { useAuth } from './AuthContext'
import client from '../api/client'

const AccessRequestContext = createContext(null)

export function AccessRequestProvider({ children }) {
  const { user } = useAuth()
  const [request, setRequest] = useState(null)
  const [loading, setLoading] = useState(false)

  const refetch = useCallback(async () => {
    if (!user) { setRequest(null); return }
    setLoading(true)
    try {
      const { data } = await client.get('/access-requests/mine/')
      setRequest(data)
    } catch {
      setRequest(null)
    } finally {
      setLoading(false)
    }
  }, [user])

  useEffect(() => { refetch() }, [refetch])

  const submit = useCallback(async (message) => {
    const { data } = await client.post('/access-requests/', { message })
    setRequest(data)
    return data
  }, [])

  const cancel = useCallback(async (id) => {
    await client.delete(`/access-requests/${id}/`)
    setRequest(null)
  }, [])

  const dismiss = useCallback(async (id) => {
    await client.patch(`/access-requests/${id}/seen/`)
    setRequest(prev => prev ? { ...prev, denial_seen: true } : prev)
  }, [])

  return (
    <AccessRequestContext.Provider value={{ request, loading, submit, cancel, dismiss, refetch }}>
      {children}
    </AccessRequestContext.Provider>
  )
}

AccessRequestProvider.propTypes = { children: PropTypes.node.isRequired }

// eslint-disable-next-line react-refresh/only-export-components
export function useAccessRequest() {
  return useContext(AccessRequestContext)
}
```

- [ ] **Step 2: Read `frontend/src/components/layout/Layout.jsx` before editing**

Current content:
```jsx
import { Outlet, Navigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import Sidebar from './Sidebar'
import Header from './Header'
import Footer from './Footer'
import './Layout.css'

export default function Layout() {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  return (
    <div className="layout">
      <Sidebar />
      <div className="layout-body">
        <Header />
        <main className="layout-main">
          <Outlet />
        </main>
        <Footer />
      </div>
    </div>
  )
}
```

Replace the entire file with:

```jsx
import { Outlet, Navigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { AccessRequestProvider, useAccessRequest } from '../../context/AccessRequestContext'
import Sidebar from './Sidebar'
import Header from './Header'
import Footer from './Footer'
import './Layout.css'

function DenialBanner() {
  const { request, dismiss } = useAccessRequest()
  if (!request || request.status !== 'denied' || request.denial_seen) return null
  return (
    <div className="denial-banner">
      <span>
        Your Content Creator access request was denied: &quot;{request.denial_reason}&quot;
      </span>
      <button
        className="denial-banner-close"
        onClick={() => dismiss(request.id)}
        aria-label="Dismiss"
      >
        ×
      </button>
    </div>
  )
}

function LayoutInner() {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  return (
    <div className="layout">
      <Sidebar />
      <div className="layout-body">
        <Header />
        <DenialBanner />
        <main className="layout-main">
          <Outlet />
        </main>
        <Footer />
      </div>
    </div>
  )
}

export default function Layout() {
  return (
    <AccessRequestProvider>
      <LayoutInner />
    </AccessRequestProvider>
  )
}
```

- [ ] **Step 3: Add denial banner styles to `frontend/src/components/layout/Layout.css`**

Append to the end of the existing file:

```css
.denial-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  background: #fef2f2;
  border-bottom: 1px solid #fecaca;
  color: #991b1b;
  padding: 0.75rem 2rem;
  font-size: 0.875rem;
}

.denial-banner-close {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.1rem;
  color: #991b1b;
  padding: 0 0.25rem;
  line-height: 1;
  flex-shrink: 0;
}

.denial-banner-close:hover {
  opacity: 0.7;
}
```

- [ ] **Step 4: Run ESLint — expect clean**

```
cd frontend && npm run lint
```

- [ ] **Step 5: Commit**

```
git add frontend/src/context/AccessRequestContext.jsx \
        frontend/src/components/layout/Layout.jsx \
        frontend/src/components/layout/Layout.css
git commit -m "feat: add AccessRequestContext and denial banner in Layout"
```

---

### Task 5: Frontend — Admin page + routing + sidebar

**Files:**
- Create: `frontend/src/pages/AdminPage.jsx`
- Create: `frontend/src/pages/AdminPage.css`
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/components/layout/Sidebar.jsx`

**Interfaces:**
- Consumes: `GET /api/admin/users/`, `PATCH /api/admin/users/<id>/role/`, `GET /api/admin/access-requests/`, `PATCH /api/admin/access-requests/<id>/`
- Produces: `AdminPage` default export; `AdminRoute` guard in App.jsx; Admin sidebar link for `user_type === 'admin'`

- [ ] **Step 1: Create `frontend/src/pages/AdminPage.css`**

```css
.admin-page {
  max-width: 900px;
}

.admin-page-header {
  margin-bottom: 1.25rem;
}

.admin-page-header h1 {
  font-size: 1.5rem;
  font-weight: 700;
  margin: 0;
  color: var(--color-text);
}

/* Tabs */

.admin-tabs {
  display: flex;
  gap: 0;
  border-bottom: 2px solid var(--color-border);
  margin-bottom: 1.5rem;
}

.admin-tab-btn {
  background: none;
  border: none;
  padding: 0.6rem 1.25rem;
  font-size: 0.9375rem;
  font-weight: 500;
  color: var(--color-text-muted);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: color 0.15s, border-color 0.15s;
}

.admin-tab-btn.active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
}

.admin-tab-btn:hover:not(.active) {
  color: var(--color-text);
}

/* Users table */

.admin-users-table-wrap {
  overflow-x: auto;
}

.admin-users-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.admin-users-table th {
  text-align: left;
  font-weight: 600;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text-muted);
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.admin-users-table td {
  padding: 0.65rem 0.75rem;
  border-bottom: 1px solid var(--color-border);
  vertical-align: middle;
}

.admin-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.75rem;
  flex-shrink: 0;
}

.admin-role-cell {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.admin-role-select {
  padding: 0.35rem 0.6rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  background: var(--color-bg);
  color: var(--color-text);
  font-size: 0.875rem;
  cursor: pointer;
}

.admin-role-select:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.admin-you-badge {
  font-size: 0.75rem;
  background: var(--color-border);
  color: var(--color-text-muted);
  padding: 0.2rem 0.5rem;
  border-radius: 999px;
}

.admin-feedback {
  font-size: 0.8rem;
}

.admin-feedback.info    { color: var(--color-primary); }
.admin-feedback.success { color: #16a34a; }
.admin-feedback.error   { color: #dc2626; }

/* Loading / empty */

.admin-loading,
.admin-empty {
  color: var(--color-text-muted);
  font-size: 0.875rem;
  margin: 0;
  padding: 1rem 0;
}

/* Access request cards */

.admin-requests {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.admin-request-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 1.25rem;
}

.admin-request-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.admin-request-name {
  font-weight: 600;
  margin: 0 0 0.15rem;
  font-size: 0.9375rem;
}

.admin-request-meta {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  margin: 0;
}

.admin-request-message {
  font-size: 0.875rem;
  color: var(--color-text);
  margin: 0 0 1rem;
  white-space: pre-wrap;
}

.admin-request-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.admin-approve-btn {
  background: #16a34a;
  color: #fff;
  border: none;
  border-radius: var(--radius);
  padding: 0.5rem 1.2rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
}

.admin-approve-btn:hover {
  opacity: 0.88;
}

.admin-deny-btn {
  background: transparent;
  color: #dc2626;
  border: 1px solid #fca5a5;
  border-radius: var(--radius);
  padding: 0.5rem 1.2rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}

.admin-deny-btn:hover {
  background: #fef2f2;
}

.admin-deny-form {
  margin-top: 0.75rem;
  width: 100%;
}

.admin-deny-form textarea {
  width: 100%;
  padding: 0.55rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  background: var(--color-bg);
  color: var(--color-text);
  font-size: 0.875rem;
  font-family: inherit;
  resize: vertical;
  box-sizing: border-box;
}

.admin-deny-confirm-btn {
  background: #dc2626;
  color: #fff;
  border: none;
  border-radius: var(--radius);
  padding: 0.45rem 1rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
}

.admin-deny-confirm-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Past requests */

.admin-past-section {
  margin-top: 1.5rem;
}

.admin-past-toggle {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text-muted);
  padding: 0;
  margin-bottom: 0.75rem;
}

.admin-past-toggle:hover {
  color: var(--color-text);
}

.admin-status-badge {
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
  text-transform: capitalize;
}

.admin-status-approved { background: #dcfce7; color: #15803d; }
.admin-status-denied   { background: #fef2f2; color: #991b1b; }

.admin-denial-reason {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  margin: 0.5rem 0 0;
  font-style: italic;
}
```

- [ ] **Step 2: Create `frontend/src/pages/AdminPage.jsx`**

```jsx
import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'
import './AdminPage.css'

const ROLE_LABELS = {
  teacher:         'Teacher',
  content_creator: 'Content Creator',
  admin:           'Admin',
}

// ── Users tab ────────────────────────────────────────────────────────────────

function UsersTab() {
  const { user: me } = useAuth()
  const [users,    setUsers]    = useState([])
  const [loading,  setLoading]  = useState(true)
  const [feedback, setFeedback] = useState({})

  useEffect(() => {
    client.get('/admin/users/')
      .then(({ data }) => { setUsers(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const handleRoleChange = async (userId, newRole) => {
    setFeedback(prev => ({ ...prev, [userId]: { saving: true, error: '', saved: false } }))
    try {
      const { data } = await client.patch(`/admin/users/${userId}/role/`, { user_type: newRole })
      setUsers(prev => prev.map(u => u.id === userId ? { ...u, user_type: data.user_type } : u))
      setFeedback(prev => ({ ...prev, [userId]: { saving: false, error: '', saved: true } }))
      setTimeout(() => setFeedback(prev => ({ ...prev, [userId]: { saving: false, error: '', saved: false } })), 2000)
    } catch (err) {
      const msg = err?.response?.data?.error || 'Failed to update.'
      setFeedback(prev => ({ ...prev, [userId]: { saving: false, error: msg, saved: false } }))
    }
  }

  if (loading) return <p className="admin-loading">Loading users…</p>

  return (
    <div className="admin-users-table-wrap">
      <table className="admin-users-table">
        <thead>
          <tr>
            <th></th>
            <th>Name</th>
            <th>Username</th>
            <th>Email</th>
            <th>Role</th>
          </tr>
        </thead>
        <tbody>
          {users.map(u => {
            const isMe = u.id === me?.id
            const fb   = feedback[u.id] || {}
            return (
              <tr key={u.id}>
                <td><div className="admin-avatar">{u.avatar_initials || '?'}</div></td>
                <td>{u.first_name} {u.last_name}</td>
                <td>@{u.username}</td>
                <td>{u.email}</td>
                <td>
                  {isMe ? (
                    <span className="admin-you-badge">{ROLE_LABELS[u.user_type]} · You</span>
                  ) : (
                    <div className="admin-role-cell">
                      <select
                        className="admin-role-select"
                        value={u.user_type}
                        disabled={fb.saving}
                        onChange={e => handleRoleChange(u.id, e.target.value)}
                      >
                        <option value="teacher">Teacher</option>
                        <option value="content_creator">Content Creator</option>
                        <option value="admin">Admin</option>
                      </select>
                      {fb.saving && <span className="admin-feedback info">Saving…</span>}
                      {fb.saved  && <span className="admin-feedback success">✓ Saved</span>}
                      {fb.error  && <span className="admin-feedback error">{fb.error}</span>}
                    </div>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ── Access requests tab ───────────────────────────────────────────────────────

function RequestsTab() {
  const [requests,  setRequests]  = useState([])
  const [loading,   setLoading]   = useState(true)
  const [denyForms, setDenyForms] = useState({})
  const [showPast,  setShowPast]  = useState(false)

  const fetchRequests = useCallback(async () => {
    try {
      const { data } = await client.get('/admin/access-requests/')
      setRequests(data)
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { fetchRequests() }, [fetchRequests])

  const handleApprove = async (id) => {
    try {
      const { data } = await client.patch(`/admin/access-requests/${id}/`, { action: 'approve' })
      setRequests(prev => prev.map(r => r.id === id ? { ...r, ...data } : r))
    } catch { /* ignore */ }
  }

  const openDeny = (id) =>
    setDenyForms(prev => ({ ...prev, [id]: { reason: '', submitting: false, error: '' } }))

  const closeDeny = (id) =>
    setDenyForms(prev => { const n = { ...prev }; delete n[id]; return n })

  const handleDeny = async (id) => {
    const form = denyForms[id]
    if (!form?.reason?.trim()) return
    setDenyForms(prev => ({ ...prev, [id]: { ...prev[id], submitting: true, error: '' } }))
    try {
      const { data } = await client.patch(`/admin/access-requests/${id}/`, {
        action: 'deny',
        denial_reason: form.reason.trim(),
      })
      setRequests(prev => prev.map(r => r.id === id ? { ...r, ...data } : r))
      closeDeny(id)
    } catch (err) {
      const msg = err?.response?.data?.error || 'Failed to deny.'
      setDenyForms(prev => ({ ...prev, [id]: { ...prev[id], submitting: false, error: msg } }))
    }
  }

  if (loading) return <p className="admin-loading">Loading requests…</p>

  const pending = requests.filter(r => r.status === 'pending')
  const past    = requests.filter(r => r.status !== 'pending')

  return (
    <div className="admin-requests">
      {pending.length === 0 && <p className="admin-empty">No pending requests.</p>}

      {pending.map(req => (
        <div key={req.id} className="admin-request-card">
          <div className="admin-request-header">
            <div className="admin-avatar">{req.avatar_initials || '?'}</div>
            <div>
              <p className="admin-request-name">{req.first_name} {req.last_name}</p>
              <p className="admin-request-meta">
                @{req.username} · {new Date(req.created_at).toLocaleDateString()}
              </p>
            </div>
          </div>
          <p className="admin-request-message">{req.message}</p>
          <div className="admin-request-actions">
            <button className="admin-approve-btn" onClick={() => handleApprove(req.id)}>Approve</button>
            {!denyForms[req.id] ? (
              <button className="admin-deny-btn" onClick={() => openDeny(req.id)}>Deny</button>
            ) : (
              <div className="admin-deny-form">
                <textarea
                  rows={3}
                  placeholder="Explain why this request is denied…"
                  value={denyForms[req.id].reason}
                  onChange={e => setDenyForms(prev => ({
                    ...prev, [req.id]: { ...prev[req.id], reason: e.target.value },
                  }))}
                />
                {denyForms[req.id].error && (
                  <p style={{ color: '#dc2626', fontSize: '0.8rem', margin: '0.25rem 0 0' }}>
                    {denyForms[req.id].error}
                  </p>
                )}
                <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
                  <button
                    className="admin-deny-confirm-btn"
                    disabled={denyForms[req.id].submitting || !denyForms[req.id].reason.trim()}
                    onClick={() => handleDeny(req.id)}
                  >
                    {denyForms[req.id].submitting ? 'Denying…' : 'Confirm Deny'}
                  </button>
                  <button
                    style={{ background: 'none', border: '1px solid var(--color-border)', borderRadius: 'var(--radius)', padding: '0.4rem 0.75rem', cursor: 'pointer', fontSize: '0.875rem' }}
                    onClick={() => closeDeny(req.id)}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      ))}

      {past.length > 0 && (
        <div className="admin-past-section">
          <button className="admin-past-toggle" onClick={() => setShowPast(v => !v)}>
            {showPast ? '▲' : '▼'} Past Requests ({past.length})
          </button>
          {showPast && past.map(req => (
            <div key={req.id} className="admin-request-card">
              <div className="admin-request-header">
                <div className="admin-avatar">{req.avatar_initials || '?'}</div>
                <div>
                  <p className="admin-request-name">{req.first_name} {req.last_name}</p>
                  <p className="admin-request-meta">
                    @{req.username} · {new Date(req.created_at).toLocaleDateString()}
                    {' '}<span className={`admin-status-badge admin-status-${req.status}`}>{req.status}</span>
                  </p>
                </div>
              </div>
              <p className="admin-request-message">{req.message}</p>
              {req.denial_reason && (
                <p className="admin-denial-reason">Reason: {req.denial_reason}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function AdminPage() {
  const [tab, setTab] = useState('users')
  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <h1>Admin Panel</h1>
      </div>
      <div className="admin-tabs">
        <button
          className={`admin-tab-btn ${tab === 'users' ? 'active' : ''}`}
          onClick={() => setTab('users')}
        >
          Users
        </button>
        <button
          className={`admin-tab-btn ${tab === 'requests' ? 'active' : ''}`}
          onClick={() => setTab('requests')}
        >
          Access Requests
        </button>
      </div>
      {tab === 'users' ? <UsersTab /> : <RequestsTab />}
    </div>
  )
}
```

- [ ] **Step 3: Read `frontend/src/App.jsx`, then add `AdminRoute` and `/admin/users` route**

After reading the file, add this import:

```jsx
import AdminPage from './pages/AdminPage'
```

Add `AdminRoute` component (after `ContentCreatorRoute`):

```jsx
AdminRoute.propTypes = { element: PropTypes.node.isRequired }

function AdminRoute({ element }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (user.profile?.user_type !== 'admin') return <Navigate to="/" replace />
  return element
}
```

Add this route inside the `RequireOnboarding` block (alongside `/authoring`):

```jsx
<Route path="/admin/users" element={<AdminRoute element={<AdminPage />} />} />
```

- [ ] **Step 4: Read `frontend/src/components/layout/Sidebar.jsx`, then add Admin nav item**

After reading, update Sidebar.jsx. The existing logic for content creators removes `/pathway` and adds `/authoring`. The new logic adds a third case for admins.

Replace the entire file content:

```jsx
import { NavLink } from 'react-router-dom'
import { House, BookOpen, GraduationCap, BarChart2, User, PenLine, Map, Shield } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import './Sidebar.css'

const BASE_NAV = [
  { to: '/',          label: 'Home',              Icon: House },
  { to: '/courses',   label: 'Courses',           Icon: BookOpen },
  { to: '/learning',  label: 'My Learning',       Icon: GraduationCap },
  { to: '/pathway',   label: 'My Pathway',        Icon: Map },
  { to: '/analytics', label: 'Content Analytics', Icon: BarChart2 },
  { to: '/profile',   label: 'Profile',           Icon: User },
]

const AUTHORING_ITEM = { to: '/authoring',    label: 'Authoring', Icon: PenLine }
const ADMIN_ITEM     = { to: '/admin/users',  label: 'Admin',     Icon: Shield  }

export default function Sidebar() {
  const { user } = useAuth()
  const userType = user?.profile?.user_type

  let navItems
  if (userType === 'admin') {
    navItems = [...BASE_NAV.filter(item => item.to !== '/pathway'), ADMIN_ITEM]
  } else if (userType === 'content_creator') {
    navItems = [...BASE_NAV.filter(item => item.to !== '/pathway'), AUTHORING_ITEM]
  } else {
    navItems = BASE_NAV
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <img
          src="https://aideaacademy.eu/demo/wp-content/uploads/2026/01/aidea-logo-3-AIdEA-COLORED-162px.png"
          alt="AIDEA"
        />
      </div>
      <nav>
        <ul>
          {navItems.map(({ to, label, Icon: NavIcon }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={to === '/'}
                className={({ isActive }) => isActive ? 'active' : ''}
              >
                <NavIcon size={18} className="nav-icon" />
                <span>{label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  )
}
```

- [ ] **Step 5: Run ESLint — expect clean**

```
cd frontend && npm run lint
```

- [ ] **Step 6: Commit**

```
git add frontend/src/pages/AdminPage.jsx \
        frontend/src/pages/AdminPage.css \
        frontend/src/App.jsx \
        frontend/src/components/layout/Sidebar.jsx
git commit -m "feat: add AdminPage with user management and access request review"
```

---

### Task 6: Frontend — Profile page Content Creator Access section

**Files:**
- Modify: `frontend/src/pages/ProfilePage.jsx`
- Modify: `frontend/src/pages/ProfilePage.css`

**Interfaces:**
- Consumes: `useAccessRequest()` from `../context/AccessRequestContext` (provided by Layout, so always available on this page)
- Produces: `ContentCreatorAccessSection` rendered at the bottom of `ProfilePage` for teachers only

- [ ] **Step 1: Read `frontend/src/pages/ProfilePage.jsx` before editing**

You MUST read the full file before making changes. After reading, add:

1. Import `useAccessRequest` at the top:

```jsx
import { useAccessRequest } from '../context/AccessRequestContext'
```

2. Add the `ContentCreatorAccessSection` component (add it before the `// ── Page` section):

```jsx
// ── Content Creator Access ────────────────────────────────────────────────────

function ContentCreatorAccessSection() {
  const { user } = useAuth()
  const { request, loading, submit, cancel } = useAccessRequest()
  const [showForm,   setShowForm]   = useState(false)
  const [message,    setMessage]    = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error,      setError]      = useState('')

  if (user?.profile?.user_type !== 'teacher') return null

  if (loading) {
    return (
      <section className="profile-card">
        <h2>Content Creator Access</h2>
        <p className="profile-loading">Loading…</p>
      </section>
    )
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!message.trim()) return
    setSubmitting(true)
    setError('')
    try {
      await submit(message.trim())
      setShowForm(false)
      setMessage('')
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to submit request.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleCancel = async () => {
    try { await cancel(request.id) } catch { /* ignore */ }
  }

  const requestForm = (
    <form onSubmit={handleSubmit}>
      <div className="profile-field">
        <label htmlFor="cc-message">Why do you want Content Creator access?</label>
        <textarea
          id="cc-message"
          value={message}
          onChange={e => setMessage(e.target.value)}
          placeholder="Describe your plans for creating courses…"
          rows={4}
          required
        />
      </div>
      {error && <p className="profile-feedback error">{error}</p>}
      <div className="profile-section-footer">
        <button
          type="button"
          className="profile-outline-btn"
          onClick={() => { setShowForm(false); setMessage('') }}
        >
          Cancel
        </button>
        <button
          type="submit"
          className="profile-save-btn"
          disabled={submitting || !message.trim()}
        >
          {submitting ? 'Submitting…' : 'Submit Request'}
        </button>
      </div>
    </form>
  )

  return (
    <section className="profile-card">
      <h2>Content Creator Access</h2>

      {!request && !showForm && (
        <>
          <p className="profile-loading">
            Want to create and publish courses? Request access from the admin team.
          </p>
          <button
            className="profile-outline-btn"
            style={{ marginTop: '1rem' }}
            onClick={() => setShowForm(true)}
          >
            Request Access
          </button>
        </>
      )}

      {!request && showForm && requestForm}

      {request?.status === 'pending' && (
        <>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
            <span className="cc-badge cc-badge-pending">Pending Review</span>
            <span className="profile-loading">
              Submitted {new Date(request.created_at).toLocaleDateString()}
            </span>
          </div>
          <button className="profile-outline-btn" onClick={handleCancel}>
            Cancel Request
          </button>
        </>
      )}

      {request?.status === 'denied' && (
        <>
          <div className="cc-denial-box">
            <p className="cc-denial-label">Your request was denied</p>
            <p className="cc-denial-reason">{request.denial_reason}</p>
          </div>
          {!showForm ? (
            <button
              className="profile-outline-btn"
              style={{ marginTop: '1rem' }}
              onClick={() => setShowForm(true)}
            >
              Request Again
            </button>
          ) : (
            <div style={{ marginTop: '1rem' }}>{requestForm}</div>
          )}
        </>
      )}
    </section>
  )
}
```

3. Add `<ContentCreatorAccessSection />` inside `ProfilePage` return, after `<SecuritySection />`:

```jsx
      <SecuritySection />
      <ContentCreatorAccessSection />
```

- [ ] **Step 2: Read `frontend/src/pages/ProfilePage.css`, then append new styles**

Append to the end of the existing file:

```css
/* Content Creator Access section */

.profile-field textarea {
  width: 100%;
  padding: 0.55rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  background: var(--color-bg);
  color: var(--color-text);
  font-size: 0.9rem;
  font-family: inherit;
  resize: vertical;
  box-sizing: border-box;
  transition: border-color 0.15s;
}

.profile-field textarea:focus {
  outline: none;
  border-color: var(--color-primary);
}

.cc-badge {
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.2rem 0.65rem;
  border-radius: 999px;
}

.cc-badge-pending {
  background: #fef9c3;
  color: #854d0e;
}

.cc-denial-box {
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: var(--radius);
  padding: 0.9rem 1rem;
}

.cc-denial-label {
  font-weight: 600;
  font-size: 0.875rem;
  color: #991b1b;
  margin: 0 0 0.35rem;
}

.cc-denial-reason {
  font-size: 0.875rem;
  color: #7f1d1d;
  margin: 0;
}
```

- [ ] **Step 3: Run ESLint — expect clean**

```
cd frontend && npm run lint
```

- [ ] **Step 4: Run backend tests — no regressions**

```
cd backend
.venv\Scripts\python.exe manage.py test hub --verbosity=1
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```
git add frontend/src/pages/ProfilePage.jsx \
        frontend/src/pages/ProfilePage.css
git commit -m "feat: add Content Creator access request section to profile page"
```

---

## Done

After all six tasks:

- Admins can view all users and change roles at `/admin/users` (Users tab)
- Admins can review, approve, or deny CC access requests (Access Requests tab)
- Any teacher can submit a request with a message from their profile page
- On deny, the teacher sees the reason in their profile and as a dismissable banner on any page load
- Denied teachers can re-submit a new request
- Cancelling a pending request deletes it (teacher can re-submit later)
- Approving auto-promotes the user to `content_creator` in the same transaction

**To create an admin user for manual testing:**
```
cd backend
.venv\Scripts\python.exe manage.py shell -c "
from django.contrib.auth.models import User
from hub.models import UserProfile
u = User.objects.create_user('demo_admin', email='admin@test.com', password='Admin#1234', first_name='Demo', last_name='Admin')
UserProfile.objects.create(user=u, user_type='admin', avatar_initials='DA')
print('Admin created: demo_admin / Admin#1234')
"
```
