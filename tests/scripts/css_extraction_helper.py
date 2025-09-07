#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
CSS Extraction Helper - Utility to help extract inline styles to CSS classes
"""

import os
import re
import glob
import argparse
from pathlib import Path
from collections import defaultdict


class CSSExtractionHelper:
    """Helper for extracting inline styles and generating CSS classes"""
    
    def __init__(self, project_root=None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent.parent
        self.templates_dir = self.project_root / "templates"
        self.admin_templates_dir = self.project_root / "admin" / "templates"
    
    def extract_unique_styles(self):
        """Extract unique inline styles and suggest CSS classes"""
        inline_style_pattern = re.compile(r'style\s*=\s*["\']([^"\']*)["\']', re.IGNORECASE)
        unique_styles = defaultdict(list)
        
        # Get all template files, excluding email templates
        template_files = glob.glob(str(self.templates_dir / "**" / "*.html"), recursive=True)
        # Filter out email templates as they require inline CSS for email client compatibility
        template_files = [f for f in template_files if '/emails/' not in f.replace('\\', '/')]
        
        if self.admin_templates_dir.exists():
            admin_template_files = glob.glob(str(self.admin_templates_dir / "**" / "*.html"), recursive=True)
            template_files.extend(admin_template_files)
        
        for template_file in template_files:
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
                matches = inline_style_pattern.findall(content)
                
                for style_content in matches:
                    # Clean up the style content
                    style_content = style_content.strip()
                    if style_content:
                        relative_path = os.path.relpath(template_file, self.project_root)
                        unique_styles[style_content].append(relative_path)
        
        return unique_styles
    
    def suggest_css_classes(self, style_content):
        """Suggest CSS class names based on style content"""
        suggestions = []
        
        # Common patterns
        if 'display: none' in style_content:
            suggestions.append('hidden')
        elif 'display:none' in style_content:
            suggestions.append('hidden')
        
        if 'font-size:' in style_content or 'font-size :' in style_content:
            if '3rem' in style_content or '4rem' in style_content:
                suggestions.append('icon-lg')
            elif '2rem' in style_content or '2.5rem' in style_content:
                suggestions.append('icon-md')
            elif '1.5rem' in style_content:
                suggestions.append('icon-sm')
        
        if 'width:' in style_content and '%' in style_content:
            if 'progress' in style_content.lower():
                suggestions.append('progress-bar-dynamic')
            else:
                suggestions.append('width-percentage')
        
        if 'height:' in style_content and 'px' in style_content:
            if '200px' in style_content:
                suggestions.append('image-preview')
            elif '20px' in style_content or '8px' in style_content:
                suggestions.append('progress-bar')
        
        if 'max-height:' in style_content and 'overflow-y: auto' in style_content:
            suggestions.append('scrollable-container')
        
        if 'position: absolute' in style_content:
            suggestions.append('absolute-positioned')
        
        if 'cursor:' in style_content:
            if 'move' in style_content:
                suggestions.append('cursor-move')
            elif 'pointer' in style_content:
                suggestions.append('cursor-pointer')
        
        if 'transform: scale' in style_content:
            suggestions.append('scaled-element')
        
        if 'background:' in style_content or 'background-color:' in style_content:
            suggestions.append('custom-background')
        
        # If no specific suggestions, create generic one
        if not suggestions:
            # Create a generic class name based on properties
            properties = []
            for prop in ['display', 'width', 'height', 'font-size', 'color', 'margin', 'padding']:
                if f'{prop}:' in style_content:
                    properties.append(prop.replace('-', ''))
            
            if properties:
                suggestions.append('-'.join(properties[:2]) + '-style')
            else:
                suggestions.append('custom-style')
        
        return suggestions
    
    def generate_extraction_report(self):
        """Generate a report with extraction suggestions"""
        unique_styles = self.extract_unique_styles()
        
        print("=== CSS Extraction Helper Report ===\n")
        print("📧 Email templates (templates/emails/) are intentionally excluded from this report.")
        print("   Email templates require inline CSS for proper rendering across email clients.\n")
        print(f"Found {len(unique_styles)} unique inline styles in web templates\n")
        
        # Group by suggested class names
        class_suggestions = defaultdict(list)
        
        for style_content, files in unique_styles.items():
            suggestions = self.suggest_css_classes(style_content)
            primary_suggestion = suggestions[0] if suggestions else 'custom-style'
            
            class_suggestions[primary_suggestion].append({
                'style': style_content,
                'files': files,
                'count': len(files)
            })
        
        # Print suggestions grouped by class
        for class_name, styles in sorted(class_suggestions.items()):
            print(f"🎨 Suggested class: .{class_name}")
            print(f"   Styles to extract: {len(styles)}")
            
            for style_info in sorted(styles, key=lambda x: x['count'], reverse=True):
                print(f"   • {style_info['style']}")
                print(f"     Used in {style_info['count']} file(s): {', '.join(style_info['files'][:3])}")
                if len(style_info['files']) > 3:
                    print(f"     ... and {len(style_info['files']) - 3} more")
                print()
        
        print("=== Extraction Priority ===")
        
        # Sort by frequency
        all_styles = [(style, files) for style, files in unique_styles.items()]
        all_styles.sort(key=lambda x: len(x[1]), reverse=True)
        
        print("\n📊 Most frequently used inline styles:")
        for i, (style, files) in enumerate(all_styles[:10]):
            print(f"   {i+1}. {style}")
            print(f"      Used in {len(files)} files")
        
        print(f"\n=== End Report ===")
    
    def generate_css_template(self, class_name, style_content):
        """Generate CSS template for a given style"""
        return f"""
/* {class_name} - extracted from inline styles */
.{class_name} {{
    {style_content}
}}
"""


def main():
    parser = argparse.ArgumentParser(description='CSS Extraction Helper')
    parser.add_argument('--report', action='store_true', help='Generate extraction report')
    parser.add_argument('--project-root', help='Project root directory')
    
    args = parser.parse_args()
    
    helper = CSSExtractionHelper(args.project_root)
    
    if args.report:
        helper.generate_extraction_report()
    else:
        print("Use --report to generate extraction suggestions")


if __name__ == '__main__':
    main()