# Inline CSS Prevention Guide

## Overview

This guide provides comprehensive strategies and tools to prevent the introduction of inline CSS styles in Vedfolnir templates, maintaining Content Security Policy (CSP) compliance and security best practices.

## Why Prevent Inline CSS

### Security Risks
- **CSP Violations**: Inline styles require `unsafe-inline` directive
- **XSS Vulnerabilities**: Inline styles can be injection vectors
- **Security Policy Bypass**: Circumvents security controls

### Maintenance Issues
- **Code Duplication**: Repeated styles across templates
- **Difficult Updates**: Changes require template modifications
- **Poor Organization**: Styles scattered throughout HTML

### Performance Impact
- **No Caching**: Inline styles can't be cached separately
- **Larger HTML**: Increases page size and load time
- **Render Blocking**: Inline styles block rendering

## Prevention Strategies

### 1. Development Workflow Integration

#### Pre-Commit Hooks

**Git Pre-Commit Hook (`.git/hooks/pre-commit`):**
```bash
#!/bin/bash
# Pre-commit hook to prevent inline CSS

echo "Checking for inline CSS styles..."

# Check for inline styles in templates (excluding emails)
INLINE_STYLES=$(find templates -name "*.html" -not -path "*/emails/*" -exec grep -l 'style="' {} \;)
ADMIN_INLINE_STYLES=$(find admin/templates -name "*.html" -exec grep -l 'style="' {} \;)

if [ ! -z "$INLINE_STYLES" ] || [ ! -z "$ADMIN_INLINE_STYLES" ]; then
    echo "❌ ERROR: Inline styles detected in templates:"
    echo "$INLINE_STYLES"
    echo "$ADMIN_INLINE_STYLES"
    echo ""
    echo "Please extract inline styles to CSS files before committing."
    echo "See docs/css-organization-guide.md for guidance."
    exit 1
fi

echo "✅ No inline styles detected. Commit allowed."
exit 0
```

**Make executable:**
```bash
chmod +x .git/hooks/pre-commit
```

#### IDE Integration

**VS Code Settings (`.vscode/settings.json`):**
```json
{
    "html.validate.styles": true,
    "css.lint.unknownProperties": "error",
    "html.customData": [
        {
            "version": 1.1,
            "tags": [
                {
                    "name": "div",
                    "attributes": [
                        {
                            "name": "style",
                            "description": "❌ AVOID: Use CSS classes instead of inline styles"
                        }
                    ]
                }
            ]
        }
    ]
}
```

**ESLint Rules (`.eslintrc.js`):**
```javascript
module.exports = {
    rules: {
        // Prevent inline styles in JavaScript
        'no-inline-styles': 'error'
    }
};
```

### 2. Automated Detection Tools

#### CSS Extraction Helper

**Enhanced Detection Script (`scripts/css_inline_detector.py`):**
```python
#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import os
import re
import sys
from pathlib import Path

def detect_inline_styles():
    """Detect inline styles in HTML templates"""
    
    # Directories to scan
    template_dirs = [
        'templates',
        'admin/templates'
    ]
    
    # Exclude email templates (they need inline styles)
    exclude_patterns = [
        'templates/emails/',
        'templates/email_'
    ]
    
    violations = []
    
    for template_dir in template_dirs:
        if not os.path.exists(template_dir):
            continue
            
        for root, dirs, files in os.walk(template_dir):
            for file in files:
                if not file.endswith('.html'):
                    continue
                    
                file_path = os.path.join(root, file)
                
                # Skip email templates
                if any(exclude in file_path for exclude in exclude_patterns):
                    continue
                
                # Check for inline styles
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Find all style attributes
                style_matches = re.finditer(r'style="([^"]*)"', content)
                
                for match in style_matches:
                    line_num = content[:match.start()].count('\n') + 1
                    style_content = match.group(1)
                    
                    violations.append({
                        'file': file_path,
                        'line': line_num,
                        'style': style_content,
                        'context': get_context(content, match.start())
                    })
    
    return violations

def get_context(content, position):
    """Get context around the inline style"""
    lines = content.split('\n')
    line_num = content[:position].count('\n')
    
    start = max(0, line_num - 1)
    end = min(len(lines), line_num + 2)
    
    context_lines = []
    for i in range(start, end):
        prefix = '>>> ' if i == line_num else '    '
        context_lines.append(f"{prefix}{i+1}: {lines[i]}")
    
    return '\n'.join(context_lines)

def suggest_css_class(style_content):
    """Suggest appropriate CSS class for inline style"""
    
    suggestions = {
        'display: none': '.hidden',
        'display: block': '.d-block',
        'display: flex': '.d-flex',
        'width: 75%': '.w-75',
        'width: 100%': '.w-100',
        'font-size: 3rem': '.icon-lg',
        'cursor: move': '.image-zoom-wrapper',
        'position: absolute': '.position-absolute',
        'overflow-y: auto': '.scrollable-container'
    }
    
    # Check for exact matches
    if style_content in suggestions:
        return suggestions[style_content]
    
    # Check for pattern matches
    if 'display:' in style_content:
        return '.hidden or .d-block (see utilities.css)'
    elif 'width:' in style_content:
        return '.w-* utility class (see utilities.css)'
    elif 'font-size:' in style_content:
        return '.icon-* sizing class (see utilities.css)'
    elif 'height:' in style_content and 'min-height:' in style_content:
        return '.scrollable-* container class (see components.css)'
    
    return 'Create appropriate CSS class in components.css'

def main():
    """Main detection and reporting function"""
    
    print("🔍 Scanning for inline CSS styles...")
    print("=" * 60)
    
    violations = detect_inline_styles()
    
    if not violations:
        print("✅ No inline styles detected!")
        print("All templates are CSP compliant.")
        return 0
    
    print(f"❌ Found {len(violations)} inline style violations:")
    print()
    
    # Group violations by file
    files_with_violations = {}
    for violation in violations:
        file_path = violation['file']
        if file_path not in files_with_violations:
            files_with_violations[file_path] = []
        files_with_violations[file_path].append(violation)
    
    for file_path, file_violations in files_with_violations.items():
        print(f"📄 {file_path} ({len(file_violations)} violations)")
        print("-" * 40)
        
        for violation in file_violations:
            print(f"Line {violation['line']}: style=\"{violation['style']}\"")
            print(f"Suggestion: {suggest_css_class(violation['style'])}")
            print()
            print("Context:")
            print(violation['context'])
            print()
    
    print("=" * 60)
    print("📚 Resources:")
    print("- CSS Organization Guide: docs/css-organization-guide.md")
    print("- Utility Classes: static/css/utilities.css")
    print("- Component Classes: static/css/components.css")
    print()
    print("🔧 Quick fixes:")
    print("1. Replace style=\"display: none;\" with class=\"hidden\"")
    print("2. Replace style=\"width: X%;\" with class=\"w-X\"")
    print("3. Replace style=\"font-size: Xrem;\" with class=\"icon-*\"")
    
    return 1

if __name__ == '__main__':
    sys.exit(main())
```

#### Continuous Integration Integration

**GitHub Actions Workflow (`.github/workflows/css-check.yml`):**
```yaml
name: CSS Compliance Check

on:
  pull_request:
    paths:
      - 'templates/**'
      - 'admin/templates/**'
      - 'static/css/**'
      - 'admin/static/css/**'

jobs:
  css-compliance:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.8'
    
    - name: Check for inline CSS
      run: |
        python scripts/css_inline_detector.py
        if [ $? -ne 0 ]; then
          echo "❌ Inline CSS detected. Please extract to CSS files."
          exit 1
        fi
    
    - name: Validate CSS syntax
      run: |
        # Install CSS validator
        npm install -g css-validator-cli
        
        # Validate all CSS files
        find static/css -name "*.css" -exec css-validator {} \;
        find admin/static/css -name "*.css" -exec css-validator {} \;
```

### 3. Template Development Guidelines

#### Template Creation Checklist

**Before creating new templates:**
- [ ] Review existing CSS classes in `utilities.css`
- [ ] Check component classes in `components.css`
- [ ] Plan styling approach without inline styles
- [ ] Identify reusable patterns

**During template development:**
- [ ] Use semantic CSS classes
- [ ] Leverage existing utility classes
- [ ] Create component-specific classes when needed
- [ ] Document new CSS classes

**Before committing templates:**
- [ ] Run inline style detector
- [ ] Test CSP compliance
- [ ] Verify visual consistency
- [ ] Update CSS documentation if needed

#### Alternative Patterns

**Instead of inline styles, use these patterns:**

**❌ Inline Display Control:**
```html
<div style="display: none;" id="modal">Content</div>
<script>
document.getElementById('modal').style.display = 'block';
</script>
```

**✅ CSS Class Control:**
```html
<div class="modal-overlay" id="modal">Content</div>
<script>
document.getElementById('modal').classList.add('show');
</script>
```

**❌ Inline Dynamic Styling:**
```html
<div class="progress-bar" style="width: {{ progress }}%;">
```

**✅ CSS Variable Styling:**
```html
<div class="progress-bar-dynamic" style="--progress-width: {{ progress }}%;">
```

**❌ Inline Positioning:**
```html
<div style="position: absolute; top: 10px; left: 10px;">
```

**✅ CSS Class Positioning:**
```html
<div class="bulk-select-position">
```

### 4. JavaScript Integration

#### Avoiding Style Manipulation

**❌ Direct Style Manipulation:**
```javascript
// Avoid direct style property manipulation
element.style.display = 'none';
element.style.width = '75%';
element.style.backgroundColor = 'red';
```

**✅ Class-Based Manipulation:**
```javascript
// Use class-based styling
element.classList.add('hidden');
element.classList.add('w-75');
element.classList.add('bg-danger');

// Toggle states
element.classList.toggle('active');
element.classList.toggle('show');
```

#### CSS Variable Updates

**For dynamic values, use CSS variables:**
```javascript
// Update CSS variables for dynamic styling
element.style.setProperty('--progress-width', progress + '%');
element.style.setProperty('--dynamic-height', height + 'px');
```

### 5. Framework Integration

#### Flask Template Helpers

**Template Helper Functions (`utils/template_helpers.py`):**
```python
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from flask import Markup

def css_class_helper(base_class, conditions=None):
    """Helper to build CSS classes conditionally"""
    classes = [base_class]
    
    if conditions:
        for condition, class_name in conditions.items():
            if condition:
                classes.append(class_name)
    
    return ' '.join(classes)

def progress_bar_helper(percentage, size='md'):
    """Helper to create progress bar with CSS variables"""
    return Markup(f'''
        <div class="progress progress-{size}">
            <div class="progress-bar-dynamic" style="--progress-width: {percentage}%;"></div>
        </div>
    ''')

def modal_helper(content, modal_id, show=False):
    """Helper to create modal with proper CSS classes"""
    show_class = 'show' if show else ''
    return Markup(f'''
        <div class="modal-overlay {show_class}" id="{modal_id}">
            <div class="modal-content">
                {content}
            </div>
        </div>
    ''')
```

**Register helpers in Flask app:**
```python
from utils.template_helpers import css_class_helper, progress_bar_helper, modal_helper

app.jinja_env.globals.update(
    css_class=css_class_helper,
    progress_bar=progress_bar_helper,
    modal=modal_helper
)
```

#### Template Usage

**Using template helpers:**
```html
<!-- Dynamic CSS classes -->
<div class="{{ css_class('card', {'is_active': user.is_active, 'is-admin': user.is_admin}) }}">

<!-- Progress bar with CSS variables -->
{{ progress_bar(task.progress_percent, 'lg') }}

<!-- Modal with proper classes -->
{{ modal(modal_content, 'user-modal', show=show_modal) }}
```

### 6. Testing and Validation

#### Automated Testing

**CSS Compliance Test (`tests/test_css_compliance.py`):**
```python
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import unittest
import os
import re
from pathlib import Path

class TestCSSCompliance(unittest.TestCase):
    
    def test_no_inline_styles_in_templates(self):
        """Test that no inline styles exist in templates (excluding emails)"""
        
        template_dirs = ['templates', 'admin/templates']
        exclude_patterns = ['templates/emails/', 'templates/email_']
        
        violations = []
        
        for template_dir in template_dirs:
            if not os.path.exists(template_dir):
                continue
                
            for root, dirs, files in os.walk(template_dir):
                for file in files:
                    if not file.endswith('.html'):
                        continue
                        
                    file_path = os.path.join(root, file)
                    
                    # Skip email templates
                    if any(exclude in file_path for exclude in exclude_patterns):
                        continue
                    
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Find inline styles
                    style_matches = re.findall(r'style="[^"]*"', content)
                    
                    if style_matches:
                        violations.append({
                            'file': file_path,
                            'styles': style_matches
                        })
        
        if violations:
            error_msg = "Inline styles detected in templates:\n"
            for violation in violations:
                error_msg += f"  {violation['file']}: {violation['styles']}\n"
            self.fail(error_msg)
    
    def test_css_files_exist(self):
        """Test that required CSS files exist"""
        
        required_files = [
            'static/css/utilities.css',
            'static/css/components.css',
            'static/css/security-extracted.css',
            'admin/static/css/admin-extracted.css'
        ]
        
        for css_file in required_files:
            self.assertTrue(
                os.path.exists(css_file),
                f"Required CSS file missing: {css_file}"
            )
    
    def test_css_class_usage(self):
        """Test that templates use appropriate CSS classes"""
        
        # Check for common utility class usage
        template_dirs = ['templates', 'admin/templates']
        
        for template_dir in template_dirs:
            if not os.path.exists(template_dir):
                continue
                
            for root, dirs, files in os.walk(template_dir):
                for file in files:
                    if not file.endswith('.html'):
                        continue
                        
                    file_path = os.path.join(root, file)
                    
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check for proper class usage patterns
                    if 'display: none' in content:
                        self.fail(f"Found 'display: none' in {file_path}. Use .hidden class instead.")
                    
                    if 'style="width:' in content:
                        self.fail(f"Found inline width in {file_path}. Use .w-* utility classes.")

if __name__ == '__main__':
    unittest.main()
```

#### Manual Testing Checklist

**Before deploying templates:**
- [ ] No inline styles detected by automated tools
- [ ] All styling uses CSS classes
- [ ] Dynamic styles use CSS variables
- [ ] Interactive elements use class toggles
- [ ] CSP compliance verified in browser
- [ ] Visual consistency maintained
- [ ] Cross-browser compatibility tested

### 7. Team Training and Documentation

#### Developer Onboarding

**CSS Guidelines Training:**
1. Review CSS organization guide
2. Understand security implications
3. Learn utility class system
4. Practice template development
5. Use automated tools

#### Code Review Guidelines

**CSS-Related Code Review Checklist:**
- [ ] No inline styles introduced
- [ ] Appropriate CSS classes used
- [ ] New classes properly documented
- [ ] Consistent naming conventions
- [ ] Security implications considered

#### Knowledge Sharing

**Regular Team Activities:**
- CSS best practices workshops
- Code review sessions
- Security compliance training
- Tool usage demonstrations

## Emergency Procedures

### When Inline Styles Are Absolutely Necessary

**Rare exceptions may include:**
- Email templates (already excluded)
- Third-party widget integration
- Emergency hotfixes (temporary only)

**Emergency inline style procedure:**
1. **Document the exception:**
   ```html
   <!-- EMERGENCY INLINE STYLE - TEMPORARY -->
   <!-- Reason: [Specific reason] -->
   <!-- Date: [Current date] -->
   <!-- TODO: Extract to CSS by [Date] -->
   <div style="display: none;">Emergency content</div>
   ```

2. **Create tracking issue:**
   - Document the inline style
   - Set extraction deadline
   - Assign responsibility

3. **Schedule extraction:**
   - Plan CSS extraction ASAP
   - Test thoroughly
   - Remove emergency style

## Conclusion

Preventing inline CSS requires:
- **Automated Detection**: Tools and scripts to catch violations
- **Development Integration**: Workflow and IDE integration
- **Team Training**: Education and best practices
- **Continuous Monitoring**: Ongoing compliance checking

Following these guidelines ensures continued CSP compliance and security best practices.