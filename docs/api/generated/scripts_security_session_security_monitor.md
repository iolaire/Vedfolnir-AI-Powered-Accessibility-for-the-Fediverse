# scripts.security.session_security_monitor

Session Security Monitor CLI

Command-line utility for monitoring and managing session security.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/scripts/security/session_security_monitor.py`

## Functions

### setup_database

```python
def setup_database()
```

Set up database connection

### get_security_status

```python
def get_security_status(session_manager)
```

Get overall security status

### list_session_metrics

```python
def list_session_metrics(session_manager, session_id)
```

List session security metrics

### cleanup_expired_data

```python
def cleanup_expired_data(session_manager, max_age_hours)
```

Clean up expired security data

### validate_session_security

```python
def validate_session_security(session_manager, session_id, user_id)
```

Validate security for a specific session

### invalidate_suspicious_sessions

```python
def invalidate_suspicious_sessions(session_manager, user_id, reason)
```

Invalidate all sessions for a user due to suspicious activity

### show_suspicious_activity

```python
def show_suspicious_activity(session_manager)
```

Show sessions with suspicious activity

### main

```python
def main()
```

Main CLI function

