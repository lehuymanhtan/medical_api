# Medical API — Full Code Audit Report
> Generated: 2026-04-29 | Auditor: Antigravity AI

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Architecture Assessment](#2-architecture-assessment)
3. [Security Analysis](#3-security-analysis)
4. [Bugs & Issues](#4-bugs--issues)
5. [Performance](#5-performance)
6. [Code Quality](#6-code-quality)
7. [Testing](#7-testing)
8. [Dependency Analysis](#8-dependency-analysis)
9. [Summary Table](#9-summary-table)
10. [Recommendations Roadmap](#10-recommendations-roadmap)

---

## 1. Project Overview

A Django 5.2 / DRF university medical API with JWT auth, RBAC, Celery background tasks, FCM push notifications, and Swagger docs.

**Stack:** Django 5.2 · DRF · SimpleJWT + Token Blacklist · Celery + Redis · MySQL (prod) / SQLite (dev) · Firebase Admin SDK · drf-spectacular

**Domain models:** `User`, `PatientProfile`, `DoctorProfile`, `Appointment`, `Examination`, `Ticket`, `TicketReply`, `QueueEntry`, `FCMDeviceToken`, `UploadedFile`, `AuditLog`

**Endpoint groups:** Auth · Patient Dashboard · Doctor Workflow · Scheduling · Consulting · Queue · Notifications · Admin · Utilities

---

## 2. Architecture Assessment

### ✅ Strengths

| Area | Detail |
|------|--------|
| **RBAC design** | Clean three-role model (STUDENT / DOCTOR / ADMIN) with dedicated permission classes |
| **Custom User model** | Properly extends `AbstractUser` with UUID PK; correct `AUTH_USER_MODEL` setting |
| **Serializer segregation** | Separate Create / Update / Finalize serializers per resource — avoids over-posting |
| **Audit trail** | `AuditLog` captures user, IP, user-agent, and diff for all sensitive operations |
| **Immutable records** | `Examination.finalize()` locks the record; guards against post-finalization writes |
| **Atomic transactions** | `transaction.atomic()` used correctly in examination, ticket, and admin batch-create flows |
| **DB indexes** | Thoughtful composite indexes on hot query paths (role+is_active, patient+date, status+timestamp) |
| **Health check** | `/api/v1/health/` checks DB and Redis; returns 503 on failure |
| **FCM mock fallback** | `send_fcm_notification` gracefully mocks when Firebase creds are absent |

### ⚠️ Structural Concerns

**2.1 — Single-app monolith**
Everything lives in one `mainAPI` app. As the project grows, splitting into `accounts`, `appointments`, `consultations`, `notifications` sub-apps would improve isolation and testability.

**2.2 — `UserProfileViewSet` is not a real ViewSet**
`UserProfileViewSet` extends `GenericViewSet` and manually routes everything through `@action`. Plain `APIView` subclasses would be clearer and avoid unnecessary ViewSet overhead.

**2.3 — `UploadedFile.url` is stored redundantly**
The model has both `file = ImageField(...)` and `url = URLField()`. The `url` field is computed after save (two DB writes per upload). Use a `@property` or remove the field entirely.

**2.4 — No API versioning strategy**
The prefix `/api/v1/` exists but there is no versioning middleware. Adding a second version would require manual URL duplication.

---

## 3. Security Analysis

### 🔴 High Priority

**3.1 — Hardcoded insecure SECRET_KEY fallback**
`settings.py` line 29 has a fallback insecure secret key. If `.env` is missing, the app silently uses it.

```python
# Current (dangerous)
SECRET_KEY = config("SECRET_KEY", default="django-insecure-f=4*oernq...")

# Fix: remove default so it raises ImproperlyConfigured
SECRET_KEY = config("SECRET_KEY")
```

**3.2 — `ALLOWED_HOSTS = ["*"]` in development**
This bleeds into staging/CI environments that set `DEVELOPMENT=True`. Use an explicit list.

**3.3 — IP spoofing via `X-Forwarded-For`**
`get_client_ip()` trusts the first value in `HTTP_X_FORWARDED_FOR` unconditionally without a trusted proxy list. Audit log IPs can be spoofed in development.

**3.4 — Placeholder email domain in responses**
`CreateAccountSerializer.create()` generates `{username}@placeholder.local` when no email is provided. This leaks an internal convention in API responses.

**3.5 — ChangePassword does not call Django password validators**
`ChangePasswordRequestSerializer` only requires `new_password` to be non-empty. Django's `AUTH_PASSWORD_VALIDATORS` in settings are NOT called in the view. Must add:

```python
from django.contrib.auth.password_validation import validate_password
validate_password(new_password, user=user)
```

### 🟡 Medium Priority

**3.6 — No dedicated throttle on login endpoint**
`LoginView` relies only on DRF's global anon throttle (`10/minute`). A targeted brute-force on known usernames is feasible. Apply a tighter custom throttle specifically to `LoginView`.

**3.7 — `Examination.doctor` FK uses `on_delete=CASCADE`**
If a doctor account is deleted, all their examination records are destroyed. Medical records must survive staff changes — use `on_delete=PROTECT`.

**3.8 — `TicketReply.save()` overwrites `is_staff_reply` on every save**
The role check runs on every `save()` call, not just on creation. Add `if not self.pk:` guard.

**3.9 — Queue number generation race condition**
The `while True / IntegrityError` retry loop works but creates a tight spin under load. A `SELECT FOR UPDATE` on the max row would be more robust.

---

## 4. Bugs & Issues

### 🔴 High Priority

**4.1 — `auto_close_inactive_tickets` may not close unanswered tickets**
The task filters on `last_reply_at__lt=threshold`. Since `last_reply_at` defaults to `NULL` on a new ticket, and `NULL < threshold` is False in SQL, tickets that were never replied to sit open forever. Add `Q(last_reply_at__isnull=True, created_at__lt=threshold)` if you want to auto-close them too.

**4.2 — Can re-open cancelled appointments**
`AppointmentPatchSerializer.validate()` blocks modifying `COMPLETED` appointments but has no guard for `CANCELLED`. A user can PATCH a cancelled appointment back to `PENDING`.

```python
# Fix: add to validate()
if instance.status == "CANCELLED":
    raise serializers.ValidationError("Cannot modify a cancelled appointment")
```

**4.3 — `hasattr(appointment, "examination")` is unreliable**
Accessing a missing OneToOne reverse relation raises `RelatedObjectDoesNotExist`, it does not return `False`. The correct check:

```python
# Wrong (ExaminationCreateSerializer line 123)
if hasattr(appointment, "examination"):

# Correct
try:
    _ = appointment.examination
    raise serializers.ValidationError("This appointment already has an examination")
except Examination.DoesNotExist:
    pass
```

**4.4 — `PatientSummarySerializer` crashes if `patient_profile` does not exist**
Fields using `source="patient_profile.blood_type"` will raise `AttributeError` if the `PatientProfile` row was never created. This happens on doctor-side patient lookup. Add null-safety via `SerializerMethodField` or `try/except`.

**4.5 — Audit log uses `APPOINTMENT_CREATED` for generic appointment updates**
```python
# views/appointment.py line 217
else:
    audit_action = AuditLog.Action.APPOINTMENT_CREATED  # Generic update
```
A reschedule is incorrectly logged as a creation. Add a dedicated `APPOINTMENT_UPDATED` action.

**4.6 — Duplicate tickets in doctor queryset**
```python
return (Ticket.objects.filter(assigned_to=user) | Ticket.objects.filter(status="OPEN"))
```
A ticket assigned to the doctor that is also OPEN appears twice. Use `Q` objects:
```python
from django.db.models import Q
return Ticket.objects.filter(
    Q(assigned_to=user) | Q(status="OPEN")
).select_related("creator", "assigned_to").distinct()
```

### 🟡 Medium Priority

**4.7 — `ImageUploadSerializer` reads the file MIME type twice**
`validate_file` reads and seeks back, then `create()` reads again. Store detected MIME in `validate_file` and attach to context.

**4.8 — `my_examinations` endpoint lacks pagination**
Returns all examinations for a user in one response, bypassing the global `PAGE_SIZE=20` setting.

**4.9 — Two DB writes to `Ticket` on every staff reply**
`add_reply` calls `ticket.save(update_fields=["status"])` and `TicketReply.save()` calls `ticket.save(update_fields=["last_reply_at"])` — two round-trips. Combine into one.

---

## 5. Performance

**5.1 — N+1 on PatientSummarySerializer in list context**
`_get_last_exam` caches within one serialization but not across a list. Add `prefetch_related("examinations_as_patient")` at the view queryset level when using this serializer for multiple users.

**5.2 — N+1 on ticket list (last_reply per ticket)**
```python
# ticket/serializers.py
last_reply = obj.replies.order_by("-created_at").first()  # 1 query per ticket
```
Fix with:
```python
from django.db.models import Prefetch
queryset.prefetch_related(
    Prefetch("replies", queryset=TicketReply.objects.order_by("-created_at"))
)
```

**5.3 — No caching on `GET /queues/current`**
This endpoint is likely polled frequently by a display board. The result changes only when a doctor calls a patient. Add a short cache (5–10 seconds) with invalidation in `call_patient`.

**5.4 — Celery task saves tickets one-by-one**
```python
for ticket in tickets:
    ticket.close()  # individual save per ticket
```
Replace with bulk update:
```python
tickets.update(status="RESOLVED", resolved_at=timezone.now())
```

---

## 6. Code Quality

**6.1 — Mixed line endings**
Most files use CRLF (`\r\n`) but `queue.py`, `notification.py`, `fcm.py`, and `serializers/queue.py` use LF (`\n`). Add a `.gitattributes` file to enforce consistent endings.

**6.2 — No version pins in `requirements.txt`**
Every package listed without version constraints. Add `~=` pins or maintain a `requirements.lock` produced by `pip freeze`.

**6.3 — Unused dependencies**
`django-ratelimit` and `django-environ` are listed but never used. Remove them.

**6.4 — `mainAPI/views.py` is an empty stub**
A `views.py` file coexists with the `views/` package. This is a leftover scaffold file. Delete it.

**6.5 — Magic role/status strings instead of enum constants**
Role strings (`"STUDENT"`, `"DOCTOR"`, `"ADMIN"`) and status strings are used as bare literals throughout views and serializers. Use the class enums consistently:

```python
# Bad
if user.role == "STUDENT":

# Good
if user.role == User.Role.STUDENT:
```

**6.6 — Import inside methods**
`ExaminationCreateSerializer.validate()` imports `User` inside the method; `CreateAccountSerializer.create()` imports `PatientProfile` and `uuid` inside `create()`. Move all to top-level imports.

**6.7 — `PatientSummarySerializer` has 20+ identical `DecimalField` declarations**
Each differs only by `source`. A `to_representation` override or a field factory would reduce boilerplate by ~80%.

**6.8 — `django-debug-toolbar` not gated by `DEBUG`**
Listed in `requirements.txt` unconditionally. It should only be added to `INSTALLED_APPS` when `DEBUG=True` to avoid importing it in production.

---

## 7. Testing

**`tests.py` is completely empty.**

There are **zero tests** in the entire project. This is the most critical gap for a medical data API. Minimum test coverage needed:

| Priority | Test Case |
|----------|-----------|
| 🔴 | Auth: login, refresh, logout, blacklist enforcement |
| 🔴 | Permission: student cannot access doctor endpoints and vice versa |
| 🔴 | Appointment: duplicate booking blocked, past date blocked |
| 🔴 | Examination: finalized record rejects updates |
| 🔴 | Queue: auto-increment, cancel own entry only |
| 🟡 | Audit log created on examination create/finalize/update |
| 🟡 | Ticket auto-close Celery task logic |
| 🟡 | FCM mock mode when no credentials |
| 🟡 | Image upload: rejects non-image MIME, rejects >10MB |

---

## 8. Dependency Analysis

| Package | Status | Notes |
|---------|--------|-------|
| `django-ratelimit` | ❌ Unused | Remove; DRF throttling already configured |
| `django-environ` | ❌ Unused | Remove; `python-decouple` already handles env vars |
| `django-db-connection-pool` | ⚠️ Unconfigured | Listed but not set up in `DATABASES`; configure or remove |
| `django-debug-toolbar` | ⚠️ Not gated | Should only be active when `DEBUG=True` |
| `redis` | ✅ Used | Celery broker + cache backend |
| `firebase-admin` | ✅ Used | FCM push notifications |
| `python-magic` | ✅ Used | MIME validation in image upload |
| `sentry-sdk` | ✅ Conditionally used | Correctly initialized only when DSN is set and not DEBUG |

---

## 9. Summary Table

| # | Issue | Severity | Category |
|---|-------|----------|----------|
| 3.1 | Hardcoded insecure SECRET_KEY fallback | 🔴 High | Security |
| 3.5 | Password validators not called on change-password | 🔴 High | Security |
| 3.7 | Examination.doctor FK CASCADE deletes medical records | 🔴 High | Security/Data |
| 4.3 | `hasattr` on OneToOne reverse accessor unreliable | 🔴 High | Bug |
| 4.4 | PatientSummarySerializer crashes if profile missing | 🔴 High | Bug |
| 7.1 | Zero tests in the entire project | 🔴 High | Testing |
| 3.6 | No dedicated brute-force throttle on login | 🟡 Medium | Security |
| 3.8 | TicketReply overwrites is_staff_reply on every save | 🟡 Medium | Bug |
| 4.1 | Auto-close task may miss unanswered tickets | 🟡 Medium | Bug |
| 4.2 | Can re-open cancelled appointments | 🟡 Medium | Bug |
| 4.5 | Audit action mislabeled on appointment update | 🟡 Medium | Bug |
| 4.6 | Duplicate tickets in doctor queryset | 🟡 Medium | Bug |
| 5.1 | N+1 on PatientSummarySerializer in list context | 🟡 Medium | Performance |
| 5.2 | N+1 on ticket list (last_reply per ticket) | 🟡 Medium | Performance |
| 6.2 | No version pins in requirements.txt | 🟡 Medium | DevOps |
| 4.8 | my_examinations endpoint lacks pagination | 🟡 Medium | Performance |
| 6.5 | Magic strings instead of enum constants | 🟢 Low | Code Quality |
| 6.1 | Mixed line endings in codebase | 🟢 Low | Code Quality |
| 6.3 | Unused dependencies in requirements.txt | 🟢 Low | DevOps |
| 6.7 | Overly verbose PatientSummarySerializer | 🟢 Low | Code Quality |
| 5.3 | No caching on current-queue endpoint | 🟢 Low | Performance |
| 5.4 | Celery task saves tickets one-by-one | 🟢 Low | Performance |
| 2.3 | Redundant `url` field on UploadedFile | 🟢 Low | Architecture |

---

## 10. Recommendations Roadmap

### Phase 1 — Fix Critical Bugs & Security (do now)
1. Remove `SECRET_KEY` default fallback from settings
2. Call `validate_password()` in `ChangePasswordView`
3. Change `Examination.doctor` FK to `on_delete=PROTECT`
4. Fix `hasattr(appointment, "examination")` → try/except
5. Add null-safety to `PatientSummarySerializer` for missing `patient_profile`
6. Add guard against re-opening cancelled appointments

### Phase 2 — Fix Medium Bugs & Performance
7. Replace `|` QuerySet union with `Q()` in `TicketViewSet.get_queryset`
8. Add `prefetch_related` for `replies` in ticket list view
9. Fix audit action mislabeling for appointment updates
10. Fix `TicketReply.save()` to set `is_staff_reply` only on creation
11. Add pagination to `my_examinations`
12. Use enum constants consistently throughout views/serializers

### Phase 3 — Testing & Developer Experience
13. Write test suite covering auth, permissions, all CRUD flows, and edge cases
14. Pin dependency versions in `requirements.txt`
15. Add `.gitattributes` for consistent line endings
16. Remove unused packages and add `DEBUG` gate for debug-toolbar

### Phase 4 — Architecture & Scalability
17. Add `APPOINTMENT_UPDATED` audit action
18. Cache `GET /queues/current` with short TTL + invalidation on `call_patient`
19. Refactor `PatientSummarySerializer` to reduce 20+ field declarations
20. Consider splitting `mainAPI` into domain sub-apps as the project grows
