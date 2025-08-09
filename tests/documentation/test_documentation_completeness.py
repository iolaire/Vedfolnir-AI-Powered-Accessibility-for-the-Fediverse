#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Tests for Task 6.1: Documentation completeness and accuracy
"""

import unittest
import os
import re
from pathlib import Path

class TestDocumentationCompleteness(unittest.TestCase):
    """Test that all required documentation exists and is complete"""
    
    def setUp(self):
        self.docs_dir = Path(__file__).parent.parent.parent / 'docs'
        self.root_dir = Path(__file__).parent.parent.parent
        
    def test_readme_explains_platform_features(self):
        """Test README clearly explains platform-aware features"""
        readme_path = self.root_dir / 'README.md'
        self.assertTrue(readme_path.exists(), "README.md must exist")
        
        content = readme_path.read_text()
        
        # Check for platform-aware content
        platform_keywords = ['platform', 'Pixelfed', 'Mastodon', 'ActivityPub']
        for keyword in platform_keywords:
            self.assertIn(keyword, content, f"README should mention {keyword}")
    
    def test_platform_setup_guide_exists(self):
        """Test setup guide enables successful platform configuration"""
        setup_path = self.docs_dir / 'platform_setup.md'
        self.assertTrue(setup_path.exists(), "Platform setup guide must exist")
        
        content = setup_path.read_text()
        
        # Check for essential setup content
        setup_keywords = ['Pixelfed Setup', 'Mastodon Setup', 'Configuration']
        for keyword in setup_keywords:
            self.assertIn(keyword, content, f"Setup guide should include {keyword}")
    
    def test_migration_guide_provides_upgrade_path(self):
        """Test migration guide provides clear upgrade path"""
        migration_path = self.docs_dir / 'migration_guide.md'
        self.assertTrue(migration_path.exists(), "Migration guide must exist")
        
        content = migration_path.read_text()
        
        # Check for migration content
        migration_keywords = ['migration', 'backup', 'rollback']
        for keyword in migration_keywords:
            self.assertIn(keyword, content, f"Migration guide should include {keyword}")
    
    def test_troubleshooting_guide_covers_scenarios(self):
        """Test troubleshooting guide covers common scenarios"""
        troubleshooting_path = self.docs_dir / 'troubleshooting.md'
        self.assertTrue(troubleshooting_path.exists(), "Troubleshooting guide must exist")
        
        content = troubleshooting_path.read_text()
        
        # Check for troubleshooting content
        troubleshooting_keywords = ['Connection Issues', 'Platform Data Issues', 'Migration Issues']
        for keyword in troubleshooting_keywords:
            self.assertIn(keyword, content, f"Troubleshooting guide should include {keyword}")
    
    def test_user_guide_explains_interface_features(self):
        """Test user guide explains all interface features"""
        user_guide_path = self.docs_dir / 'user_guide.md'
        self.assertTrue(user_guide_path.exists(), "User guide must exist")
        
        content = user_guide_path.read_text()
        
        # Check for user interface content
        ui_keywords = ['Platform Management', 'web application', 'user', 'Log in']
        for keyword in ui_keywords:
            self.assertIn(keyword, content, f"User guide should include {keyword}")
    
    def test_api_documentation_is_accurate(self):
        """Test API documentation is accurate and complete"""
        api_docs_path = self.docs_dir / 'api_documentation.md'
        self.assertTrue(api_docs_path.exists(), "API documentation must exist")
        
        content = api_docs_path.read_text()
        
        # Check for API content
        api_keywords = ['API', 'endpoint', 'platform', 'authentication']
        for keyword in api_keywords:
            self.assertIn(keyword, content, f"API documentation should include {keyword}")


class TestDocumentationExamples(unittest.TestCase):
    """Test that documentation examples are valid"""
    
    def setUp(self):
        self.docs_dir = Path(__file__).parent.parent.parent / 'docs'
    
    def test_code_snippets_have_proper_syntax(self):
        """Test that code snippets in documentation have proper syntax"""
        for doc_file in self.docs_dir.glob('*.md'):
            content = doc_file.read_text()
            
            # Find bash code blocks
            bash_blocks = re.findall(r'```bash\n(.*?)\n```', content, re.DOTALL)
            for block in bash_blocks:
                # Basic validation - no obvious syntax errors
                self.assertNotIn('{{', block, f"Template variables found in {doc_file.name}")
                self.assertNotIn('}}', block, f"Template variables found in {doc_file.name}")
    
    def test_environment_examples_are_realistic(self):
        """Test that environment variable examples are realistic"""
        setup_path = self.docs_dir / 'platform_setup.md'
        if setup_path.exists():
            content = setup_path.read_text()
            
            # Check for realistic URLs
            if 'ACTIVITYPUB_INSTANCE_URL' in content:
                self.assertIn('https://', content, "Should use HTTPS URLs in examples")
    
    def test_no_real_credentials_in_docs(self):
        """Test that no real credentials are present in documentation"""
        sensitive_patterns = [
            r'[A-Za-z0-9]{40,}',  # Long tokens
            r'sk_[a-zA-Z0-9]{24,}',  # API keys
            r'password.*=.*[^example]',  # Real passwords
        ]
        
        for doc_file in self.docs_dir.glob('*.md'):
            content = doc_file.read_text()
            
            for pattern in sensitive_patterns:
                matches = re.findall(pattern, content)
                # Filter out obvious examples
                real_matches = [m for m in matches if not any(ex in m.lower() for ex in ['example', 'test', 'your_', 'abc123'])]
                self.assertEqual(len(real_matches), 0, f"Potential real credentials in {doc_file.name}: {real_matches}")


class TestDocumentationStructure(unittest.TestCase):
    """Test documentation structure and organization"""
    
    def setUp(self):
        self.docs_dir = Path(__file__).parent.parent.parent / 'docs'
        self.root_dir = Path(__file__).parent.parent.parent
    
    def test_all_required_docs_exist(self):
        """Test that all required documentation files exist"""
        required_docs = [
            'platform_setup.md',
            'migration_guide.md', 
            'troubleshooting.md',
            'user_guide.md',
            'api_documentation.md'
        ]
        
        for doc in required_docs:
            doc_path = self.docs_dir / doc
            self.assertTrue(doc_path.exists(), f"Required documentation {doc} must exist")
    
    def test_docs_have_proper_headers(self):
        """Test that documentation files have proper header structure"""
        for doc_file in self.docs_dir.glob('*.md'):
            content = doc_file.read_text()
            
            # Should have at least one header
            self.assertRegex(content, r'^#', f"{doc_file.name} should have headers")
    
    def test_docs_are_not_empty(self):
        """Test that documentation files are not empty"""
        for doc_file in self.docs_dir.glob('*.md'):
            content = doc_file.read_text().strip()
            self.assertGreater(len(content), 100, f"{doc_file.name} should have substantial content")


if __name__ == '__main__':
    unittest.main(verbosity=2)