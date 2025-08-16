# Design Document

## Overview

This design document outlines the complete rewrite of the Vedfolnir user management system, replacing the current error-prone implementation with a robust, secure, and GDPR-compliant system. The new architecture will integrate seamlessly with the existing database session management system while providing comprehensive role-based access control, email verification workflows, and complete data protection compliance.

## Architecture

### High-Level Architecture

The user management system follows a layered architecture pattern:

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Interface Layer                      │
├─────────────────────────────────────────────────────────────┤
│  Registration │  Login  │  Profile  │  Admin  │  Password   │
│     Forms     │  Forms  │   Forms   │  Panel  │   Reset     │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer                            │
├─────────────────────────────────────────────────────────────┤
│  User Service │ Email   │ Auth      │ Profile │ GDPR        │
│               │ Service │ Service   │ Service │ Service     │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    Security Layer                           │
├─────────────────────────────────────────────────────────────┤
│  CSRF         │ Rate    │ Input     │ Session │ Audit       │
│  Protection   │ Limiting│ Validation│ Security│ Logging     │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                               │
├─────────────────────────────────────────────────────────────┤
│  User Model   │ Session │ Email     │ Audit   │ Platform    │
│               │ Model   │ Token     │ Trail   │ Connection  │
└─────────────────────────────────────────────────────────────┘
```

### Integration with Existing System

The new user management system integrates with existing components:

- **Database Sessions**: Uses existing `SessionManager` and `UserSession` model
- **Platform Context**: Leverages existing `PlatformConnection` relationships
- **Security Framework**: Extends existing security middleware and decorators
- **Admin Interface**: Integrates with existing admin module structure

## Components and Interfaces

### 1. Enhanced User Model

**Location**: `models.py` (modifications to existing `User` class)

**New Fields**:
```python
class User(Base):
    # Existing fields...
    
    # Email verification
    email_verified = Column(Boolean, default=False)
    email_verification_token = Column(String(255), nullable=True)
    email_verification_sent_at = Column(DateTime, nullable=True)
    
    # Profile management
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    
    # Password reset
    password_reset_token = Column(String(255), nullable=True)
    password_reset_sent_at = Column(DateTime, nullable=True)
    password_reset_used = Column(Boolean, default=False)
    
    # GDPR compliance
    data_processing_consent = Column(Boolean, default=False)
    data_processing_consent_date = Column(DateTime, nullable=True)
    
    # Account status
    account_locked = Column(Boolean, default=False)
    failed_login_attempts = Column(Integer, default=0)
    last_failed_login = Column(DateTime, nullable=True)
```

**New Methods**:
- `generate_email_verification_token()`
- `verify_email_token(token)`
- `generate_password_reset_token()`
- `verify_password_reset_token(token)`
- `can_login()` - checks email verification and account status
- `get_full_name()` - returns formatted full name
- `export_personal_data()` - GDPR data export
- `anonymize_data()` - GDPR-compliant data anonymization

### 2. Email Verification Token Model

**Location**: `models.py` (new model)

```python
class EmailVerificationToken(Base):
    __tablename__ = 'email_verification_tokens'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    token = Column(String(255), unique=True, nullable=False)
    email = Column(String(120), nullable=False)  # Email being verified
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    
    user = relationship("User", backref="verification_tokens")
```

### 3. User Service Layer

**Location**: `services/user_management_service.py` (new file)

**Core Services**:

#### UserRegistrationService
- `register_user(username, email, password, role=UserRole.VIEWER)`
- `send_verification_email(user_id)`
- `verify_email(token)`
- `resend_verification_email(user_id)`

#### UserAuthenticationService  
- `authenticate_user(username_or_email, password)`
- `login_user(user, remember=False)`
- `logout_user()`
- `check_account_status(user)`

#### UserProfileService
- `update_profile(user_id, profile_data)`
- `change_email(user_id, new_email)`
- `delete_user_profile(user_id)`
- `export_user_data(user_id)`

#### PasswordManagementService
- `initiate_password_reset(email)`
- `verify_reset_token(token)`
- `reset_password(token, new_password)`
- `change_password(user_id, current_password, new_password)`

### 4. Email Service Integration

**Location**: `services/email_service.py` (new file)

**Email Templates**:
- `email_verification.html` - Email verification template
- `password_reset.html` - Password reset template  
- `account_created.html` - Admin-created account notification
- `profile_deleted.html` - Profile deletion confirmation

**Email Service Methods**:
- `send_verification_email(user, token)`
- `send_password_reset_email(user, token)`
- `send_account_created_email(user, temporary_password)`
- `send_profile_deleted_confirmation(email)`

**Configuration**:
```python
# Email configuration from dedicated .env file
MAIL_SERVER = os.getenv('MAIL_SERVER')
MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
MAIL_USERNAME = os.getenv('MAIL_USERNAME')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')
```

### 5. Form Components

**Location**: `forms/user_management_forms.py` (new file)

**Forms**:
- `UserRegistrationForm` - User self-registration
- `LoginForm` - User authentication
- `ProfileEditForm` - Profile management
- `PasswordChangeForm` - Password changes
- `PasswordResetRequestForm` - Password reset initiation
- `PasswordResetForm` - Password reset completion
- `ProfileDeleteForm` - Profile deletion confirmation
- `AdminUserCreateForm` - Admin user creation
- `AdminUserEditForm` - Admin user editing

### 6. Route Handlers

**Location**: `routes/user_management_routes.py` (new file)

**Public Routes**:
- `GET/POST /register` - User registration
- `GET/POST /login` - User authentication  
- `GET /logout` - User logout
- `GET /verify-email/<token>` - Email verification
- `GET/POST /forgot-password` - Password reset request
- `GET/POST /reset-password/<token>` - Password reset completion

**Authenticated Routes**:
- `GET/POST /profile` - Profile management
- `GET/POST /profile/edit` - Profile editing
- `GET/POST /profile/delete` - Profile deletion
- `GET/POST /change-password` - Password changes

**Admin Routes** (extends existing admin module):
- `GET /admin/users` - User management dashboard
- `GET/POST /admin/users/create` - Create new user
- `GET/POST /admin/users/<id>/edit` - Edit user
- `POST /admin/users/<id>/delete` - Delete user
- `POST /admin/users/<id>/reset-password` - Admin password reset

### 7. Security Integration

**CSRF Protection**:
- All forms include CSRF tokens
- Integration with existing `CSRFProtect` middleware
- Custom CSRF error handling for user management routes

**Rate Limiting**:
- Login attempts: 5 per minute per IP
- Registration: 3 per hour per IP  
- Password reset: 3 per hour per email
- Email verification resend: 1 per 5 minutes per user

**Input Validation**:
- Email validation using `email_validator`
- Password strength requirements
- Username format validation
- XSS prevention for all text inputs

**Session Security**:
- Integration with existing database session management
- Secure session token generation
- Session invalidation on password changes
- Cross-tab session synchronization

## Data Models

### Enhanced User Model Schema

```sql
ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN email_verification_token VARCHAR(255);
ALTER TABLE users ADD COLUMN email_verification_sent_at DATETIME;
ALTER TABLE users ADD COLUMN first_name VARCHAR(100);
ALTER TABLE users ADD COLUMN last_name VARCHAR(100);
ALTER TABLE users ADD COLUMN password_reset_token VARCHAR(255);
ALTER TABLE users ADD COLUMN password_reset_sent_at DATETIME;
ALTER TABLE users ADD COLUMN password_reset_used BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN data_processing_consent BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN data_processing_consent_date DATETIME;
ALTER TABLE users ADD COLUMN account_locked BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN last_failed_login DATETIME;

CREATE INDEX idx_users_email_verified ON users(email_verified);
CREATE INDEX idx_users_verification_token ON users(email_verification_token);
CREATE INDEX idx_users_reset_token ON users(password_reset_token);
```

### Audit Trail Model

```sql
CREATE TABLE user_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    details TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    admin_user_id INTEGER REFERENCES users(id)
);

CREATE INDEX idx_audit_user_id ON user_audit_log(user_id);
CREATE INDEX idx_audit_action ON user_audit_log(action);
CREATE INDEX idx_audit_created_at ON user_audit_log(created_at);
```

## Error Handling

### Error Categories

1. **Validation Errors**:
   - Invalid email format
   - Weak passwords
   - Duplicate usernames/emails
   - Missing required fields

2. **Authentication Errors**:
   - Invalid credentials
   - Unverified email
   - Account locked
   - Expired tokens

3. **Authorization Errors**:
   - Insufficient permissions
   - Invalid session
   - CSRF token mismatch

4. **System Errors**:
   - Database connection failures
   - Email delivery failures
   - Token generation failures

### Error Handling Strategy

**User-Facing Errors**:
- Clear, actionable error messages
- No sensitive information disclosure
- Consistent error formatting
- Proper HTTP status codes

**System Errors**:
- Comprehensive logging
- Error recovery mechanisms
- Graceful degradation
- Admin notifications for critical errors

**Security Errors**:
- Rate limiting enforcement
- Account lockout mechanisms
- Audit trail logging
- Security event notifications

## Testing Strategy

### Unit Tests

**Model Tests**:
- User model validation
- Token generation and verification
- Password hashing and verification
- Role permission checking

**Service Tests**:
- User registration workflow
- Email verification process
- Password reset functionality
- Profile management operations

**Form Tests**:
- Form validation rules
- CSRF token handling
- Input sanitization
- Error message generation

### Integration Tests

**Authentication Flow**:
- Complete registration process
- Email verification workflow
- Login/logout functionality
- Session management integration

**Admin Functionality**:
- User creation by admin
- User management operations
- Permission enforcement
- Session preservation

**Security Tests**:
- CSRF protection
- Rate limiting enforcement
- Input validation
- Session security

### End-to-End Tests

**User Journey Tests**:
- New user registration to first login
- Password reset complete workflow
- Profile management lifecycle
- Account deletion process

**Admin Journey Tests**:
- Admin user management workflows
- Bulk user operations
- Security enforcement
- Audit trail verification

### Performance Tests

**Load Testing**:
- Concurrent user registrations
- Login performance under load
- Email sending capacity
- Database query optimization

**Security Performance**:
- Rate limiting effectiveness
- CSRF token performance
- Session lookup optimization
- Audit logging performance

## GDPR Compliance Implementation

### Data Subject Rights

**Right to Access**:
- User data export functionality
- Comprehensive data inventory
- Machine-readable format
- Secure delivery mechanism

**Right to Rectification**:
- Profile editing interface
- Email change workflow
- Data validation and verification
- Change audit logging

**Right to Erasure**:
- Complete profile deletion
- Cascading data removal
- Anonymization options
- Deletion confirmation

**Data Portability**:
- Structured data export
- Standard format compliance
- Secure transfer mechanisms
- Data integrity verification

### Privacy by Design

**Data Minimization**:
- Collect only necessary data
- Regular data cleanup
- Retention policy enforcement
- Purpose limitation

**Consent Management**:
- Clear consent mechanisms
- Granular consent options
- Consent withdrawal
- Consent audit trail

**Security Measures**:
- Data encryption at rest
- Secure data transmission
- Access control enforcement
- Regular security audits

## Migration Strategy

### Phase 1: Database Schema Updates
1. Add new columns to users table
2. Create audit log table
3. Create email verification tokens table
4. Update indexes and constraints

### Phase 2: Service Layer Implementation
1. Implement user management services
2. Create email service integration
3. Add security enhancements
4. Implement audit logging

### Phase 3: Web Interface Updates
1. Create new forms and templates
2. Update existing admin interface
3. Add new route handlers
4. Integrate with existing security middleware

### Phase 4: Testing and Validation
1. Comprehensive test suite execution
2. Security penetration testing
3. Performance validation
4. GDPR compliance verification

### Phase 5: Deployment and Monitoring
1. Production deployment
2. Monitoring setup
3. User migration assistance
4. Documentation updates

## Security Considerations

### Authentication Security
- Secure password hashing (existing bcrypt)
- Account lockout after failed attempts
- Secure token generation for resets
- Session fixation prevention

### Authorization Security  
- Role-based access control enforcement
- Platform context validation
- Admin privilege separation
- Audit trail for all actions

### Data Protection
- Input sanitization and validation
- XSS prevention
- SQL injection prevention
- Secure data storage

### Communication Security
- HTTPS enforcement
- Secure email transmission
- Token expiration management
- CSRF protection

This design provides a comprehensive foundation for implementing a secure, scalable, and GDPR-compliant user management system that integrates seamlessly with Vedfolnir's existing architecture.