# Old Session Context System Removal Plan

## Overview
The old session context system (`get_current_session_context()`) has been causing issues and should be removed in favor of:
1. **Global Template Context Processor** - for template data
2. **Direct Flask session access** - for route logic
3. **Database queries** - for authoritative data

## Files to Modify

### 1. **web_app.py** - Main application file
**Current Usage**: Multiple functions use `get_current_session_context()`
**Replacement Strategy**:
- Use `session.get('platform_connection_id')` for platform ID
- Use global template context processor for template data
- Query database directly for authoritative platform data

### 2. **session_error_handlers.py** - Error handling middleware
**Current Usage**: Platform context validation
**Replacement Strategy**:
- Already partially fixed (removed caption_generation)
- Replace remaining usage with direct session access

### 3. **session_middleware_v2.py** - Session middleware
**Current Usage**: Provides the old session context functions
**Replacement Strategy**:
- Keep Redis session management
- Remove `get_current_session_context()` function
- Keep direct session access functions

### 4. **Other files** - Various utilities and tests
**Current Usage**: Testing and debugging
**Replacement Strategy**:
- Update tests to use new approach
- Remove debug utilities that depend on old system

## Replacement Patterns

### Pattern 1: Platform ID Access
**Old:**
```python
context = get_current_session_context()
platform_id = context.get('platform_connection_id') if context else None
```

**New:**
```python
platform_id = session.get('platform_connection_id')
```

### Pattern 2: Platform Object Access
**Old:**
```python
context = get_current_session_context()
if context and context.get('platform_connection_id'):
    # Use platform
```

**New:**
```python
platform_id = session.get('platform_connection_id')
if platform_id:
    # Query database for platform object if needed
    platform = db_session.query(PlatformConnection).filter_by(id=platform_id).first()
```

### Pattern 3: Template Context (Already Working)
**Current:**
```python
# Global template context processor already provides:
# - current_platform
# - user_platforms
# No changes needed for templates
```

## Implementation Steps

### Phase 1: Replace web_app.py usage
1. Update `platform_required` decorator
2. Update route functions that check platform context
3. Test each change individually

### Phase 2: Update error handlers
1. Replace session context usage in error handlers
2. Test error handling scenarios

### Phase 3: Clean up middleware
1. Remove unused functions from session_middleware_v2.py
2. Update imports across the project

### Phase 4: Remove dead code
1. Remove unused imports
2. Remove debug utilities
3. Update tests

## Benefits of Removal

1. **Simplified Architecture**: Fewer layers of abstraction
2. **Better Performance**: Direct session access is faster
3. **Fewer Bugs**: Less complex session synchronization
4. **Easier Debugging**: Clear data flow
5. **Maintainability**: Less code to maintain

## Risks and Mitigation

### Risk 1: Breaking existing functionality
**Mitigation**: Test each change thoroughly, replace one function at a time

### Risk 2: Template context issues
**Mitigation**: Global template context processor already works, no changes needed

### Risk 3: Session data inconsistency
**Mitigation**: Use Flask session as single source of truth, backed by Redis

## Testing Strategy

1. **Unit Tests**: Test each replaced function individually
2. **Integration Tests**: Test complete user workflows
3. **Manual Testing**: Test all major features
4. **Regression Testing**: Ensure no existing functionality breaks
