# Test Organization Guidelines

## Core Rule
**All test files MUST be in `tests/` directory. NO test files in project root.**

## Directory Structure
```
tests/
├── admin/                    # Admin functionality tests
├── frontend/                 # Frontend/UI tests (Python-based)
├── integration/              # Integration tests
├── performance/              # Performance tests
├── playwright/               # Browser automation (ALL Playwright files)
├── security/                 # Security tests
├── unit/                     # Unit tests
├── scripts/                  # Test utilities
└── test_helpers/             # Reusable test utilities
```

## File Placement Rules

### By Category
- **Admin**: `tests/admin/test_*.py`
- **Security**: `tests/security/test_*.py`
- **Unit**: `tests/unit/test_*.py`
- **Integration**: `tests/integration/test_*.py`
- **Performance**: `tests/performance/test_*.py`

### Playwright Files (ALL in `tests/playwright/`)
```
tests/playwright/
├── MMdd_HH_mm_test_*.js          # Test files with timestamp
├── MMdd_HH_mm_playwright.config.js # Config with timestamp
├── MMdd_HH_mm_README.md          # Docs with timestamp
├── fixtures/                     # Test data
├── page_objects/                 # Page objects
└── utils/                        # Utilities
```

**MANDATORY**: All Playwright files need timestamp prefix `MMdd_HH_mm_`

## Naming Conventions
- **Test Files**: `test_<functionality>.py`
- **Test Classes**: `Test<Functionality>`
- **Test Methods**: `test_<specific_behavior>`
- **Playwright**: `MMdd_HH_mm_test_<functionality>.js`

## Import Path Management
```python
import sys
import os

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Now import project modules
from config import Config
```

## Playwright Requirements

### Configuration (MANDATORY)
```javascript
// MMdd_HH_mm_playwright.config.js
module.exports = {
  use: {
    headless: false,  // REQUIRED for debugging
  }
};
```

### Security Considerations
- **No `page.evaluate()`** for localStorage/sessionStorage (causes SecurityError)
- **Use `domcontentloaded`** not `networkidle` (WebSocket timeout issues)
- **Always cleanup** with `ensureLoggedOut()`

## Enforcement Rules
1. Always ask: "What type of test is this?"
2. Place in appropriate `tests/` subdirectory
3. Never create test files in project root
4. Use proper naming conventions
5. Include copyright headers (Python files)
6. For Playwright: ALL files in `tests/playwright/` with timestamps
7. For Playwright config: Always set `headless: false`

## Migration Example
```bash
# CORRECT - Preserves git history
git mv test_pause_system.py tests/admin/test_pause_system.py

# WRONG - Loses git history
mv test_pause_system.py tests/admin/
```

## Benefits
- Clean project structure
- Better maintainability
- Improved test discovery
- Team collaboration
- Scalability
