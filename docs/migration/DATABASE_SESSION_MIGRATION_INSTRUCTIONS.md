# Database Session Migration Instructions

## Overview

This document provides instructions to migrate direct `db_manager.get_session()` usage to use the `unified_session_manager` or appropriate session management patterns. This ensures consistent session handling, better error management, and proper integration with the unified session architecture.

## Current State Analysis

### Direct db_manager.get_session() Usage Found:

**Root Directory (`/`):**
- `web_app.py`: 21 instances
- `session_performance_optimizer.py`: 8 instances

**Admin Directory (`/admin`):**
- `admin/routes/dashboard.py`: 1 instance
- `admin/routes/user_management.py`: 2 instances  
- `admin/routes/system_health.py`: 1 instance
- `admin/services/cleanup_service.py`: 1 instance
- `admin/services/user_service.py`: 11 instances
- `admin/services/monitoring_service.py`: 7 instances

**Total**: ~52 instances requiring migration

## Migration Strategy

### 1. **Session-Aware Operations** → Use `unified_session_manager.get_db_session()`
For operations that need session context or user authentication.

### 2. **Simple Database Queries** → Use `request_session_manager.session_scope()`
For straightforward database operations within request context.

### 3. **Service Layer Operations** → Use appropriate service pattern
For admin services and background operations.

## Migration Patterns

### Pattern 1: Session-Aware Web Routes

**BEFORE:**
```python
@app.route('/some_route')
@login_required
def some_function():
    session = db_manager.get_session()
    try:
        # Database operations
        result = session.query(Model).filter_by(user_id=current_user.id).all()
        return render_template('template.html', data=result)
    finally:
        session.close()
```

**AFTER:**
```python
@app.route('/some_route')
@login_required
def some_function():
    with unified_session_manager.get_db_session() as session:
        # Database operations with automatic session management
        result = session.query(Model).filter_by(user_id=current_user.id).all()
        return render_template('template.html', data=result)
```

### Pattern 2: Request-Scoped Operations

**BEFORE:**
```python
def some_function():
    session = db_manager.get_session()
    try:
        # Simple database query
        result = session.query(Model).all()
        return result
    finally:
        session.close()
```

**AFTER:**
```python
def some_function():
    with request_session_manager.session_scope() as session:
        # Simple database query with proper scope management
        result = session.query(Model).all()
        return result
```

### Pattern 3: Service Layer Operations

**BEFORE:**
```python
class SomeService:
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def get_data(self):
        session = self.db_manager.get_session()
        try:
            return session.query(Model).all()
        finally:
            session.close()
```

**AFTER:**
```python
class SomeService:
    def __init__(self, db_manager, session_manager=None):
        self.db_manager = db_manager
        self.session_manager = session_manager or self._get_unified_session_manager()
    
    def _get_unified_session_manager(self):
        from flask import current_app
        return getattr(current_app, 'unified_session_manager', None)
    
    def get_data(self):
        if self.session_manager:
            with self.session_manager.get_db_session() as session:
                return session.query(Model).all()
        else:
            # Fallback for non-Flask contexts
            session = self.db_manager.get_session()
            try:
                return session.query(Model).all()
            finally:
                session.close()
```

## Migration Implementation Plan

### Phase 1: Web Application Routes (High Priority)

#### Files to Update:
- `web_app.py` (21 instances)

#### Key Functions:
1. `platform_management()` (line 1720)
2. `post_approved_captions()` (line 1543)
3. `dashboard()` (line 932)
4. `images()` (line 1103)
5. `review_captions()` (line 1285)

### Phase 2: Admin Services (Medium Priority)

#### Files to Update:
- `admin/services/user_service.py` (11 instances)
- `admin/services/monitoring_service.py` (7 instances)
- `admin/services/cleanup_service.py` (1 instance)

### Phase 3: Admin Routes (Medium Priority)

#### Files to Update:
- `admin/routes/dashboard.py` (1 instance)
- `admin/routes/user_management.py` (2 instances)
- `admin/routes/system_health.py` (1 instance)

### Phase 4: Performance Optimization (Low Priority)

#### Files to Update:
- `session_performance_optimizer.py` (8 instances)

## Detailed Migration Steps

### Step 1: Update Web Application Routes

#### 1.1: Platform Management Function
```python
# BEFORE (line 1720)
def platform_management():
    session = db_manager.get_session()
    try:
        # ... operations
    finally:
        session.close()

# AFTER
def platform_management():
    with unified_session_manager.get_db_session() as session:
        # ... operations (automatic cleanup)
```

#### 1.2: Session-Aware Routes
For routes that need user context, use `unified_session_manager.get_db_session()`:

```python
# Add import at top of web_app.py
# (Already exists from previous migration)

# Update each function pattern:
@app.route('/some_route')
@login_required
def some_route():
    with unified_session_manager.get_db_session() as session:
        # Database operations
        pass
```

### Step 2: Update Admin Services

#### 2.1: User Service Migration
```python
# admin/services/user_service.py

class UserService:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        # Add unified session manager reference
        self._unified_session_manager = None
    
    @property
    def unified_session_manager(self):
        if self._unified_session_manager is None:
            try:
                from flask import current_app
                self._unified_session_manager = getattr(current_app, 'unified_session_manager', None)
            except RuntimeError:
                # Outside Flask context
                pass
        return self._unified_session_manager
    
    def get_all_users(self):
        # BEFORE
        # session = self.db_manager.get_session()
        # try:
        #     return session.query(User).all()
        # finally:
        #     session.close()
        
        # AFTER
        if self.unified_session_manager:
            with self.unified_session_manager.get_db_session() as session:
                return session.query(User).all()
        else:
            # Fallback for non-Flask contexts
            session = self.db_manager.get_session()
            try:
                return session.query(User).all()
            finally:
                session.close()
```

### Step 3: Update Admin Routes

#### 3.1: Admin Dashboard
```python
# admin/routes/dashboard.py

@admin_bp.route('/dashboard')
@login_required
@require_admin
def admin_dashboard():
    # BEFORE
    # session = db_manager.get_session()
    # try:
    #     # ... operations
    # finally:
    #     session.close()
    
    # AFTER
    from flask import current_app
    unified_session_manager = current_app.unified_session_manager
    
    with unified_session_manager.get_db_session() as session:
        # ... operations
        pass
```

## Migration Scripts

### Script 1: Automated Pattern Detection and Replacement

Create `scripts/maintenance/migrate_db_sessions.py`:

```python
#!/usr/bin/env python3
"""
Script to migrate db_manager.get_session() usage to unified patterns
"""

import os
import re
import glob
import argparse

def migrate_web_app_routes(file_path, dry_run=False):
    """Migrate web app routes to use unified_session_manager"""
    # Implementation details...
    pass

def migrate_admin_services(file_path, dry_run=False):
    """Migrate admin services to use appropriate session patterns"""
    # Implementation details...
    pass

def main():
    # Script implementation...
    pass

if __name__ == '__main__':
    main()
```

### Script 2: Validation Script

Create `scripts/testing/validate_db_session_migration.py`:

```python
#!/usr/bin/env python3
"""
Validate database session migration
"""

import unittest
import glob
import re

class DatabaseSessionMigrationValidation(unittest.TestCase):
    def test_no_direct_db_manager_usage_in_routes(self):
        """Test that web routes don't use db_manager.get_session() directly"""
        # Implementation...
        pass
    
    def test_admin_services_use_proper_patterns(self):
        """Test that admin services use appropriate session patterns"""
        # Implementation...
        pass

if __name__ == '__main__':
    unittest.main()
```

## Benefits of Migration

### 1. **Consistent Session Management**
- All database operations use unified session handling
- Proper error handling and cleanup
- Session context awareness

### 2. **Better Error Handling**
- Automatic rollback on exceptions
- Proper connection cleanup
- Comprehensive error logging

### 3. **Performance Improvements**
- Connection pooling optimization
- Reduced connection leaks
- Better resource management

### 4. **Security Enhancements**
- Session validation and audit trails
- User context awareness
- Platform context integration

### 5. **Maintainability**
- Single session management pattern
- Easier debugging and monitoring
- Consistent code patterns

## Testing Strategy

### 1. **Unit Tests**
- Test each migrated function individually
- Verify session cleanup and error handling
- Test both success and failure scenarios

### 2. **Integration Tests**
- Test complete request flows
- Verify session context propagation
- Test admin functionality

### 3. **Performance Tests**
- Compare before/after performance
- Monitor connection pool usage
- Test under load conditions

## Rollback Plan

### 1. **Immediate Rollback**
- Keep backup copies of original files
- Use git to revert specific changes
- Test rollback in staging environment

### 2. **Gradual Migration**
- Migrate one file at a time
- Test each migration thoroughly
- Keep both patterns temporarily if needed

## Success Criteria

- [ ] All direct `db_manager.get_session()` usage migrated
- [ ] All tests pass with new session patterns
- [ ] No performance degradation
- [ ] Proper error handling and cleanup
- [ ] Session context awareness maintained
- [ ] Admin functionality works correctly
- [ ] Monitoring and logging functional

## Next Steps

1. **Phase 1**: Migrate web application routes
2. **Phase 2**: Migrate admin services  
3. **Phase 3**: Migrate admin routes
4. **Phase 4**: Migrate performance optimization code
5. **Validation**: Run comprehensive tests
6. **Documentation**: Update steering documents
7. **Monitoring**: Monitor performance and errors

This migration will result in a fully unified session management system with consistent patterns, better error handling, and improved maintainability.
