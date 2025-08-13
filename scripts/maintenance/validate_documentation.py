#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Documentation validation script for Vedfolnir.

This script validates:
- Configuration examples in documentation
- Code snippets for syntax errors
- Environment variable references
- Link validity (basic checks)
"""

import os
import re
import sys
import ast
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Set

class DocumentationValidator:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.config_vars = self._load_config_variables()
        
    def _load_config_variables(self) -> Set[str]:
        """Load all configuration variables from config.py"""
        config_vars = set()
        
        try:
            with open('config.py', 'r') as f:
                content = f.read()
                
            # Find environment variable references
            env_pattern = r'os\.getenv\(["\']([^"\']+)["\']'
            matches = re.findall(env_pattern, content)
            config_vars.update(matches)
            
            # Also check .env.example files
            for env_file in ['.env.example']:
                if os.path.exists(env_file):
                    with open(env_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                var_name = line.split('=')[0].strip()
                                config_vars.add(var_name)
                                
        except Exception as e:
            self.warnings.append(f"Could not load config variables: {e}")
            
        return config_vars
    
    def validate_file(self, filepath: str) -> None:
        """Validate a single documentation file"""
        print(f"Validating {filepath}...")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self.errors.append(f"{filepath}: Could not read file - {e}")
            return
            
        # Validate code blocks
        self._validate_code_blocks(filepath, content)
        
        # Validate environment variables
        self._validate_env_vars(filepath, content)
        
        # Validate configuration examples
        self._validate_config_examples(filepath, content)
        
        # Validate links (basic check)
        self._validate_links(filepath, content)
        
    def _validate_code_blocks(self, filepath: str, content: str) -> None:
        """Validate code blocks for syntax errors"""
        # Find bash code blocks
        bash_pattern = r'```(?:bash|sh|shell)\n(.*?)\n```'
        bash_blocks = re.findall(bash_pattern, content, re.DOTALL)
        
        for i, block in enumerate(bash_blocks):
            # Basic bash syntax validation
            if block.strip():
                # Check for common bash syntax issues
                lines = block.split('\n')
                for line_num, line in enumerate(lines, 1):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Check for unmatched quotes
                        if line.count('"') % 2 != 0 or line.count("'") % 2 != 0:
                            self.warnings.append(
                                f"{filepath}: Bash block {i+1}, line {line_num}: "
                                f"Possible unmatched quotes: {line}"
                            )
        
        # Find Python code blocks
        python_pattern = r'```python\n(.*?)\n```'
        python_blocks = re.findall(python_pattern, content, re.DOTALL)
        
        for i, block in enumerate(python_blocks):
            if block.strip():
                try:
                    # Try to parse as Python AST
                    ast.parse(block)
                except SyntaxError as e:
                    self.errors.append(
                        f"{filepath}: Python block {i+1}: Syntax error - {e}"
                    )
                except Exception as e:
                    self.warnings.append(
                        f"{filepath}: Python block {i+1}: Could not validate - {e}"
                    )
    
    def _validate_env_vars(self, filepath: str, content: str) -> None:
        """Validate environment variable references"""
        # Find environment variable references in documentation
        env_var_pattern = r'`([A-Z_][A-Z0-9_]*)`'
        doc_vars = set(re.findall(env_var_pattern, content))
        
        # Also find variables in configuration examples
        config_pattern = r'^([A-Z_][A-Z0-9_]*)='
        config_vars_in_doc = set()
        for line in content.split('\n'):
            line = line.strip()
            if re.match(config_pattern, line):
                var_name = line.split('=')[0].strip()
                config_vars_in_doc.add(var_name)
        
        # Check if documented variables exist in config
        all_doc_vars = doc_vars.union(config_vars_in_doc)
        for var in all_doc_vars:
            if var not in self.config_vars and not var.startswith('YOUR_') and var not in [
                'PATH', 'HOME', 'USER', 'PWD', 'SHELL'  # Common system variables
            ]:
                self.warnings.append(
                    f"{filepath}: Environment variable `{var}` not found in config.py"
                )
    
    def _validate_config_examples(self, filepath: str, content: str) -> None:
        """Validate configuration examples"""
        # Find configuration blocks
        config_pattern = r'```(?:bash|shell|env)\n((?:[A-Z_][A-Z0-9_]*=.*\n?)+)```'
        config_blocks = re.findall(config_pattern, content, re.MULTILINE)
        
        for i, block in enumerate(config_blocks):
            lines = block.strip().split('\n')
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    var_name, value = line.split('=', 1)
                    var_name = var_name.strip()
                    value = value.strip()
                    
                    # Check for placeholder values that might be real credentials
                    if any(suspicious in value.lower() for suspicious in [
                        'secret', 'token', 'key', 'password'
                    ]) and not any(placeholder in value.lower() for placeholder in [
                        'your_', 'example', 'change', 'here', 'placeholder'
                    ]):
                        self.warnings.append(
                            f"{filepath}: Config block {i+1}, line {line_num}: "
                            f"Possible real credential in example: {var_name}"
                        )
    
    def _validate_links(self, filepath: str, content: str) -> None:
        """Basic link validation"""
        # Find markdown links
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        links = re.findall(link_pattern, content)
        
        for link_text, url in links:
            # Check for relative file links
            if not url.startswith(('http://', 'https://', 'mailto:', '#')):
                # Relative file path
                if url.startswith('./'):
                    url = url[2:]
                
                # Check if file exists
                if not os.path.exists(url):
                    self.errors.append(
                        f"{filepath}: Broken link to file: {url}"
                    )
            
            # Check for common URL issues
            if url.startswith('http://') and 'localhost' not in url:
                self.warnings.append(
                    f"{filepath}: HTTP link (consider HTTPS): {url}"
                )
    
    def validate_all(self) -> bool:
        """Validate all documentation files"""
        doc_files = [
            'README.md',
            'docs/deployment.md',
            'docs/troubleshooting.md',
            'docs/multi-platform-setup.md',
            'docs/activitypub_platforms.md',
            'docs/batch_update.md',
            'docs/database_migrations.md'
        ]
        
        for doc_file in doc_files:
            if os.path.exists(doc_file):
                self.validate_file(doc_file)
            else:
                self.warnings.append(f"Documentation file not found: {doc_file}")
        
        # Validate example configuration files
        example_files = [
            '.env.example',
            '.env.example.mastodon',
            # Platform configuration now handled via web interface
        ]
        
        for example_file in example_files:
            if os.path.exists(example_file):
                self._validate_example_config(example_file)
            else:
                self.errors.append(f"Example configuration file missing: {example_file}")
        
        return len(self.errors) == 0
    
    def _validate_example_config(self, filepath: str) -> None:
        """Validate example configuration files"""
        print(f"Validating {filepath}...")
        
        try:
            with open(filepath, 'r') as f:
                content = f.read()
        except Exception as e:
            self.errors.append(f"{filepath}: Could not read file - {e}")
            return
        
        required_vars = {
            'ACTIVITYPUB_API_TYPE',
            'ACTIVITYPUB_INSTANCE_URL',
            'ACTIVITYPUB_USERNAME',
            'ACTIVITYPUB_ACCESS_TOKEN'
        }
        
        mastodon_vars = {
            'MASTODON_CLIENT_KEY',
            'MASTODON_CLIENT_SECRET'
        }
        
        found_vars = set()
        
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                var_name = line.split('=')[0].strip()
                found_vars.add(var_name)
                
                # Check for placeholder values
                value = line.split('=', 1)[1].strip()
                if not value or value in ['', '""', "''"]:
                    self.warnings.append(
                        f"{filepath}: Empty value for {var_name}"
                    )
                
                # Check for example values that look like real credentials
                if any(word in value.lower() for word in ['secret', 'token']) and \
                   not any(placeholder in value.lower() for placeholder in [
                       'your_', 'example', 'change', 'here', 'placeholder'
                   ]):
                    self.warnings.append(
                        f"{filepath}: Possible real credential: {var_name}={value}"
                    )
        
        # Check required variables
        missing_required = required_vars - found_vars
        if missing_required:
            self.errors.append(
                f"{filepath}: Missing required variables: {', '.join(missing_required)}"
            )
        
        # Check Mastodon-specific requirements
        if 'mastodon' in filepath.lower():
            missing_mastodon = mastodon_vars - found_vars
            if missing_mastodon:
                self.errors.append(
                    f"{filepath}: Missing Mastodon variables: {', '.join(missing_mastodon)}"
                )
    
    def print_results(self) -> None:
        """Print validation results"""
        if self.errors:
            print("\n❌ ERRORS:")
            for error in self.errors:
                print(f"  {error}")
        
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"  {warning}")
        
        if not self.errors and not self.warnings:
            print("\n✅ All documentation validation checks passed!")
        elif not self.errors:
            print(f"\n✅ No errors found, but {len(self.warnings)} warnings.")
        else:
            print(f"\n❌ Found {len(self.errors)} errors and {len(self.warnings)} warnings.")

def main():
    """Main function"""
    validator = DocumentationValidator()
    success = validator.validate_all()
    validator.print_results()
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())