#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
CSP Violation Fix Script
Automatically fixes CSP violations by replacing inline event handlers and styles
"""

import os
import re
import sys
from pathlib import Path

def fix_inline_event_handlers(content):
    """Replace inline event handlers with data attributes"""
    
    # Common onclick patterns
    replacements = [
        # Window actions
        (r'onclick="window\.location\.reload\(\)"', 'data-action="reload"'),
        (r'onclick="window\.history\.back\(\)"', 'data-action="go-back"'),
        (r'onclick="location\.reload\(\)"', 'data-action="reload"'),
        
        # Platform management
        (r'onclick="switchPlatform\((\d+),\s*\'([^\']+)\'\)"', r'data-action="switch-platform" data-platform-id="\1" data-platform-name="\2"'),
        (r'onclick="editPlatform\((\d+)\)"', r'data-action="edit-platform" data-platform-id="\1"'),
        (r'onclick="testConnection\((\d+),\s*\'([^\']+)\'\)"', r'data-action="test-connection" data-platform-id="\1" data-platform-name="\2"'),
        (r'onclick="deletePlatform\((\d+),\s*\'([^\']+)\'\)"', r'data-action="delete-platform" data-platform-id="\1" data-platform-name="\2"'),
        (r'onclick="confirmPlatformDeletion\(\)"', 'data-action="confirm-platform-deletion"'),
        (r'onclick="switchToPlatform\((\d+)\)"', r'data-action="switch-to-platform" data-platform-id="\1"'),
        (r'onclick="showPlatformSwitcher\(\)"', 'data-action="show-platform-switcher"'),
        (r'onclick="hidePlatformSwitcher\(\)"', 'data-action="hide-platform-switcher"'),
        (r'onchange="switchPlatform\(this\.value\)"', 'data-action="switch-platform-select"'),
        
        # Caption generation
        (r'onclick="cancelTask\(\'([^\']+)\'\)"', r'data-action="cancel-task" data-task-id="\1"'),
        (r'onclick="filterTasks\(\'([^\']+)\'\)"', r'data-action="filter-tasks" data-filter="\1"'),
        (r'onclick="retryTask\(\'([^\']+)\'\)"', r'data-action="retry-task" data-task-id="\1"'),
        (r'onclick="showErrorDetails\(\'([^\']+)\'\)"', r'data-action="show-error-details" data-task-id="\1"'),
        (r'onclick="cancelGeneration\(\'([^\']+)\'\)"', r'data-action="cancel-generation" data-task-id="\1"'),
        
        # Profile management
        (r'onclick="toggleEditMode\(\)"', 'data-action="toggle-edit-mode"'),
        
        # Admin job management
        (r'onclick="loadJobDetails\(\'([^\']+)\'\)"', r'data-action="load-job-details" data-job-id="\1"'),
        (r'onclick="copyToClipboard\(\'([^\']+)\'\)"', r'data-action="copy-clipboard" data-copy-text="\1"'),
        (r'onclick="selectAllJobs\(\)"', 'data-action="select-all-jobs"'),
        (r'onclick="clearJobSelection\(\)"', 'data-action="clear-job-selection"'),
        (r'onclick="executeBulkAction\(\)"', 'data-action="execute-bulk-action"'),
        (r'onclick="handleBulkActionChange\(\)"', 'data-action="handle-bulk-action-change"'),
        (r'onclick="addBulkQuickNote\(\'([^\']+)\'\)"', r'data-action="add-bulk-quick-note" data-note="\1"'),
        (r'onclick="addBulkTag\(\'([^\']+)\'\)"', r'data-action="add-bulk-tag" data-tag="\1"'),
        (r'onclick="addQuickNote\(\'([^\']+)\'\)"', r'data-action="add-quick-note" data-note="\1"'),
        (r'onclick="addTag\(\'([^\']+)\'\)"', r'data-action="add-tag" data-tag="\1"'),
        (r'onclick="loadTemplate\(\'([^\']+)\'\)"', r'data-action="load-template" data-template="\1"'),
        
        # Form submissions and changes
        (r'onchange="this\.form\.submit\(\)"', 'data-auto-submit="true"'),
        (r'onchange="handleBulkActionChange\(\)"', 'data-action="handle-bulk-action-change"'),
        
        # Generic function calls - catch remaining patterns
        (r'onclick="([^"(]+)\(\)"', r'data-action="\1"'),
        (r'onclick="([^"(]+)\(([^")]+)\)"', r'data-action="\1" data-params="\2"'),
    ]
    
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)
    
    return content

def fix_inline_styles(content):
    """Replace common inline styles with CSS classes"""
    
    replacements = [
        # Large icons
        (r'style="font-size:\s*4rem;"', 'class="status-icon-large"'),
        
        # Progress bars
        (r'style="--progress-width:\s*([^"]+);"', r'style="--progress-width: \1;" class="progress-custom"'),
        
        # Cursor pointer
        (r'style="cursor:\s*pointer;"', 'class="cursor-pointer"'),
        
        # Email styles - these are more complex and may need manual review
        (r'style="font-family:\s*Arial,\s*sans-serif;\s*line-height:\s*1\.6;\s*color:\s*#333;"', 'class="email-body"'),
        (r'style="max-width:\s*600px;\s*margin:\s*0\s*auto;\s*padding:\s*20px;"', 'class="email-container"'),
        (r'style="text-align:\s*center;"', 'class="text-center"'),
        (r'style="text-align:\s*center;\s*max-width:\s*800px;\s*margin:\s*auto;"', 'class="landing-section-text"'),
    ]
    
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)
    
    return content

def process_template_file(file_path):
    """Process a single template file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Fix inline event handlers
        content = fix_inline_event_handlers(content)
        
        # Fix inline styles
        content = fix_inline_styles(content)
        
        # Only write if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Fixed: {file_path}")
            return True
        else:
            print(f"⏭️  No changes: {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return False

def add_csp_scripts_to_base_template():
    """Add CSP-compliant scripts to base template"""
    base_template_path = Path('templates/base.html')
    
    if not base_template_path.exists():
        print(f"❌ Base template not found: {base_template_path}")
        return False
    
    try:
        with open(base_template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if CSP scripts are already included
        if 'csp-compliant-handlers.js' in content:
            print("✅ CSP scripts already included in base template")
            return True
        
        # Find the closing </body> tag and add scripts before it
        script_includes = '''
    <!-- CSP-Compliant Scripts -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/csp-compliant-styles.css') }}?v=1.0.1">
    <script src="{{ url_for('static', filename='js/csp-compliant-handlers.js') }}?v=1.0.1" nonce="{{ g.csp_nonce if g.csp_nonce else '' }}"></script>
</body>'''
        
        content = content.replace('</body>', script_includes)
        
        with open(base_template_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Added CSP-compliant scripts to base template")
        return True
        
    except Exception as e:
        print(f"❌ Error updating base template: {e}")
        return False

def main():
    """Main function to fix CSP violations"""
    print("🔒 CSP Violation Fix Script")
    print("=" * 50)
    
    # Find all HTML template files
    templates_dir = Path('templates')
    if not templates_dir.exists():
        print(f"❌ Templates directory not found: {templates_dir}")
        sys.exit(1)
    
    html_files = list(templates_dir.rglob('*.html'))
    
    if not html_files:
        print("❌ No HTML template files found")
        sys.exit(1)
    
    print(f"📁 Found {len(html_files)} HTML template files")
    
    # Process each template file
    fixed_count = 0
    for file_path in html_files:
        if process_template_file(file_path):
            fixed_count += 1
    
    print(f"\n📊 Summary:")
    print(f"   Total files: {len(html_files)}")
    print(f"   Files fixed: {fixed_count}")
    print(f"   Files unchanged: {len(html_files) - fixed_count}")
    
    # Add CSP scripts to base template
    print(f"\n🔧 Updating base template...")
    add_csp_scripts_to_base_template()
    
    print(f"\n✅ CSP violation fixes completed!")
    print(f"\n📋 Next steps:")
    print(f"   1. Review the changes in your templates")
    print(f"   2. Test your application functionality")
    print(f"   3. Update your JavaScript functions in csp-compliant-handlers.js")
    print(f"   4. Restart your web application")
    print(f"   5. Check for remaining CSP violations in browser console")

if __name__ == '__main__':
    main()