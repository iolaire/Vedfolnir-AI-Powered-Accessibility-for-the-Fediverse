#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
CSS Security Scanner - Utility script for scanning inline styles and CSS usage
"""

import os
import re
import glob
import argparse
from pathlib import Path
from collections import defaultdict


class CSSSecurityScanner:
    """Scanner for CSS security issues and inline style detection"""
    
    def __init__(self, project_root=None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent.parent
        self.templates_dir = self.project_root / "templates"
        self.admin_templates_dir = self.project_root / "admin" / "templates"
        
    def scan_inline_styles(self, detailed=False):
        """Scan for inline styles in HTML templates"""
        inline_style_pattern = re.compile(r'style\s*=\s*["\'][^"\']*["\']', re.IGNORECASE)
        violations = []
        
        # Get all template files
        template_files = glob.glob(str(self.templates_dir / "**" / "*.html"), recursive=True)
        if self.admin_templates_dir.exists():
            admin_template_files = glob.glob(str(self.admin_templates_dir / "**" / "*.html"), recursive=True)
            template_files.extend(admin_template_files)
        
        for template_file in template_files:
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
                matches = inline_style_pattern.findall(content)
                if matches:
                    relative_path = os.path.relpath(template_file, self.project_root)
                    violations.append({
                        'file': relative_path,
                        'count': len(matches),
                        'styles': matches if detailed else []
                    })
        
        return violations
    
    def analyze_inline_styles(self):
        """Analyze types of inline styles found"""
        violations = self.scan_inline_styles(detailed=True)
        style_types = defaultdict(int)
        
        for violation in violations:
            for style in violation['styles']:
                # Extract CSS properties
                style_content = re.search(r'["\']([^"\']*)["\']', style)
                if style_content:
                    properties = style_content.group(1).split(';')
                    for prop in properties:
                        if ':' in prop:
                            prop_name = prop.split(':')[0].strip()
                            style_types[prop_name] += 1
        
        return style_types
    
    def check_css_files(self):
        """Check if expected CSS files exist"""
        expected_files = [
            "static/css/security-extracted.css",
            "static/css/components.css", 
            "admin/static/css/admin-extracted.css"
        ]
        
        results = {}
        for css_file in expected_files:
            full_path = self.project_root / css_file
            results[css_file] = {
                'exists': full_path.exists(),
                'size': full_path.stat().st_size if full_path.exists() else 0
            }
        
        return results
    
    def generate_report(self):
        """Generate comprehensive CSS security report"""
        print("=== CSS Security Enhancement Report ===\n")
        
        # Inline styles scan
        violations = self.scan_inline_styles()
        print(f"📊 Inline Styles Summary:")
        print(f"   Files with inline styles: {len(violations)}")
        print(f"   Total inline style instances: {sum(v['count'] for v in violations)}")
        
        if violations:
            print(f"\n📋 Files with most inline styles:")
            sorted_violations = sorted(violations, key=lambda x: x['count'], reverse=True)
            for i, violation in enumerate(sorted_violations[:10]):  # Top 10
                print(f"   {i+1}. {violation['file']}: {violation['count']} styles")
        
        # Style type analysis
        print(f"\n🎨 Most Common CSS Properties:")
        style_types = self.analyze_inline_styles()
        sorted_types = sorted(style_types.items(), key=lambda x: x[1], reverse=True)
        for prop, count in sorted_types[:10]:  # Top 10
            print(f"   {prop}: {count} occurrences")
        
        # CSS files check
        print(f"\n📁 CSS Files Status:")
        css_files = self.check_css_files()
        for file_path, info in css_files.items():
            status = "✅ EXISTS" if info['exists'] else "❌ MISSING"
            size_info = f" ({info['size']} bytes)" if info['exists'] else ""
            print(f"   {file_path}: {status}{size_info}")
        
        print(f"\n=== End Report ===")


def main():
    parser = argparse.ArgumentParser(description='CSS Security Scanner')
    parser.add_argument('--detailed', action='store_true', help='Show detailed inline style information')
    parser.add_argument('--report', action='store_true', help='Generate comprehensive report')
    parser.add_argument('--project-root', help='Project root directory')
    
    args = parser.parse_args()
    
    scanner = CSSSecurityScanner(args.project_root)
    
    if args.report:
        scanner.generate_report()
    else:
        violations = scanner.scan_inline_styles(detailed=args.detailed)
        
        if not violations:
            print("✅ No inline styles found!")
        else:
            print(f"❌ Found {len(violations)} files with inline styles:")
            for violation in violations:
                print(f"  {violation['file']}: {violation['count']} styles")
                if args.detailed:
                    for style in violation['styles']:
                        print(f"    - {style}")


if __name__ == '__main__':
    main()