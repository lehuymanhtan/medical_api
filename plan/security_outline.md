# Security Outline - Medical Management System

## Document Information
- **Project**: University Healthcare Management System
- **Version**: 1.0.0
- **Date**: December 26, 2025
- **Based On**: api.yaml v1.0.0, model.md

---

## Table of Contents
1. [Security Overview](#security-overview)
2. [Authentication & Authorization](#authentication--authorization)
3. [Data Protection](#data-protection)
4. [API Security](#api-security)
5. [Access Control (RBAC)](#access-control-rbac)
6. [Audit & Compliance](#audit--compliance)
7. [File Upload Security](#file-upload-security)
8. [Database Security](#database-security)
9. [Network Security](#network-security)
10. [Threat Mitigation](#threat-mitigation)
11. [Security Implementation Checklist](#security-implementation-checklist)

---

## Security Overview

### Security Goals
1. **Confidentiality**: Protect sensitive medical data from unauthorized access
2. **Integrity**: Ensure data accuracy and prevent unauthorized modifications
3. **Availability**: Maintain system accessibility for authorized users
4. **Compliance**: Meet healthcare data protection regulations (HIPAA-like standards)
5. **Auditability**: Track all sensitive operations for forensic analysis

### Security Principles
- **Least Privilege**: Users only access data necessary for their role
- **Defense in Depth**: Multiple layers of security controls
- **Fail Secure**: System defaults to deny access on errors
- **Privacy by Design**: Security built into every feature
- **Zero Trust**: Verify every request, never assume trust

---

## Authentication & Authorization

### 1. Authentication Strategy

#### JWT (JSON Web Token) Authentication
```
Technology: djangorestframework-simplejwt
Token Type: Bearer Token
Algorithm: HS256 or RS256
```

**Token Configuration**:
- **Access Token Lifetime**: 8 hours (work shift duration)
- **Refresh Token Lifetime**: 7 days
- **Token Storage**: Client-side (localStorage with HttpOnly cookie option)
- **Token Claims**: user_id, role, issued_at, expiration

**Login Flow** (`POST /auth/login`):
1. User submits username + password
2. Validate credentials against User model
3. Generate access token + refresh token
4. Return tokens + user profile
5. Log authentication event in AuditLog

**Security Measures**:
- Rate limiting: Max 5 login attempts per minute per IP
- Account lockout: 30 minutes after 5 failed attempts
- Password requirements:
  - Minimum 8 characters
  - Must contain: uppercase, lowercase, number, special character
  - Cannot be common passwords (Django's password validators)
- Passwords hashed with PBKDF2 (Django default) or Argon2
- No password storage in plaintext anywhere

#### Session Management
- Tokens invalidated on logout
- Refresh token rotation on renewal
- Detect concurrent sessions (optional)
- Force re-authentication for sensitive operations (examination finalization)

---

### 2. Authorization & RBAC

#### Role Definitions

**STUDENT (Patient)**:
- View own profile and medical summary
- Create and view own appointments
- Cancel own appointments (before completion)
- View own examination history
- Create and view own tickets
- Reply to own tickets
- Upload images (limited to ticket attachments)

**DOCTOR**:
- View assigned appointments
- Scan QR codes to lookup patients
- View patient medical history (via QR or appointment)
- Create and update examinations
- Finalize examinations (immutable record)
- View and reply to all tickets
- Upload medical images (examination attachments)
- Access patient records (with audit logging)

**ADMIN (Super Doctor)**:
- All DOCTOR permissions
- Manage doctor schedules (optional TimeSlot model)
- Assign tickets to doctors
- View system-wide statistics
- Access audit logs
- Manage user accounts (create, deactivate)

#### Permission Enforcement

**Django Permission Classes**:
```python
# Custom permission classes
IsStudent
IsDoctor
IsDoctorOrAdmin
IsOwnerOrStaff
IsPatientOwner
```

**Row-Level Permissions**:
- Students can only access their own data (appointments, examinations, tickets)
- Doctors can access patient data only through valid workflows:
  - QR scan lookup (with audit log)
  - Assigned appointments
  - Ticket assignment
- Admins have broader access (still logged)

**API Endpoint Authorization Matrix**:

| Endpoint | STUDENT | DOCTOR | ADMIN |
|----------|---------|--------|-------|
| `POST /auth/login` | ✓ | ✓ | ✓ |
| `GET /users/me` | ✓ (own) | ✓ (own) | ✓ (own) |
| `GET /users/me/medical-summary` | ✓ | - | - |
| `GET /users/me/examinations` | ✓ | - | - |
| `GET /patients/lookup` | - | ✓ | ✓ |
| `GET /patients/{id}/examinations` | - | ✓ | ✓ |
| `GET /appointments` | ✓ (own) | ✓ (assigned) | ✓ (all) |
| `POST /appointments` | ✓ | - | - |
| `PATCH /appointments/{id}` | ✓ (own) | ✓ (status) | ✓ |
| `POST /examinations` | - | ✓ | ✓ |
| `PUT /examinations/{id}` | - | ✓ (own) | ✓ |
| `POST /examinations/{id}/finalize` | - | ✓ (own) | ✓ |
| `GET /tickets` | ✓ (own) | ✓ (assigned/all) | ✓ (all) |
| `POST /tickets` | ✓ | - | - |
| `GET /tickets/{id}` | ✓ (own) | ✓ (assigned) | ✓ |
| `POST /tickets/{id}/close` | ✓ (own) | ✓ (assigned) | ✓ |
| `POST /tickets/{id}/replies` | ✓ (own) | ✓ (assigned) | ✓ |
| `POST /upload/image` | ✓ (limited) | ✓ | ✓ |

---

## Data Protection

### 1. Sensitive Data Classification

**Critical (Highest Protection)**:
- Patient medical records (Examination model)
- Diagnoses (initial_diagnosis, final_diagnosis)
- Prescriptions
- Vital signs
- Medical history

**High (Strong Protection)**:
- User credentials (passwords, tokens)
- Personal identifiers (student_id, email)
- Patient profile data (allergies, blood type, chronic conditions)
- Appointment details

**Medium (Protected)**:
- Ticket conversations
- Audit logs
- Uploaded files

**Low (General Protection)**:
- User full names
- Doctor specializations
- Appointment dates (without details)

---

### 2. Data Encryption

#### Encryption at Rest
**Database Encryption**:
- Enable MySQL transparent data encryption (TDE)
- Encrypt backup files
- Secure database credentials in environment variables

**Field-Level Encryption** (for ultra-sensitive data):
```python
# Consider encrypting these fields
- PatientProfile.allergies
- PatientProfile.chronic_conditions
- Examination.final_diagnosis
- Examination.prescription
```

**Implementation Options**:
- Django `django-encrypted-model-fields`
- Application-level encryption with AES-256
- Key management via environment variables or AWS KMS/HashiCorp Vault

#### Encryption in Transit
- **TLS/HTTPS Only**: All API communication over HTTPS
- **Certificate Requirements**: Valid SSL certificate (Let's Encrypt or commercial CA)
- **TLS Version**: Minimum TLS 1.2, prefer TLS 1.3
- **Cipher Suites**: Strong ciphers only (no RC4, no MD5)
- **HSTS Header**: Enforce HTTPS in browsers

---

### 3. Data Minimization
- Only collect necessary medical information
- Avoid storing unnecessary sensitive data
- Auto-delete resolved tickets after 1 year (configurable)
- Anonymize old audit logs (keep action statistics)

---

### 4. Data Masking
- Mask sensitive data in logs
- Redact patient details in error messages
- Partial display of sensitive IDs in admin interfaces

---

## API Security

### 1. Input Validation

**Request Validation**:
- **Schema Validation**: All requests validated against OpenAPI schema
- **Django REST Framework Serializers**: Strict field validation
- **Type Checking**: Enforce data types (UUID, date, email, etc.)
- **Length Limits**: Max field lengths enforced
- **Allowed Characters**: Sanitize input to prevent injection

**Specific Validations**:
```python
# User Input
- Email: Valid format, unique
- Student ID: Alphanumeric, unique
- Passwords: Strong password policy
- Phone numbers: Valid format

# Dates
- appointment_date: Cannot be in past
- appointment_date: Maximum 30 days in future

# Files
- Image uploads: MIME type validation
- File size: Max 10MB
- File extensions: Only .jpg, .jpeg, .png

# Business Logic
- One appointment per patient per day
- Cannot finalize examination without final_diagnosis and prescription
- Cannot cancel completed appointments
```

---

### 2. Injection Prevention

#### SQL Injection
- **Django ORM Only**: Never use raw SQL queries
- **Parameterized Queries**: ORM handles automatically
- **Escape Special Characters**: ORM sanitizes inputs

#### XSS (Cross-Site Scripting)
- **Output Encoding**: Django templates auto-escape
- **Content Security Policy (CSP)**: Restrict inline scripts
- **Sanitize Rich Text**: If using WYSIWYG editors

#### Command Injection
- **No Shell Commands**: Avoid `os.system()`, `subprocess` with user input
- **File Operations**: Use Django's File API

---

### 3. Rate Limiting

**API Rate Limits** (using `django-ratelimit` or DRF throttling):

```python
# Authentication Endpoints
/auth/login: 5 requests/minute per IP

# Patient Lookup (QR Scan)
/patients/lookup: 30 requests/minute per user (prevent brute-force QR guessing)

# General API
Authenticated users: 100 requests/minute
Unauthenticated: 10 requests/minute

# File Upload
/upload/image: 10 uploads/hour per user
```

**Implementation**:
```python
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '10/minute',
        'user': '100/minute',
        'login': '5/minute',
    }
}
```

---

### 4. CORS (Cross-Origin Resource Sharing)

**Configuration** (using `django-cors-headers`):
```python
CORS_ALLOWED_ORIGINS = [
    "https://medical.university.edu",
    "https://student-portal.university.edu",
]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
    'OPTIONS',
]

CORS_ALLOW_HEADERS = [
    'authorization',
    'content-type',
    'x-requested-with',
]
```

---

### 5. Security Headers

**Required HTTP Headers**:
```python
# Django Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Custom Middleware for additional headers
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';
```

---

## Access Control (RBAC)

### 1. QR Code Security

**QR Code Design**:
- Contains: Patient UUID (User.id)
- Format: `{UUID}` (e.g., `550e8400-e29b-41d4-a716-446655440000`)
- Non-sequential, unpredictable
- No sensitive data encoded

**Lookup Security** (`GET /patients/lookup?qr_code={uuid}`):
1. **Authentication Required**: Only DOCTOR/ADMIN roles
2. **Rate Limiting**: Max 30 lookups/minute
3. **Audit Logging**: Every lookup creates AuditLog entry
   - Who accessed
   - When accessed
   - Which patient
   - IP address
   - User agent
4. **Validation**: UUID format validation
5. **Access Control**: Verify requester has DOCTOR/ADMIN role

**QR Code Display**:
- Generated client-side from UUID
- Displayed only to patient (in their app/portal)
- Regenerate QR if UUID changes (user account recreation)

---

### 2. Patient Record Access

**Access Workflows**:

**Workflow 1: QR Scan (Direct Lookup)**
```
Doctor scans QR → GET /patients/lookup?qr_code={uuid}
→ Verify doctor role
→ Fetch patient summary
→ Log access (PATIENT_RECORD_ACCESSED)
→ Return data
```

**Workflow 2: Appointment-Based Access**
```
Doctor views appointments → GET /appointments
→ Returns only doctor's assigned appointments
→ Doctor clicks patient → GET /patients/{id}/examinations
→ Verify patient is in doctor's appointment list OR doctor is admin
→ Log access (PATIENT_HISTORY_VIEWED)
→ Return data
```

**Workflow 3: Examination Creation**
```
Doctor creates exam → POST /examinations
→ Verify appointment exists and not already examined
→ Verify patient_id matches appointment
→ Create examination
→ Log action (EXAMINATION_CREATED)
```

**Access Denied Scenarios**:
- Student tries to access another student's data
- Doctor tries to access patient without valid workflow
- Expired or invalid token
- Insufficient permissions

---

### 3. Immutable Records

**Examination Finalization**:
- Status: DRAFT → COMPLETED (one-way transition)
- Once COMPLETED, no further edits allowed
- `finalized_at` timestamp set
- Audit log entry: EXAMINATION_FINALIZED

**Implementation**:
```python
# In Examination model save() method
def save(self, *args, **kwargs):
    if self.pk:  # Existing record
        old_instance = Examination.objects.get(pk=self.pk)
        if old_instance.status == 'COMPLETED':
            # Prevent any changes to completed examinations
            raise PermissionDenied("Cannot modify finalized examination")
    super().save(*args, **kwargs)
```

**Finalize Endpoint** (`POST /examinations/{id}/finalize`):
1. Verify current status is DRAFT
2. Validate required fields (final_diagnosis, prescription)
3. Set status = COMPLETED
4. Set finalized_at = now()
5. Create audit log
6. Lock record from further edits

---

## Audit & Compliance

### 1. Audit Logging

**Logged Actions** (AuditLog model):

**Examination Events**:
- EXAMINATION_CREATED
- EXAMINATION_UPDATED
- EXAMINATION_FINALIZED

**Appointment Events**:
- APPOINTMENT_CREATED
- APPOINTMENT_CANCELLED
- APPOINTMENT_COMPLETED

**Ticket Events**:
- TICKET_CREATED
- TICKET_CLOSED
- TICKET_ASSIGNED

**Data Access Events**:
- PATIENT_RECORD_ACCESSED (QR scan lookup)
- PATIENT_HISTORY_VIEWED (examination history)
- QR_SCAN_LOOKUP (specifically for QR scans)

**Authentication Events**:
- USER_LOGIN
- USER_LOGOUT (if implemented)

**Audit Log Entry Structure**:
```json
{
  "id": "uuid",
  "user": "doctor_user_id",
  "action": "PATIENT_RECORD_ACCESSED",
  "model_name": "User",
  "object_id": "patient_uuid",
  "object_repr": "John Doe (student_id: 12345)",
  "changes": {},
  "additional_data": {
    "qr_code": "550e8400-e29b-41d4-a716-446655440000",
    "access_method": "qr_scan"
  },
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "timestamp": "2025-12-26T10:30:00Z"
}
```

---

### 2. Audit Trail Properties

**Characteristics**:
- **Append-Only**: No deletions or modifications
- **Immutable**: Once written, cannot be changed
- **Comprehensive**: Captures who, what, when, where, why
- **Tamper-Evident**: Checksums or signatures (optional enhancement)

**Retention Policy**:
- Medical records: Minimum 7 years (regulatory requirement)
- Audit logs: Minimum 7 years
- Resolved tickets: 1 year, then archive/anonymize
- User accounts: Soft delete, retain 5 years

---

### 3. Compliance Requirements

#### HIPAA-Like Standards (Adapt based on jurisdiction)

**Administrative Safeguards**:
- Role-based access control
- User training on data handling
- Incident response plan
- Regular security audits

**Physical Safeguards**:
- Secure server hosting
- Physical access controls to servers
- Workstation security policies

**Technical Safeguards**:
- Access controls (authentication, authorization)
- Audit controls (comprehensive logging)
- Integrity controls (prevent unauthorized data alteration)
- Transmission security (HTTPS/TLS)

**Breach Notification**:
- Detect unauthorized access (monitoring audit logs)
- Notification procedures (admin alerts)
- User notification requirements (if patient data exposed)

---

### 4. Audit Log Monitoring

**Security Monitoring**:
- Unusual access patterns (e.g., doctor accessing 50+ patient records in 1 minute)
- After-hours access to sensitive data
- Multiple failed login attempts
- Repeated QR scan failures
- Mass data exports (not implemented but monitor for future)

**Alerting**:
- Email alerts for suspicious activity
- Dashboard for security team
- Daily/weekly audit reports

**Tools**:
- Django Admin custom views for audit logs
- ELK Stack (Elasticsearch, Logstash, Kibana) for log analysis
- Splunk or similar SIEM tools

---

## File Upload Security

### 1. File Validation

**Allowed File Types**:
- Images only: `.jpg`, `.jpeg`, `.png`
- Validate by MIME type AND file extension
- Check magic bytes (file signature)

**Validation Steps**:
1. Check file extension
2. Validate MIME type (`image/jpeg`, `image/png`)
3. Verify file size (max 10MB)
4. Check image integrity (use Pillow to open and validate)
5. Scan for malware (optional: ClamAV integration)

**Implementation**:
```python
# Custom validator
def validate_image_file(file):
    # Check size
    if file.size > 10 * 1024 * 1024:
        raise ValidationError("File too large (max 10MB)")
    
    # Check MIME type
    if file.content_type not in ['image/jpeg', 'image/png']:
        raise ValidationError("Invalid file type")
    
    # Verify it's actually an image
    try:
        from PIL import Image
        image = Image.open(file)
        image.verify()
    except Exception:
        raise ValidationError("Corrupted image file")
```

---

### 2. File Storage

**Storage Configuration**:
- **Upload Path**: `media/uploads/%Y/%m/%d/`
- **Filename**: UUID-based (prevent overwriting and directory traversal)
- **Permissions**: Files not directly executable
- **Serving**: Via Django (dev) or CDN/S3 (production)

**Secure File Serving**:
```python
# Don't serve files directly from web root
# Use Django views with authentication checks
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def serve_uploaded_file(request, file_id):
    file_obj = UploadedFile.objects.get(id=file_id)
    
    # Check permissions
    if not has_access_to_file(request.user, file_obj):
        return Response(status=403)
    
    # Serve file
    return FileResponse(file_obj.file.open())
```

**Production Storage**:
- Use AWS S3 with pre-signed URLs
- Set bucket policies (private, no public access)
- Enable versioning and logging
- Regular backups

---

### 3. Malware Scanning

**Optional Enhancements**:
- Integrate ClamAV or similar antivirus
- Scan uploaded files before storage
- Quarantine suspicious files

```python
# Example: ClamAV integration
import pyclamd

def scan_file_for_malware(file_path):
    cd = pyclamd.ClamdUnixSocket()
    scan_result = cd.scan_file(file_path)
    if scan_result and scan_result[file_path][0] == 'FOUND':
        raise ValidationError("Malware detected in uploaded file")
```

---

## Database Security

### 1. Connection Security

**MySQL Configuration**:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'ssl': {
                'ca': '/path/to/ca-cert.pem',
                'cert': '/path/to/client-cert.pem',
                'key': '/path/to/client-key.pem',
            },
        },
    }
}
```

**Security Measures**:
- Use environment variables for credentials (never hardcode)
- Enable SSL/TLS for database connections
- Use dedicated database user (not root)
- Grant minimal permissions (SELECT, INSERT, UPDATE, DELETE only on necessary tables)
- Disable remote root access
- Regular password rotation

---

### 2. Query Security

**ORM Usage**:
- Always use Django ORM (no raw SQL)
- If raw SQL necessary, use parameterized queries

**Example of SAFE query**:
```python
# GOOD: Django ORM (safe)
patients = User.objects.filter(role='STUDENT', full_name__icontains=search_term)

# GOOD: Parameterized raw query (if absolutely necessary)
patients = User.objects.raw(
    "SELECT * FROM users WHERE role = %s AND full_name LIKE %s",
    ['STUDENT', f'%{search_term}%']
)
```

**Example of UNSAFE query** (NEVER DO THIS):
```python
# BAD: String concatenation (SQL injection vulnerability)
query = f"SELECT * FROM users WHERE full_name = '{search_term}'"
```

---

### 3. Database Hardening

**MySQL Security**:
1. Remove test databases
2. Disable anonymous accounts
3. Set strong root password
4. Restrict network access (bind to localhost or private IP)
5. Enable query logging (slow query log, error log)
6. Regular security updates
7. Implement database firewall rules

**Backup Security**:
- Encrypt backup files
- Store backups in secure location (off-site)
- Test restoration procedures
- Access controls on backup storage
- Retain backups per compliance requirements (7+ years)

---

## Network Security

### 1. Firewall Configuration

**Server Firewall** (ufw/iptables):
```bash
# Allow only necessary ports
Allow: 443 (HTTPS)
Allow: 22 (SSH, restricted IPs only)
Deny: All other incoming traffic

# Restrict SSH access
Allow SSH only from admin IP addresses
Disable root SSH login
Use SSH keys (disable password auth)
```

---

### 2. DDoS Protection

**Mitigation Strategies**:
- Use CDN (CloudFlare, AWS CloudFront) for DDoS protection
- Rate limiting at API and network levels
- Web Application Firewall (WAF) rules
- Monitor traffic patterns
- Auto-scaling for traffic spikes

---

### 3. Network Segmentation

**Recommended Architecture**:
```
[Internet]
    ↓
[Load Balancer / WAF]
    ↓
[Web Servers (DMZ)]
    ↓
[Application Servers (Private Network)]
    ↓
[Database Servers (Private Network, separate subnet)]
```

---

## Threat Mitigation

### 1. OWASP Top 10 Mitigations

#### A01: Broken Access Control
- **Mitigation**: RBAC implementation, row-level permissions, audit logging
- **Tests**: Verify users cannot access other users' data

#### A02: Cryptographic Failures
- **Mitigation**: HTTPS/TLS, encrypted database fields, strong password hashing
- **Tests**: Verify no sensitive data in logs, URLs, or error messages

#### A03: Injection
- **Mitigation**: Django ORM, input validation, parameterized queries
- **Tests**: Test with SQL injection payloads

#### A04: Insecure Design
- **Mitigation**: Security requirements in design phase, threat modeling
- **Tests**: Review architecture for security flaws

#### A05: Security Misconfiguration
- **Mitigation**: Security headers, disable debug mode in production, regular updates
- **Tests**: Security scanners (OWASP ZAP, Nmap)

#### A06: Vulnerable Components
- **Mitigation**: Regular dependency updates, vulnerability scanning
- **Tests**: Use `safety` package, Dependabot

#### A07: Authentication Failures
- **Mitigation**: Strong password policy, MFA (optional), rate limiting, account lockout
- **Tests**: Brute force attack simulation

#### A08: Software and Data Integrity Failures
- **Mitigation**: Digital signatures, verified dependencies, CI/CD security
- **Tests**: Verify package integrity

#### A09: Security Logging Failures
- **Mitigation**: Comprehensive audit logging, log monitoring, alerting
- **Tests**: Verify all sensitive operations logged

#### A10: Server-Side Request Forgery (SSRF)
- **Mitigation**: Input validation, no user-controlled URLs, network segmentation
- **Tests**: Not applicable (no URL fetching features in API)

---

### 2. Attack Scenarios & Defenses

#### Scenario 1: Unauthorized Patient Record Access
**Attack**: Student tries to access another student's medical records
**Defense**:
- Row-level permissions (filter by `request.user`)
- ViewSet checks object ownership
- Returns 403 Forbidden
- Attempt logged in audit trail

#### Scenario 2: QR Code Brute Force
**Attack**: Attacker tries to guess patient UUIDs via `/patients/lookup`
**Defense**:
- Rate limiting (30 requests/minute)
- UUID format validation (reduces search space from being obvious)
- Requires DOCTOR/ADMIN authentication
- All attempts logged (detect patterns)
- Alert on suspicious activity (100+ failed lookups)

#### Scenario 3: Examination Tampering
**Attack**: Doctor tries to modify finalized examination
**Defense**:
- Status check in model `save()` method
- Raises PermissionDenied exception
- Immutable once COMPLETED
- Audit log shows finalization timestamp

#### Scenario 4: Privilege Escalation
**Attack**: Student tries to access doctor-only endpoints
**Defense**:
- RBAC checks on every endpoint
- `permission_classes` decorators
- Returns 403 Forbidden
- Attempt logged

#### Scenario 5: Token Theft
**Attack**: Attacker steals JWT token
**Defense**:
- Short token lifetime (8 hours)
- HTTPS only (prevent man-in-the-middle)
- Secure token storage (HttpOnly cookies)
- Optional: Device fingerprinting, IP validation
- User can logout to invalidate token

#### Scenario 6: Malicious File Upload
**Attack**: Upload PHP script disguised as image
**Defense**:
- MIME type validation
- File magic bytes check
- Pillow image verification
- Non-executable upload directory
- Files served through application (not direct web access)
- Optional: Malware scanning

---

## Security Implementation Checklist

### Phase 1: Foundation (Critical)
- [ ] Custom User model with UUID primary key
- [ ] JWT authentication configured
- [ ] Password hashing (PBKDF2 or Argon2)
- [ ] HTTPS/TLS enforced
- [ ] CORS configured
- [ ] RBAC permission classes
- [ ] Row-level permissions for models
- [ ] Security headers middleware

### Phase 2: Data Protection (Critical)
- [ ] Sensitive field encryption (optional but recommended)
- [ ] Database SSL connection
- [ ] Environment variables for secrets
- [ ] File upload validation
- [ ] Secure file storage
- [ ] Input validation on all endpoints

### Phase 3: Monitoring & Audit (Critical)
- [ ] AuditLog model implemented
- [ ] Audit logging middleware/signals
- [ ] All sensitive operations logged
- [ ] Logging configured (not to console in prod)
- [ ] Error tracking (Sentry or similar)

### Phase 4: Hardening (Important)
- [ ] Rate limiting on authentication
- [ ] Rate limiting on API endpoints
- [ ] Account lockout on failed logins
- [ ] Immutable examination records
- [ ] Database backup encryption
- [ ] Backup restoration tested

### Phase 5: Advanced (Recommended)
- [ ] Malware scanning on uploads
- [ ] Intrusion detection system
- [ ] DDoS protection (CDN/WAF)
- [ ] Security audit logging dashboard
- [ ] Alerting on suspicious activity
- [ ] Penetration testing
- [ ] Security training for developers

### Phase 6: Compliance (Regulatory)
- [ ] Data retention policies
- [ ] Breach notification procedures
- [ ] User consent management (if required)
- [ ] Right to access/deletion (GDPR-like)
- [ ] Privacy policy
- [ ] Terms of service
- [ ] Regular compliance audits

---

## Security Testing

### 1. Automated Testing

**Unit Tests**:
```python
# Test permission classes
def test_student_cannot_access_other_patient_data():
    # Create two students
    # Student A tries to access Student B's appointments
    # Assert 403 Forbidden

def test_doctor_cannot_modify_finalized_examination():
    # Create examination, finalize it
    # Try to update
    # Assert PermissionDenied exception

def test_invalid_file_upload_rejected():
    # Upload .exe file
    # Assert ValidationError
```

**Integration Tests**:
- Test full workflows (login → appointment → examination)
- Verify audit logs created
- Test RBAC across multiple users

---

### 2. Security Scanning

**Tools**:
- **OWASP ZAP**: Web application scanner
- **Nmap**: Port scanning, service detection
- **SQLMap**: SQL injection testing
- **Burp Suite**: Manual security testing
- **Bandit**: Python code security scanner
- **Safety**: Python dependency vulnerability scanner

**Commands**:
```bash
# Scan Python dependencies
safety check --full-report

# Scan Python code for security issues
bandit -r mainAPI/

# Check for outdated packages
pip list --outdated
```

---

### 3. Penetration Testing

**Manual Testing Scenarios**:
1. Try to access other users' data
2. Attempt SQL injection on all input fields
3. Try XSS payloads in text fields
4. Test rate limiting (brute force simulation)
5. Upload malicious files
6. Token manipulation attempts
7. CSRF attacks (if using session auth)
8. Privilege escalation attempts

**Third-Party Assessment**:
- Hire professional penetration testers
- Annual security audits
- Vulnerability disclosure program

---

## Incident Response

### 1. Detection

**Monitoring**:
- Failed login spikes
- Unusual API traffic patterns
- Multiple 403 errors from single user
- Mass data access
- After-hours activity

**Alerting**:
- Email/SMS notifications
- Security dashboard
- Integration with incident management tools

---

### 2. Response Procedures

**Incident Severity Levels**:

**Critical** (Data breach, system compromise):
1. Isolate affected systems
2. Preserve evidence (logs, snapshots)
3. Notify security team and management
4. Investigate scope and impact
5. Contain and remediate
6. Notify affected users (if required)
7. Post-incident review

**High** (Attempted unauthorized access):
1. Block attacker IP/account
2. Review audit logs
3. Assess damage
4. Patch vulnerability
5. Monitor for repeat attempts

**Medium** (Suspicious activity):
1. Investigate and document
2. Increase monitoring
3. No immediate action needed

---

### 3. Recovery

**Steps**:
1. Restore from clean backups (if necessary)
2. Patch vulnerabilities
3. Reset compromised credentials
4. Re-enable services
5. Monitor for repeat incidents
6. Document lessons learned
7. Update security procedures

---

## Security Maintenance

### 1. Regular Updates

**Schedule**:
- **Weekly**: Review security logs and alerts
- **Monthly**: Update dependencies (`pip list --outdated`)
- **Quarterly**: Security audit, penetration testing
- **Annually**: Full security review, policy updates

**Dependency Management**:
```bash
# Update packages regularly
pip install --upgrade -r requirements.txt

# Check for vulnerabilities
safety check

# Audit Django security
python manage.py check --deploy
```

---

### 2. Security Training

**For Developers**:
- OWASP Top 10 awareness
- Secure coding practices
- Code review guidelines
- Incident response procedures

**For Users**:
- Password security
- Phishing awareness
- Data handling policies
- Reporting security concerns

---

## Production Deployment Security

### 1. Environment Configuration

**Django Production Settings**:
```python
# settings/production.py

DEBUG = False
ALLOWED_HOSTS = ['api.medical.university.edu']

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')  # Strong, random, never in code

# Security
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/django/medical_api.log',
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 10,
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': True,
        },
    },
}
```

---

### 2. Deployment Checklist

**Pre-Deployment**:
- [ ] All tests passing
- [ ] Security scan completed
- [ ] Dependencies updated
- [ ] `DEBUG = False`
- [ ] Secret keys in environment variables
- [ ] Database backups tested
- [ ] SSL certificate valid

**Post-Deployment**:
- [ ] Verify HTTPS works
- [ ] Test authentication flow
- [ ] Check error logging
- [ ] Monitor resource usage
- [ ] Verify audit logging works
- [ ] Test backup restoration

---

## Conclusion

This security outline provides a comprehensive framework for building and maintaining a secure medical management system. Security must be:

1. **Proactive**: Built into design from day one
2. **Layered**: Multiple defensive mechanisms
3. **Monitored**: Continuous auditing and alerting
4. **Maintained**: Regular updates and testing
5. **Compliant**: Meeting regulatory requirements

**Key Takeaways**:
- Implement RBAC strictly (least privilege)
- Log all sensitive operations (audit trail)
- Encrypt data at rest and in transit
- Validate all inputs rigorously
- Immutable medical records (finalized examinations)
- Regular security testing and updates
- Incident response plan ready

**Next Steps**:
1. Implement models with security features
2. Configure authentication and RBAC
3. Set up audit logging
4. Configure production security settings
5. Conduct security testing
6. Deploy with security checklist
7. Establish monitoring and maintenance procedures

---

**Document Version**: 1.0.0  
**Last Updated**: December 26, 2025  
**Review Date**: March 26, 2026 (quarterly review)
