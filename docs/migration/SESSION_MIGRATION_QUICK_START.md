# Session Manager Migration - Quick Start Guide

## Overview

This guide provides the essential steps to migrate from the legacy `session_manager.py` to the new `unified_session_manager.py` system.

## Quick Migration Steps

### 1. Run Migration Scripts

```bash
# Step 1: Migrate test files (dry run first)
python scripts/testing/migrate_session_tests.py --dry-run
python scripts/testing/migrate_session_tests.py

# Step 2: Update all import statements (dry run first)  
python scripts/maintenance/update_session_imports.py --dry-run
python scripts/maintenance/update_session_imports.py

# Step 3: Validate migration
python scripts/testing/validate_session_migration.py
```

### 2. Manual Updates Required

Update these key files manually:

#### web_app.py
```python
# BEFORE
from app.core.session.core.session_manager import SessionManager, get_current_platform_context
session_manager = SessionManager(db_manager)

# AFTER  
from app.core.session.manager import get_current_platform_context
# Remove session_manager creation - use unified_session_manager only
```

#### session_health_checker.py
```python
# BEFORE
from app.core.session.core.session_manager import SessionManager
def get_session_health_checker(db_manager: DatabaseManager, session_manager: SessionManager):

# AFTER
from app.core.session.manager import UnifiedSessionManager  
def get_session_health_checker(db_manager: DatabaseManager, session_manager: UnifiedSessionManager):
```

### 3. Add Missing Functions to UnifiedSessionManager

Add these functions to `unified_session_manager.py`:

```python
def get_current_platform_context() -> Optional[Dict[str, Any]]:
    """Get current platform context from Flask g object with fallback"""
    # Implementation provided in SESSION_MANAGER_MIGRATION_INSTRUCTIONS.md

def get_current_platform() -> Optional['PlatformConnection']:
    """Get current platform connection from context"""
    # Implementation provided in SESSION_MANAGER_MIGRATION_INSTRUCTIONS.md

def get_current_user_from_context() -> Optional['User']:
    """Get current user from platform context"""
    # Implementation provided in SESSION_MANAGER_MIGRATION_INSTRUCTIONS.md

def switch_platform_context(platform_connection_id: int) -> bool:
    """Switch current session's platform context"""
    # Implementation provided in SESSION_MANAGER_MIGRATION_INSTRUCTIONS.md
```

### 4. Test Migration

```bash
# Run tests to verify migration
python -m unittest discover tests -v

# Run specific session tests
python -m unittest tests.test_session_management -v
python -m unittest tests.test_unified_session_manager -v
```

### 5. Clean Up (After Successful Testing)

```bash
# Backup original file
cp session_manager.py session_manager.py.backup

# Replace with compatibility layer (temporary)
mv session_manager_compat.py session_manager.py

# Eventually remove legacy file entirely
# rm session_manager.py.backup
```

## Key Changes

### Import Changes
```python
# OLD
from app.core.session.core.session_manager import SessionManager, get_current_platform_context

# NEW  
from app.core.session.manager import UnifiedSessionManager, get_current_platform_context
```

### Class Changes
```python
# OLD
session_manager = SessionManager(db_manager)

# NEW
session_manager = UnifiedSessionManager(db_manager)
```

### Method Changes
Most methods remain the same:
- `create_session()` ✅ Same interface
- `get_session_context()` ✅ Same interface
- `validate_session()` ✅ Same interface  
- `destroy_session()` ✅ Same interface
- `cleanup_user_sessions()` ✅ Same interface

## Files That Need Updates

### Core Files (High Priority)
- [x] `web_app.py` - Remove legacy SessionManager creation
- [x] `session_health_checker.py` - Update type hints and imports
- [x] `security/features/caption_security.py` - Update import
- [x] `platform_context_utils.py` - Use app context instead of creating new instance

### Test Files (29 files)
- Run `scripts/testing/migrate_session_tests.py` to update automatically

### Documentation
- [x] `.kiro/steering/tech.md` - Updated to reflect unified system
- [x] `.kiro/steering/testing-guidelines.md` - Added unified session testing section

## Validation Checklist

- [ ] All imports updated to `unified_session_manager`
- [ ] No legacy `SessionManager` instantiation in core files
- [ ] Platform context functions work correctly
- [ ] All tests pass
- [ ] Health monitoring uses unified system
- [ ] Documentation reflects new architecture
- [ ] Performance maintained or improved

## Rollback Plan

If issues occur:
1. Restore `session_manager.py` from backup
2. Revert import changes: `git checkout -- <files>`
3. Keep compatibility layer as permanent bridge
4. Migrate components gradually instead of all at once

## Support

- **Full Instructions**: `SESSION_MANAGER_MIGRATION_INSTRUCTIONS.md`
- **Validation Script**: `scripts/testing/validate_session_migration.py`
- **Migration Scripts**: `scripts/testing/migrate_session_tests.py`
- **Steering Docs**: `.kiro/steering/tech.md` and `.kiro/steering/testing-guidelines.md`

## Success Criteria

✅ All tests pass with unified session manager  
✅ No legacy session_manager imports remain  
✅ Platform context functions work correctly  
✅ Health monitoring uses unified system  
✅ Documentation is updated  
✅ Performance is maintained or improved  
✅ Security features continue to work  

The migration ensures a single, robust session management system that aligns with the project's architectural goals and eliminates the complexity of dual session systems.
