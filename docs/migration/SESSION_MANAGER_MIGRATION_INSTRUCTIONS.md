# Session Manager Migration Instructions

## Overview 

This document provides step-by-step instructions to deprecate the legacy `session_manager.py` and migrate all remaining code to use the new `unified_session_manager.py`. This migration aligns with the session consolidation requirements in `.kiro/specs/session-consolidation/` and ensures a single, consistent session management approach.

## Migration Goals

1. **Eliminate Legacy Dependencies**: Remove all imports and usage of legacy `SessionManager`
2. **Standardize on UnifiedSessionManager**: Use `UnifiedSessionManager` as the single session management interface
3. **Migrate Platform Context Functions**: Ensure `get_current_platform_context` works with unified system
4. **Update Health Monitoring**: Migrate health checking to use unified session manager
5. **Update Test Suite**: Migrate all tests to use unified session manager
6. **Update Documentation**: Update steering documents and technical documentation

## Pre-Migration Checklist

- [ ] Backup current codebase
- [ ] Ensure all tests pass with current system
- [ ] Verify unified_session_manager.py is fully functional
- [ ] Review session consolidation specifications in `.kiro/specs/session-consolidation/`

## Migration Steps

### Phase 1: Core Infrastructure Migration

#### Step 1.1: Enhance UnifiedSessionManager with Missing Functions

Create missing platform context functions in `unified_session_manager.py`:

```python
# Add to unified_session_manager.py

def get_current_platform_context() -> Optional[Dict[str, Any]]:
    """
    Get the current platform context from Flask's g object with fallback
    
    Returns:
        Platform context dictionary or None
    """
    from flask import g
    
    # First try to get from g object (set by middleware)
    context = getattr(g, 'platform_context', None)
    if context:
        return context
    
    # Fallback: get from session cookie
    try:
        from flask import request
        from session_cookie_manager import get_session_cookie_manager
        
        cookie_manager = get_session_cookie_manager()
        session_id = cookie_manager.get_session_id_from_request(request)
        
        if session_id:
            # Get unified session manager from app context
            from flask import current_app
            unified_session_manager = getattr(current_app, 'unified_session_manager', None)
            if unified_session_manager:
                return unified_session_manager.get_session_context(session_id)
    except Exception as e:
        logger.debug(f"Error in platform context fallback: {e}")
    
    return None


def get_current_platform() -> Optional['PlatformConnection']:
    """
    Get the current platform connection from context using fresh database query
    
    Returns:
        PlatformConnection object or None
    """
    context = get_current_platform_context()
    if context and context.get('platform_connection_id'):
        from flask import current_app
        from models import PlatformConnection
        
        # Get db_manager from app context
        db_manager = getattr(current_app, 'config', {}).get('db_manager')
        if not db_manager:
            return None
            
        with db_manager.get_session() as db_session:
            return db_session.query(PlatformConnection).filter_by(
                id=context['platform_connection_id'],
                is_active=True
            ).first()
    return None


def get_current_user_from_context() -> Optional['User']:
    """
    Get the current user from platform context using fresh database query
    
    Returns:
        User object or None
    """
    context = get_current_platform_context()
    if context and context.get('user_id'):
        from flask import current_app
        from models import User
        
        # Get db_manager from app context
        db_manager = getattr(current_app, 'config', {}).get('db_manager')
        if not db_manager:
            return None
            
        with db_manager.get_session() as db_session:
            return db_session.query(User).filter_by(
                id=context['user_id'],
                is_active=True
            ).first()
    return None


def switch_platform_context(platform_connection_id: int) -> bool:
    """
    Switch the current session's platform context
    
    Args:
        platform_connection_id: ID of platform to switch to
        
    Returns:
        True if successful, False otherwise
    """
    context = get_current_platform_context()
    if not context:
        return False
    
    from flask import current_app
    unified_session_manager = getattr(current_app, 'unified_session_manager', None)
    if not unified_session_manager:
        return False
    
    return unified_session_manager.update_platform_context(
        context['session_id'], 
        platform_connection_id
    )
```

#### Step 1.2: Create Compatibility Module

Create `session_manager_compat.py` to provide backward compatibility:

```python
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Session Manager Compatibility Layer

This module provides backward compatibility for legacy session_manager imports
while redirecting to the unified session management system.

DEPRECATED: This module is for migration purposes only. Use unified_session_manager directly.
"""

import warnings
from unified_session_manager import (
    UnifiedSessionManager,
    get_current_platform_context,
    get_current_platform,
    get_current_user_from_context,
    switch_platform_context
)

# Issue deprecation warning
warnings.warn(
    "session_manager is deprecated. Use unified_session_manager instead.",
    DeprecationWarning,
    stacklevel=2
)

# Provide compatibility aliases
SessionManager = UnifiedSessionManager

# Re-export functions
__all__ = [
    'SessionManager',
    'get_current_platform_context',
    'get_current_platform',
    'get_current_user_from_context',
    'switch_platform_context'
]
```

### Phase 2: Core Application Migration

#### Step 2.1: Update web_app.py

Replace legacy session manager usage in `web_app.py`:

```python
# BEFORE (lines 33, 265, 302, 311):
from app.core.session.core.session_manager import SessionManager, get_current_platform_context
session_manager = SessionManager(db_manager)
session_health_checker = get_session_health_checker(db_manager, session_manager)
app.config['session_manager'] = session_manager

# AFTER:
from unified_session_manager import get_current_platform_context
# Remove session_manager creation - use unified_session_manager only
session_health_checker = get_session_health_checker(db_manager, unified_session_manager)
app.config['session_manager'] = unified_session_manager  # For backward compatibility
```

#### Step 2.2: Update Health Monitoring

Update `session_health_checker.py`:

```python
# BEFORE:
from app.core.session.core.session_manager import SessionManager

class SessionHealthChecker:
    def __init__(self, db_manager: DatabaseManager, session_manager: SessionManager):

# AFTER:
from unified_session_manager import UnifiedSessionManager

class SessionHealthChecker:
    def __init__(self, db_manager: DatabaseManager, session_manager: UnifiedSessionManager):
```

Update the factory function:

```python
# BEFORE:
def get_session_health_checker(db_manager: DatabaseManager, session_manager: SessionManager) -> SessionHealthChecker:

# AFTER:
def get_session_health_checker(db_manager: DatabaseManager, session_manager: UnifiedSessionManager) -> SessionHealthChecker:
```

### Phase 3: Security and Utility Migration

#### Step 3.1: Update Security Features

Update `security/features/caption_security.py`:

```python
# BEFORE:
from session_manager import get_current_platform_context

# AFTER:
from unified_session_manager import get_current_platform_context
```

#### Step 3.2: Update Platform Context Utils

Update `platform_context_utils.py`:

```python
# BEFORE:
from unified_session_manager import UnifiedSessionManager
unified_session_manager = UnifiedSessionManager(db_manager)

# AFTER:
from flask import current_app
unified_session_manager = current_app.unified_session_manager
```

### Phase 4: Test Suite Migration

#### Step 4.1: Create Test Migration Script

Create `scripts/testing/migrate_session_tests.py`:

```python
#!/usr/bin/env python3
"""
Script to migrate test files from legacy session_manager to unified_session_manager
"""

import os
import re
import glob
from pathlib import Path

def migrate_test_file(file_path):
    """Migrate a single test file"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Track changes
    changes_made = False
    
    # Replace imports
    old_imports = [
        r'from app.core.session.core.session_manager import SessionManager',
        r'from session_manager import get_current_platform_context',
        r'from session_manager import .*',
        r'import session_manager'
    ]
    
    new_imports = [
        'from unified_session_manager import UnifiedSessionManager as SessionManager',
        'from unified_session_manager import get_current_platform_context',
        'from unified_session_manager import *',
        'import unified_session_manager as session_manager'
    ]
    
    for old, new in zip(old_imports, new_imports):
        if re.search(old, content):
            content = re.sub(old, new, content)
            changes_made = True
    
    # Replace class references
    content = re.sub(r'\bSessionManager\b', 'UnifiedSessionManager', content)
    
    if changes_made:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Migrated: {file_path}")
        return True
    
    return False

def main():
    """Migrate all test files"""
    test_files = glob.glob('tests/**/*.py', recursive=True)
    script_files = glob.glob('scripts/**/*.py', recursive=True)
    
    all_files = test_files + script_files
    migrated_count = 0
    
    for file_path in all_files:
        if migrate_test_file(file_path):
            migrated_count += 1
    
    print(f"Migration complete. {migrated_count} files updated.")

if __name__ == '__main__':
    main()
```

#### Step 4.2: Run Test Migration

```bash
# Run the migration script
python scripts/testing/migrate_session_tests.py

# Verify tests still pass
python -m unittest discover tests -v
```

### Phase 5: Documentation Updates

#### Step 5.1: Update Steering Documents

Update `.kiro/steering/tech.md`:

```markdown
# BEFORE:
### Session Management Components
- **UserSession Model**: Database table for session storage
- **SessionManager**: Core session operations (create, validate, cleanup)
- **RequestSessionManager**: Request-scoped session handling

# AFTER:
### Session Management Components
- **UserSession Model**: Database table for session storage
- **UnifiedSessionManager**: Single session management system (create, validate, cleanup, platform context)
- **RequestSessionManager**: Request-scoped session handling
- **Session Middleware**: Automatic session validation and cleanup

### Session Management Architecture

**IMPORTANT**: This application uses **database sessions** exclusively with a **unified session manager** for all session operations.

### Unified Session Implementation
- **Primary Manager**: UnifiedSessionManager handles all session operations
- **Single Source of Truth**: All session data stored in UserSession database table
- **Platform Context**: Integrated platform switching and context management
- **Security**: Built-in session validation, fingerprinting, and audit logging
- **Performance**: Optimized database queries and connection pooling
```

#### Step 5.2: Update Testing Guidelines

Update `.kiro/steering/testing-guidelines.md`:

```markdown
# Add to Session Testing section:

**Unified Session Testing:**
For session-related tests, always use the unified session manager:

```python
# Test unified session functionality
from unified_session_manager import UnifiedSessionManager

class TestUnifiedSessions(unittest.TestCase):
    def setUp(self):
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.session_manager = UnifiedSessionManager(self.db_manager)
    
    def test_session_creation(self):
        # Test unified session creation
        session_id = self.session_manager.create_session(user_id=1)
        self.assertIsNotNone(session_id)
        
        # Test session context retrieval
        context = self.session_manager.get_session_context(session_id)
        self.assertEqual(context['user_id'], 1)
```

**Migration Note:** Legacy `SessionManager` has been deprecated in favor of `UnifiedSessionManager`. All new tests should use the unified system.
```

### Phase 6: Cleanup and Validation

#### Step 6.1: Remove Legacy Files

After successful migration and testing:

```bash
# Create backup
cp session_manager.py session_manager.py.backup

# Remove legacy file (after confirming all tests pass)
# rm session_manager.py

# Keep compatibility layer temporarily
# mv session_manager_compat.py session_manager.py
```

#### Step 6.2: Update Import Statements

Create `scripts/maintenance/update_session_imports.py`:

```python
#!/usr/bin/env python3
"""
Script to update all remaining session_manager imports to unified_session_manager
"""

import os
import re
import glob

def update_imports_in_file(file_path):
    """Update imports in a single file"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        original_content = content
        
        # Update import statements
        patterns = [
            (r'from session_manager import', 'from unified_session_manager import'),
            (r'import session_manager', 'import unified_session_manager as session_manager'),
        ]
        
        for old_pattern, new_pattern in patterns:
            content = re.sub(old_pattern, new_pattern, content)
        
        if content != original_content:
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"Updated: {file_path}")
            return True
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    
    return False

def main():
    """Update all Python files"""
    # Find all Python files except the ones we're migrating
    python_files = []
    for pattern in ['*.py', '**/*.py']:
        python_files.extend(glob.glob(pattern, recursive=True))
    
    # Exclude certain files
    exclude_patterns = [
        'session_manager.py',
        'unified_session_manager.py',
        'session_manager_compat.py',
        '__pycache__',
        '.git',
        'venv',
        'env'
    ]
    
    filtered_files = []
    for file_path in python_files:
        if not any(exclude in file_path for exclude in exclude_patterns):
            filtered_files.append(file_path)
    
    updated_count = 0
    for file_path in filtered_files:
        if update_imports_in_file(file_path):
            updated_count += 1
    
    print(f"Import update complete. {updated_count} files updated.")

if __name__ == '__main__':
    main()
```

#### Step 6.3: Validation Testing

Create comprehensive validation script `scripts/testing/validate_session_migration.py`:

```python
#!/usr/bin/env python3
"""
Comprehensive validation script for session manager migration
"""

import unittest
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

class SessionMigrationValidation(unittest.TestCase):
    """Validate session manager migration"""
    
    def setUp(self):
        from config import Config
        from app.core.database.core.database_manager import DatabaseManager
        from unified_session_manager import UnifiedSessionManager
        
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.session_manager = UnifiedSessionManager(self.db_manager)
    
    def test_unified_session_manager_import(self):
        """Test that UnifiedSessionManager can be imported and instantiated"""
        from unified_session_manager import UnifiedSessionManager
        manager = UnifiedSessionManager(self.db_manager)
        self.assertIsNotNone(manager)
    
    def test_platform_context_functions(self):
        """Test that platform context functions are available"""
        from unified_session_manager import (
            get_current_platform_context,
            get_current_platform,
            get_current_user_from_context,
            switch_platform_context
        )
        
        # Functions should be callable
        self.assertTrue(callable(get_current_platform_context))
        self.assertTrue(callable(get_current_platform))
        self.assertTrue(callable(get_current_user_from_context))
        self.assertTrue(callable(switch_platform_context))
    
    def test_session_operations(self):
        """Test basic session operations"""
        # This would require a test user - adapt based on your test setup
        pass
    
    def test_no_legacy_imports(self):
        """Test that no files import legacy session_manager directly"""
        import glob
        
        python_files = glob.glob('**/*.py', recursive=True)
        legacy_imports = []
        
        for file_path in python_files:
            if 'session_manager.py' in file_path or '__pycache__' in file_path:
                continue
                
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    
                if 'from session_manager import' in content and 'unified_session_manager' not in content:
                    legacy_imports.append(file_path)
            except Exception:
                continue
        
        if legacy_imports:
            self.fail(f"Files still importing legacy session_manager: {legacy_imports}")

def main():
    """Run validation tests"""
    unittest.main(verbosity=2)

if __name__ == '__main__':
    main()
```

## Migration Execution Plan

### Week 1: Preparation and Core Migration
- [ ] **Day 1-2**: Enhance UnifiedSessionManager with missing functions
- [ ] **Day 3**: Create compatibility layer and update web_app.py
- [ ] **Day 4**: Update health monitoring system
- [ ] **Day 5**: Test core functionality and fix issues

### Week 2: Security and Utilities Migration
- [ ] **Day 1**: Update security features and platform context utils
- [ ] **Day 2**: Create and run test migration script
- [ ] **Day 3**: Fix failing tests and update test helpers
- [ ] **Day 4**: Update documentation and steering documents
- [ ] **Day 5**: Comprehensive testing and validation

### Week 3: Cleanup and Finalization
- [ ] **Day 1**: Run import update script across codebase
- [ ] **Day 2**: Remove legacy files and clean up compatibility layer
- [ ] **Day 3**: Final validation testing
- [ ] **Day 4**: Performance testing and optimization
- [ ] **Day 5**: Documentation review and deployment preparation

## Rollback Plan

If issues arise during migration:

1. **Immediate Rollback**: Restore `session_manager.py` from backup
2. **Revert Changes**: Use git to revert specific commits
3. **Compatibility Layer**: Keep `session_manager_compat.py` as permanent bridge
4. **Gradual Migration**: Migrate components one at a time instead of all at once

## Success Criteria

- [ ] All tests pass with unified session manager
- [ ] No legacy session_manager imports remain
- [ ] Platform context functions work correctly
- [ ] Health monitoring uses unified system
- [ ] Documentation is updated
- [ ] Performance is maintained or improved
- [ ] Security features continue to work

## Post-Migration Tasks

1. **Monitor Performance**: Track session operation performance for 1 week
2. **Update CI/CD**: Ensure build and deployment processes work
3. **Team Training**: Brief team on new unified session management
4. **Documentation Review**: Ensure all docs reflect new architecture
5. **Security Audit**: Verify security features work with unified system

## Support and Troubleshooting

### Common Issues

1. **Import Errors**: Use compatibility layer temporarily
2. **Test Failures**: Update test mocks and fixtures
3. **Performance Issues**: Check database connection pooling
4. **Context Errors**: Verify Flask app context in platform functions

### Getting Help

- Review session consolidation specs in `.kiro/specs/session-consolidation/`
- Check existing unified_session_manager tests for examples
- Use validation script to identify remaining issues
- Consult steering documents for architecture guidance

This migration will result in a cleaner, more maintainable codebase with a single, robust session management system that aligns with the project's architectural goals.
