# User Registration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add self-service teacher registration with session-only auto-login that drops directly into onboarding — closing the browser tab requires a manual sign-in next time.

**Architecture:** A new `POST /api/auth/register/` endpoint creates `User` + `UserProfile(teacher)` and returns JWT tokens in the same `{access, refresh, user}` shape as login. The frontend adds a `loginSession()` to `AuthContext` that writes tokens to `sessionStorage` instead of `localStorage`; closing the tab clears it automatically. `client.js` reads from `localStorage` first, then `sessionStorage`, so the Axios interceptor works transparently for both flows. A `RegisterPage` at `/register` collects name, username, email and password (with the live strength checker extracted into a shared component), then calls `loginSession()` and redirects to `/onboarding`.

**Tech Stack:** Django 5.1, DRF, simplejwt, React 19, Vite, react-router-dom v7, lucide-react, Axios

## Global Constraints

- Backend runner: `cd backend && .venv\Scripts\python.exe manage.py ...`
- Frontend lint: `cd frontend && npm run lint` — must be clean after every task
- Password rules (identical on backend and frontend): min 8 chars, max 128, uppercase, lowercase, digit, special char `[^A-Za-z0-9]`
- Self-registered accounts always get `user_type = 'teacher'`
- Post-registration tokens → `sessionStorage` (clears on tab close)
- Manual login tokens → `localStorage` (unchanged)
- New backend endpoints are `AllowAny` (pre-auth, no JWT needed)

---

## File Map

| File | Change |
|------|--------|
| `backend/hub/serializers/auth.py` | Add `RegisterSerializer` |
| `backend/hub/serializers/__init__.py` | Export `RegisterSerializer` |
| `backend/hub/views/auth.py` | Add `RegisterView` |
| `backend/hub/views/__init__.py` | Export `RegisterView` |
| `backend/hub/urls.py` | Add `auth/register/` route |
| `backend/hub/tests/test_register.py` | New — 8 tests |
| `frontend/src/components/PasswordInput.jsx` | New — shared password UI |
| `frontend/src/components/PasswordInput.css` | New — shared pw-* styles |
| `frontend/src/pages/ProfilePage.jsx` | Import from shared component, remove local defs |
| `frontend/src/pages/ProfilePage.css` | Remove pw-* rules (moved to PasswordInput.css) |
| `frontend/src/api/client.js` | Read tokens from both storages |
| `frontend/src/context/AuthContext.jsx` | Add `loginSession()`, read/clear both storages |
| `frontend/src/pages/RegisterPage.jsx` | New |
| `frontend/src/pages/RegisterPage.css` | New |
| `frontend/src/App.jsx` | Add `/register` route |
| `frontend/src/pages/LoginPage.jsx` | Add "Create account" link |
| `frontend/src/pages/LoginPage.css` | Add link style |

---

### Task 1: Backend — RegisterSerializer, RegisterView, URL, tests

**Files:**
- Modify: `backend/hub/serializers/auth.py`
- Modify: `backend/hub/serializers/__init__.py`
- Modify: `backend/hub/views/auth.py`
- Modify: `backend/hub/views/__init__.py`
- Modify: `backend/hub/urls.py`
- Create: `backend/hub/tests/test_register.py`

**Interfaces:**
- Produces: `POST /api/auth/register/` accepts `{first_name, last_name, username, email, password, confirm_password}`, returns HTTP 201 `{access: str, refresh: str, user: {id, username, first_name, last_name, email, profile: {user_type, avatar_initials, onboarding_completed, preferred_pillars, learning_style}}}`

- [ ] **Step 1: Write the failing tests**

Create `backend/hub/tests/test_register.py`:

```python
from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from hub.models import UserProfile


class RegisterViewTest(APITestCase):
    URL = '/api/auth/register/'
    VALID = {
        'first_name': 'Test', 'last_name': 'User',
        'username': 'testuser', 'email': 'test@example.com',
        'password': 'Secure#123', 'confirm_password': 'Secure#123',
    }

    def test_register_creates_user_and_returns_201(self):
        res = self.client.post(self.URL, self.VALID, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertTrue(User.objects.filter(username='testuser').exists())

    def test_register_creates_teacher_profile(self):
        self.client.post(self.URL, self.VALID, format='json')
        profile = UserProfile.objects.get(user__username='testuser')
        self.assertEqual(profile.user_type, 'teacher')

    def test_register_sets_avatar_initials_from_name(self):
        self.client.post(self.URL, self.VALID, format='json')
        profile = UserProfile.objects.get(user__username='testuser')
        self.assertEqual(profile.avatar_initials, 'TU')

    def test_register_returns_jwt_tokens_and_user(self):
        res = self.client.post(self.URL, self.VALID, format='json')
        self.assertIn('access', res.data)
        self.assertIn('refresh', res.data)
        self.assertIn('user', res.data)
        self.assertEqual(res.data['user']['username'], 'testuser')

    def test_register_duplicate_username_returns_400(self):
        self.client.post(self.URL, self.VALID, format='json')
        res = self.client.post(
            self.URL, {**self.VALID, 'email': 'other@example.com'}, format='json'
        )
        self.assertEqual(res.status_code, 400)

    def test_register_duplicate_email_returns_400(self):
        self.client.post(self.URL, self.VALID, format='json')
        res = self.client.post(
            self.URL, {**self.VALID, 'username': 'otheruser'}, format='json'
        )
        self.assertEqual(res.status_code, 400)

    def test_register_weak_password_returns_400(self):
        data = {**self.VALID, 'password': 'weakpass', 'confirm_password': 'weakpass'}
        res = self.client.post(self.URL, data, format='json')
        self.assertEqual(res.status_code, 400)

    def test_register_password_mismatch_returns_400(self):
        data = {**self.VALID, 'confirm_password': 'Different#999'}
        res = self.client.post(self.URL, data, format='json')
        self.assertEqual(res.status_code, 400)
```

- [ ] **Step 2: Run tests — expect all 8 to fail**

```
cd backend
.venv\Scripts\python.exe manage.py test hub.tests.test_register --verbosity=2
```

Expected: 8 errors (404 — route does not exist yet).

- [ ] **Step 3: Replace `backend/hub/serializers/auth.py` with the full updated file**

```python
import re

from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from hub.models import UserProfile

_PASSWORD_RULES = [
    (lambda p: len(p) >= 8,                         'at least 8 characters'),
    (lambda p: len(p) <= 128,                        'no more than 128 characters'),
    (lambda p: bool(re.search(r'[A-Z]', p)),        'at least one uppercase letter'),
    (lambda p: bool(re.search(r'[a-z]', p)),        'at least one lowercase letter'),
    (lambda p: bool(re.search(r'\d', p)),            'at least one number'),
    (lambda p: bool(re.search(r'[^A-Za-z0-9]', p)), 'at least one special character'),
]


class RegisterSerializer(serializers.Serializer):
    first_name       = serializers.CharField(max_length=150)
    last_name        = serializers.CharField(max_length=150)
    username         = serializers.CharField(max_length=150)
    email            = serializers.EmailField()
    password         = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('This username is already taken.')
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value

    def validate_password(self, value):
        errors = [msg for check, msg in _PASSWORD_RULES if not check(value)]
        if errors:
            raise serializers.ValidationError(f"Password must have: {', '.join(errors)}.")
        return value

    def validate(self, data):
        if data.get('password') != data.get('confirm_password'):
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            password=password,
        )
        initials = (validated_data['first_name'][:1] + validated_data['last_name'][:1]).upper()
        UserProfile.objects.create(
            user=user,
            user_type=UserProfile.UserType.TEACHER,
            avatar_initials=initials,
        )
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model  = UserProfile
        fields = ['user_type', 'avatar_initials', 'onboarding_completed',
                  'preferred_pillars', 'learning_style']


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'profile']


class AideaTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user).data
        return data
```

- [ ] **Step 4: Export `RegisterSerializer` from `backend/hub/serializers/__init__.py`**

Update the `.auth` import line to:

```python
from .auth import AideaTokenObtainPairSerializer, RegisterSerializer, UserProfileSerializer, UserSerializer
```

Add `'RegisterSerializer',` to `__all__`.

- [ ] **Step 5: Replace `backend/hub/views/auth.py` with the full updated file**

```python
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from hub.serializers import AideaTokenObtainPairSerializer, RegisterSerializer, UserSerializer


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = AideaTokenObtainPairSerializer


class LogoutView(APIView):
    def post(self, request):
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({'detail': 'Logged out.'})


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'access':  str(refresh.access_token),
            'refresh': str(refresh),
            'user':    UserSerializer(user).data,
        }, status=201)
```

- [ ] **Step 6: Export `RegisterView` from `backend/hub/views/__init__.py`**

Update the `.auth` import line:

```python
from .auth import LoginView, LogoutView, RegisterView
```

Add `'RegisterView',` to `__all__`.

- [ ] **Step 7: Add the URL route in `backend/hub/urls.py`**

Add `RegisterView` to the imports block. Add this line to `urlpatterns` after `auth/logout/`:

```python
path('auth/register/', RegisterView.as_view(), name='auth-register'),
```

- [ ] **Step 8: Run tests — expect all 8 to pass**

```
cd backend
.venv\Scripts\python.exe manage.py test hub.tests.test_register --verbosity=2
```

Expected: 8 tests pass.

- [ ] **Step 9: Run full suite — no regressions**

```
cd backend
.venv\Scripts\python.exe manage.py test hub --verbosity=1
```

Expected: all prior tests still pass (≥299) + 8 new = ≥307.

- [ ] **Step 10: Commit**

```
git add backend/hub/serializers/auth.py \
        backend/hub/serializers/__init__.py \
        backend/hub/views/auth.py \
        backend/hub/views/__init__.py \
        backend/hub/urls.py \
        backend/hub/tests/test_register.py
git commit -m "feat: add POST /api/auth/register/ for self-service teacher registration"
```

---

### Task 2: Extract shared PasswordInput component + refactor ProfilePage

The password input with eye toggle, strength bar, and rules list is currently defined inline in `ProfilePage.jsx` and its CSS is in `ProfilePage.css`. RegisterPage needs the same thing — extract once, import twice.

**Files:**
- Create: `frontend/src/components/PasswordInput.jsx`
- Create: `frontend/src/components/PasswordInput.css`
- Modify: `frontend/src/pages/ProfilePage.jsx` — import from shared component; remove local defs
- Modify: `frontend/src/pages/ProfilePage.css` — remove pw-* rules

**Interfaces:**
- Produces (from `frontend/src/components/PasswordInput.jsx`):
  - `PASSWORD_RULES: Array<{key: string, label: string, test: (p: string) => boolean}>`
  - `passwordStrength(password: string): {label: string, color: string}`
  - `PasswordInput` — props: `{value, onChange, placeholder?, autoComplete?}`
  - `PasswordStrengthPanel` — props: `{password: string}`

- [ ] **Step 1: Create `frontend/src/components/PasswordInput.css`**

```css
.pw-input-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

.pw-input-wrap input {
  width: 100%;
  padding-right: 2.5rem;
}

.pw-eye-btn {
  position: absolute;
  right: 0.6rem;
  background: none;
  border: none;
  padding: 0.2rem;
  color: var(--color-text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  line-height: 1;
}

.pw-eye-btn:hover {
  color: var(--color-text);
}

.pw-strength-bar {
  height: 4px;
  background: var(--color-border);
  border-radius: 2px;
  margin-top: 0.5rem;
  overflow: hidden;
}

.pw-strength-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.25s ease, background 0.25s ease;
}

.pw-strength-label {
  font-size: 0.75rem;
  font-weight: 600;
  margin-top: 0.25rem;
  display: block;
}

.pw-rules {
  list-style: none;
  margin: 0.5rem 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.pw-rule {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.8rem;
  transition: color 0.15s;
}

.pw-rule.met   { color: #16a34a; }
.pw-rule.unmet { color: var(--color-text-muted); }

.pw-match-hint {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.8rem;
  margin-top: 0.3rem;
}

.pw-match-hint.met   { color: #16a34a; }
.pw-match-hint.unmet { color: #dc2626; }
```

- [ ] **Step 2: Create `frontend/src/components/PasswordInput.jsx`**

```jsx
import PropTypes from 'prop-types'
import { useState } from 'react'
import { Check, Eye, EyeOff, X } from 'lucide-react'
import './PasswordInput.css'

export const PASSWORD_RULES = [
  { key: 'length', label: 'At least 8 characters',          test: (p) => p.length >= 8 },
  { key: 'upper',  label: 'One uppercase letter (A–Z)',      test: (p) => /[A-Z]/.test(p) },
  { key: 'lower',  label: 'One lowercase letter (a–z)',      test: (p) => /[a-z]/.test(p) },
  { key: 'number', label: 'One number (0–9)',                test: (p) => /\d/.test(p) },
  { key: 'symbol', label: 'One special character (!@#$%…)',  test: (p) => /[^A-Za-z0-9]/.test(p) },
]

export function passwordStrength(password) {
  const passed = PASSWORD_RULES.filter(r => r.test(password)).length
  if (passed <= 2) return { label: 'Weak',   color: '#dc2626' }
  if (passed === 3) return { label: 'Fair',   color: '#f97316' }
  if (passed === 4) return { label: 'Good',   color: '#eab308' }
  return               { label: 'Strong', color: '#16a34a' }
}

export function PasswordInput({ value, onChange, placeholder, autoComplete }) {
  const [visible, setVisible] = useState(false)
  return (
    <div className="pw-input-wrap">
      <input
        type={visible ? 'text' : 'password'}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        autoComplete={autoComplete}
        required
      />
      <button
        type="button"
        className="pw-eye-btn"
        onClick={() => setVisible(v => !v)}
        aria-label={visible ? 'Hide password' : 'Show password'}
      >
        {visible ? <EyeOff size={16} /> : <Eye size={16} />}
      </button>
    </div>
  )
}

PasswordInput.propTypes = {
  value:        PropTypes.string.isRequired,
  onChange:     PropTypes.func.isRequired,
  placeholder:  PropTypes.string,
  autoComplete: PropTypes.string,
}

export function PasswordStrengthPanel({ password }) {
  if (!password) return null
  const strength = passwordStrength(password)
  const passed   = PASSWORD_RULES.filter(r => r.test(password)).length
  return (
    <>
      <div className="pw-strength-bar">
        <div
          className="pw-strength-fill"
          style={{
            width: `${(passed / PASSWORD_RULES.length) * 100}%`,
            background: strength.color,
          }}
        />
      </div>
      <span className="pw-strength-label" style={{ color: strength.color }}>
        {strength.label}
      </span>
      <ul className="pw-rules">
        {PASSWORD_RULES.map(rule => {
          const met = rule.test(password)
          return (
            <li key={rule.key} className={`pw-rule ${met ? 'met' : 'unmet'}`}>
              {met ? <Check size={12} /> : <X size={12} />}
              {rule.label}
            </li>
          )
        })}
      </ul>
    </>
  )
}

PasswordStrengthPanel.propTypes = {
  password: PropTypes.string.isRequired,
}
```

- [ ] **Step 3: Update `frontend/src/pages/ProfilePage.jsx`**

At the top of the file, replace:

```jsx
import { Eye, EyeOff, Check, X } from 'lucide-react'
```

with:

```jsx
import { Check, X } from 'lucide-react'
import {
  PasswordInput,
  PasswordStrengthPanel,
  PASSWORD_RULES,
  passwordStrength,
} from '../components/PasswordInput'
```

Then delete the following blocks that are now in the shared component (search for each one and remove it entirely):

```jsx
// ── Password helpers ──────────────────────────────────────────────────────────

const PASSWORD_RULES = [...]

function passwordStrength(password) { ... }

function PasswordInput({ ... }) { ... }

PasswordInput.propTypes = { ... }
```

Everything else in `ProfilePage.jsx` (`SecuritySection`, etc.) stays identical — it already uses `PasswordInput`, `PasswordStrengthPanel`, `PASSWORD_RULES`, `passwordStrength` by name.

- [ ] **Step 4: Remove pw-* rules from `frontend/src/pages/ProfilePage.css`**

Delete the entire block from the comment `/* Password input with eye toggle */` through the last `.pw-match-hint.unmet` rule. These classes are now in `PasswordInput.css` which the component imports directly.

- [ ] **Step 5: Run ESLint — expect clean**

```
cd frontend
npm run lint
```

Expected: no output.

- [ ] **Step 6: Commit**

```
git add frontend/src/components/PasswordInput.jsx \
        frontend/src/components/PasswordInput.css \
        frontend/src/pages/ProfilePage.jsx \
        frontend/src/pages/ProfilePage.css
git commit -m "refactor: extract PasswordInput + PasswordStrengthPanel to shared component"
```

---

### Task 3: sessionStorage support — client.js + AuthContext

**Files:**
- Modify: `frontend/src/api/client.js`
- Modify: `frontend/src/context/AuthContext.jsx`

**Interfaces:**
- Produces: `loginSession(data: {access, refresh, user})` in `AuthContext` — writes to `sessionStorage`; `logout()` now clears both storages; `client.js` reads tokens from `localStorage || sessionStorage`

- [ ] **Step 1: Replace `frontend/src/api/client.js`**

```javascript
import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

function getToken(key) {
  return localStorage.getItem(key) || sessionStorage.getItem(key)
}

const client = axios.create({ baseURL: BASE })

client.interceptors.request.use((config) => {
  const token = getToken('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const refresh = getToken('refresh_token')
      if (refresh) {
        try {
          const { data } = await axios.post(`${BASE}/auth/refresh/`, { refresh })
          // Write refreshed access token back to whichever storage holds the session
          const store = localStorage.getItem('refresh_token') ? localStorage : sessionStorage
          store.setItem('access_token', data.access)
          original.headers.Authorization = `Bearer ${data.access}`
          return client(original)
        } catch {
          ['access_token', 'refresh_token', 'user'].forEach(k => {
            localStorage.removeItem(k)
            sessionStorage.removeItem(k)
          })
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(error)
  }
)

export default client
```

- [ ] **Step 2: Replace `frontend/src/context/AuthContext.jsx`**

```jsx
import { createContext, useContext, useState, useCallback } from 'react'
import PropTypes from 'prop-types'
import client from '../api/client'

const AuthContext = createContext(null)

AuthProvider.propTypes = { children: PropTypes.node }

const KEYS = ['access_token', 'refresh_token', 'user']

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const stored = localStorage.getItem('user') || sessionStorage.getItem('user')
    return stored ? JSON.parse(stored) : null
  })

  // Persistent login — survives tab close (localStorage)
  const login = useCallback(async (username, password) => {
    const { data } = await client.post('/auth/login/', { username, password })
    localStorage.setItem('access_token', data.access)
    localStorage.setItem('refresh_token', data.refresh)
    localStorage.setItem('user', JSON.stringify(data.user))
    setUser(data.user)
  }, [])

  // Session-only login — cleared when the tab closes (sessionStorage)
  const loginSession = useCallback((data) => {
    sessionStorage.setItem('access_token', data.access)
    sessionStorage.setItem('refresh_token', data.refresh)
    sessionStorage.setItem('user', JSON.stringify(data.user))
    setUser(data.user)
  }, [])

  const logout = useCallback(async () => {
    const refresh = localStorage.getItem('refresh_token') || sessionStorage.getItem('refresh_token')
    try {
      await client.post('/auth/logout/', { refresh })
    } finally {
      KEYS.forEach(k => { localStorage.removeItem(k); sessionStorage.removeItem(k) })
      setUser(null)
    }
  }, [])

  const updateUser = useCallback((updates) => {
    setUser(prev => {
      const updated = { ...prev, ...updates }
      const store = localStorage.getItem('user') ? localStorage : sessionStorage
      store.setItem('user', JSON.stringify(updated))
      return updated
    })
  }, [])

  return (
    <AuthContext.Provider value={{ user, login, loginSession, logout, updateUser }}>
      {children}
    </AuthContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  return useContext(AuthContext)
}
```

- [ ] **Step 3: Run ESLint — expect clean**

```
cd frontend
npm run lint
```

Expected: no output.

- [ ] **Step 4: Commit**

```
git add frontend/src/api/client.js \
        frontend/src/context/AuthContext.jsx
git commit -m "feat: add loginSession() for sessionStorage-only post-registration auto-login"
```

---

### Task 4: RegisterPage

**Files:**
- Create: `frontend/src/pages/RegisterPage.jsx`
- Create: `frontend/src/pages/RegisterPage.css`

**Interfaces:**
- Consumes: `loginSession` from `useAuth()`, `PasswordInput` / `PasswordStrengthPanel` / `PASSWORD_RULES` from `../components/PasswordInput`, `client` from `../api/client`
- Produces: default export `RegisterPage`, renders at `/register`

- [ ] **Step 1: Create `frontend/src/pages/RegisterPage.css`**

```css
.register-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg);
  padding: 2rem 1rem;
}

.register-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 2.5rem;
  width: 100%;
  max-width: 440px;
  box-shadow: var(--shadow);
}

.register-logo {
  height: 48px;
  width: auto;
  display: block;
  margin-bottom: 0.5rem;
}

.register-title {
  font-size: 1.25rem;
  font-weight: 700;
  margin: 0 0 0.25rem;
  color: var(--color-text);
}

.register-subtitle {
  color: var(--color-text-muted);
  margin: 0 0 1.75rem;
  font-size: 0.875rem;
}

.register-name-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}

.register-error {
  background: #fff5f5;
  color: var(--color-red);
  border: 1px solid #fecaca;
  border-radius: var(--radius);
  padding: 0.6rem 0.8rem;
  font-size: 0.875rem;
  margin-bottom: 1rem;
}

.register-submit {
  width: 100%;
  padding: 0.65rem;
  margin-top: 0.5rem;
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: var(--radius);
  font-size: 0.95rem;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: background 0.15s;
}

.register-submit:hover:not(:disabled) {
  background: var(--color-primary-dark);
}

.register-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.register-link {
  margin-top: 1.25rem;
  text-align: center;
  font-size: 0.875rem;
  color: var(--color-text-muted);
}

.register-link a {
  color: var(--color-primary);
  font-weight: 500;
  text-decoration: none;
}

.register-link a:hover {
  text-decoration: underline;
}

.register-footer {
  margin-top: 2rem;
  padding-top: 1.25rem;
  border-top: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.6rem;
}

.register-eu-logo {
  height: 36px;
  width: auto;
}

.register-eu-text {
  font-size: 0.7rem;
  color: var(--color-text-muted);
  text-align: center;
  line-height: 1.4;
}

@media (max-width: 480px) {
  .register-name-row {
    grid-template-columns: 1fr;
  }
}
```

- [ ] **Step 2: Create `frontend/src/pages/RegisterPage.jsx`**

```jsx
import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { Check, X } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'
import {
  PasswordInput,
  PasswordStrengthPanel,
  PASSWORD_RULES,
} from '../components/PasswordInput'
import './RegisterPage.css'

export default function RegisterPage() {
  const { user, loginSession } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState({
    first_name: '', last_name: '', username: '', email: '',
    password: '', confirm: '',
  })
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')

  if (user) return <Navigate to="/" replace />

  const set = (key) => (e) => setForm(prev => ({ ...prev, [key]: e.target.value }))

  const allRulesMet    = PASSWORD_RULES.every(r => r.test(form.password))
  const passwordsMatch = form.password.length > 0 && form.password === form.confirm
  const canSubmit      =
    form.first_name && form.last_name && form.username &&
    form.email && allRulesMet && passwordsMatch && !loading

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!canSubmit) return
    setError('')
    setLoading(true)
    try {
      const { data } = await client.post('/auth/register/', {
        first_name:       form.first_name,
        last_name:        form.last_name,
        username:         form.username,
        email:            form.email,
        password:         form.password,
        confirm_password: form.confirm,
      })
      loginSession(data)
      navigate('/onboarding')
    } catch (err) {
      const detail = err?.response?.data
      if (detail && typeof detail === 'object') {
        const first = Object.values(detail)[0]
        setError(Array.isArray(first) ? first[0] : String(first))
      } else {
        setError('Registration failed. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="register-page">
      <div className="register-card">
        <img
          src="https://aideaacademy.eu/demo/wp-content/uploads/2026/01/aidea-logo-3-AIdEA-COLORED-162px.png"
          alt="AIDEA"
          className="register-logo"
        />
        <h1 className="register-title">Create your account</h1>
        <p className="register-subtitle">Join the AIDEA Teacher AI Training Platform</p>

        <form onSubmit={handleSubmit} noValidate>
          {error && <div className="register-error">{error}</div>}

          <div className="register-name-row">
            <div className="field">
              <label htmlFor="first_name">First Name</label>
              <input
                id="first_name" type="text" value={form.first_name}
                onChange={set('first_name')} placeholder="Maria" required autoFocus
              />
            </div>
            <div className="field">
              <label htmlFor="last_name">Last Name</label>
              <input
                id="last_name" type="text" value={form.last_name}
                onChange={set('last_name')} placeholder="Papadaki" required
              />
            </div>
          </div>

          <div className="field">
            <label htmlFor="reg-username">Username</label>
            <input
              id="reg-username" type="text" value={form.username}
              onChange={set('username')} placeholder="maria.papadaki" required
              autoComplete="username"
            />
          </div>

          <div className="field">
            <label htmlFor="reg-email">Email</label>
            <input
              id="reg-email" type="email" value={form.email}
              onChange={set('email')} placeholder="you@school.edu" required
              autoComplete="email"
            />
          </div>

          <div className="field">
            <label htmlFor="reg-password">Password</label>
            <PasswordInput
              value={form.password} onChange={set('password')}
              placeholder="Create a strong password" autoComplete="new-password"
            />
            <PasswordStrengthPanel password={form.password} />
          </div>

          <div className="field">
            <label htmlFor="reg-confirm">Confirm Password</label>
            <PasswordInput
              value={form.confirm} onChange={set('confirm')}
              placeholder="Repeat your password" autoComplete="new-password"
            />
            {form.confirm && (
              <span className={`pw-match-hint ${passwordsMatch ? 'met' : 'unmet'}`}>
                {passwordsMatch
                  ? <><Check size={12} /> Passwords match</>
                  : <><X size={12} /> Passwords do not match</>}
              </span>
            )}
          </div>

          <button type="submit" className="register-submit" disabled={!canSubmit}>
            {loading ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p className="register-link">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>

        <div className="register-footer">
          <img
            src="https://aideaacademy.eu/demo/wp-content/uploads/2026/03/EN-Co-funded-by-the-EU_PANTONE-300x63-1.jpg"
            alt="Co-funded by the European Union"
            className="register-eu-logo"
          />
          <p className="register-eu-text">
            Funded by the European Union. Views and opinions expressed are however those of the
            author(s) only and do not necessarily reflect those of the European Union or the EACEA.
          </p>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Run ESLint — expect clean**

```
cd frontend
npm run lint
```

Expected: no output.

- [ ] **Step 4: Commit**

```
git add frontend/src/pages/RegisterPage.jsx \
        frontend/src/pages/RegisterPage.css
git commit -m "feat: add RegisterPage with live password strength checker"
```

---

### Task 5: Wire route + login page link

**Files:**
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/pages/LoginPage.jsx`
- Modify: `frontend/src/pages/LoginPage.css`

**Interfaces:**
- Consumes: `RegisterPage` from `./pages/RegisterPage`
- Produces: navigable `/register` public route; "Don't have an account?" link on `/login`

- [ ] **Step 1: Update `frontend/src/App.jsx`**

Add import:

```jsx
import RegisterPage from './pages/RegisterPage'
```

Add route alongside the existing `/login` route (both are public, before the `RequireOnboarding` block):

```jsx
<Route path="/register" element={<RegisterPage />} />
```

- [ ] **Step 2: Update `frontend/src/pages/LoginPage.jsx`**

Add `Link` to the existing react-router-dom import:

```jsx
import { useNavigate, Navigate, Link } from 'react-router-dom'
```

Add this paragraph immediately after the closing `</form>` tag and before `<div className="login-footer">`:

```jsx
<p className="login-signup-link">
  Don&apos;t have an account? <Link to="/register">Create one</Link>
</p>
```

- [ ] **Step 3: Add style to `frontend/src/pages/LoginPage.css`**

Append to the end of the file:

```css
.login-signup-link {
  margin-top: 1.25rem;
  text-align: center;
  font-size: 0.875rem;
  color: var(--color-text-muted);
}

.login-signup-link a {
  color: var(--color-primary);
  font-weight: 500;
  text-decoration: none;
}

.login-signup-link a:hover {
  text-decoration: underline;
}
```

- [ ] **Step 4: Run ESLint — expect clean**

```
cd frontend
npm run lint
```

Expected: no output.

- [ ] **Step 5: Run backend tests — no regressions**

```
cd backend
.venv\Scripts\python.exe manage.py test hub --verbosity=1
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```
git add frontend/src/App.jsx \
        frontend/src/pages/LoginPage.jsx \
        frontend/src/pages/LoginPage.css
git commit -m "feat: wire /register route and add sign-up link on login page"
```

---

## Done

After all five tasks:
- `POST /api/auth/register/` creates teacher accounts and returns JWT tokens
- `/register` page validates all fields live (unique username/email checked server-side on submit), shows password strength, blocks submission until all rules pass and passwords match
- Successful registration auto-logs in via `sessionStorage` — closing the tab logs out
- Manual login continues to use `localStorage` — unchanged
- `/login` page has a "Create one" link; `/register` page has "Sign in" link back
- Password UI (eye toggle, strength bar, rules checklist, match hint) lives in one shared component used by both the register page and the profile change-password form
