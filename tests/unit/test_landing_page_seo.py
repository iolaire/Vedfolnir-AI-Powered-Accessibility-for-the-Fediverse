# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import unittest
import sys
import os
import json
import re
from bs4 import BeautifulSoup

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from app.core.database.core.database_manager import DatabaseManager


class TestLandingPageSEO(unittest.TestCase):
    """Test SEO metadata and structured data implementation for the landing page"""
    
    def setUp(self):
        """Set up test environment"""
        # Import the Flask app from web_app module
        import web_app
        self.app = web_app.app
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up test environment"""
        self.app_context.pop()
    
    def test_meta_title_tag_requirement_7_1(self):
        """Test that landing page includes appropriate meta title tag (Requirement 7.1)"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        soup = BeautifulSoup(response.data, 'html.parser')
        title_tag = soup.find('title')
        
        self.assertIsNotNone(title_tag, "Title tag should be present")
        self.assertIn("Vedfolnir", title_tag.text)
        self.assertIn("AI-Powered Accessibility", title_tag.text)
        self.assertIn("Fediverse", title_tag.text)
    
    def test_meta_description_tag_requirement_7_2(self):
        """Test that landing page includes meta description tag (Requirement 7.2)"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        soup = BeautifulSoup(response.data, 'html.parser')
        description_tag = soup.find('meta', attrs={'name': 'description'})
        
        self.assertIsNotNone(description_tag, "Meta description tag should be present")
        description_content = description_tag.get('content', '')
        
        # Verify description contains key value proposition elements
        self.assertIn("alt text generation", description_content.lower())
        self.assertIn("activitypub", description_content.lower())
        self.assertIn("accessible", description_content.lower())
        self.assertIn("ai-powered", description_content.lower())
        
        # Verify description length is appropriate for SEO (150-160 characters recommended)
        self.assertGreater(len(description_content), 120, "Description should be substantial")
        self.assertLess(len(description_content), 200, "Description should not be too long")
    
    def test_open_graph_tags_requirement_7_3(self):
        """Test that landing page includes proper Open Graph tags (Requirement 7.3)"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Test required Open Graph tags
        og_title = soup.find('meta', attrs={'property': 'og:title'})
        og_description = soup.find('meta', attrs={'property': 'og:description'})
        og_type = soup.find('meta', attrs={'property': 'og:type'})
        og_url = soup.find('meta', attrs={'property': 'og:url'})
        og_image = soup.find('meta', attrs={'property': 'og:image'})
        og_site_name = soup.find('meta', attrs={'property': 'og:site_name'})
        
        self.assertIsNotNone(og_title, "og:title should be present")
        self.assertIsNotNone(og_description, "og:description should be present")
        self.assertIsNotNone(og_type, "og:type should be present")
        self.assertIsNotNone(og_url, "og:url should be present")
        self.assertIsNotNone(og_image, "og:image should be present")
        self.assertIsNotNone(og_site_name, "og:site_name should be present")
        
        # Verify content quality
        self.assertIn("Vedfolnir", og_title.get('content', ''))
        self.assertEqual("website", og_type.get('content', ''))
        self.assertEqual("Vedfolnir", og_site_name.get('content', ''))
        
        # Test Twitter Card tags
        twitter_card = soup.find('meta', attrs={'name': 'twitter:card'})
        twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
        twitter_description = soup.find('meta', attrs={'name': 'twitter:description'})
        twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
        
        self.assertIsNotNone(twitter_card, "Twitter card should be present")
        self.assertIsNotNone(twitter_title, "Twitter title should be present")
        self.assertIsNotNone(twitter_description, "Twitter description should be present")
        self.assertIsNotNone(twitter_image, "Twitter image should be present")
        
        self.assertEqual("summary_large_image", twitter_card.get('content', ''))
    
    def test_structured_data_markup_requirement_7_4(self):
        """Test that landing page includes structured data markup (Requirement 7.4)"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Find all JSON-LD structured data scripts
        json_ld_scripts = soup.find_all('script', attrs={'type': 'application/ld+json'})
        
        self.assertGreater(len(json_ld_scripts), 0, "Should have structured data scripts")
        
        # Test for specific structured data types
        structured_data_types = []
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and '@type' in data:
                    structured_data_types.append(data['@type'])
            except (json.JSONDecodeError, TypeError):
                continue
        
        # Verify we have key structured data types
        expected_types = ['SoftwareApplication', 'Organization', 'WebSite']
        for expected_type in expected_types:
            self.assertIn(expected_type, structured_data_types, 
                         f"Should have {expected_type} structured data")
        
        # Test SoftwareApplication structured data specifically
        software_app_data = None
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') == 'SoftwareApplication':
                    software_app_data = data
                    break
            except (json.JSONDecodeError, TypeError):
                continue
        
        self.assertIsNotNone(software_app_data, "Should have SoftwareApplication structured data")
        self.assertEqual("Vedfolnir", software_app_data.get('name'))
        self.assertEqual("AccessibilityApplication", software_app_data.get('applicationCategory'))
        self.assertIn('featureList', software_app_data)
        self.assertIsInstance(software_app_data.get('featureList'), list)
    
    def test_heading_hierarchy_seo_requirement_7_5(self):
        """Test that landing page uses proper heading hierarchy for SEO (Requirement 7.5)"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Find all heading tags
        h1_tags = soup.find_all('h1')
        h2_tags = soup.find_all('h2')
        h3_tags = soup.find_all('h3')
        h4_tags = soup.find_all('h4')
        
        # Should have exactly one H1 tag
        self.assertEqual(len(h1_tags), 1, "Should have exactly one H1 tag")
        
        # H1 should contain main keywords
        h1_text = h1_tags[0].get_text()
        self.assertIn("Vedfolnir", h1_text)
        self.assertIn("AI-Powered Accessibility", h1_text)
        self.assertIn("Fediverse", h1_text)
        
        # Should have multiple H2 tags for main sections
        self.assertGreater(len(h2_tags), 1, "Should have multiple H2 tags for sections")
        
        # Should have H3 tags for subsections
        self.assertGreater(len(h3_tags), 0, "Should have H3 tags for subsections")
        
        # Verify H2 tags contain relevant keywords
        h2_texts = [tag.get_text() for tag in h2_tags]
        h2_combined = ' '.join(h2_texts).lower()
        
        self.assertIn("accessibility", h2_combined)
        self.assertIn("features", h2_combined)
    
    def test_keywords_naturally_integrated_requirement_7_6(self):
        """Test that relevant keywords are naturally integrated into content (Requirement 7.6)"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Get all text content
        page_text = soup.get_text().lower()
        
        # Define key SEO keywords that should appear naturally in content
        required_keywords = [
            'accessibility',
            'alt text',
            'ai-powered',
            'activitypub',
            'mastodon',
            'pixelfed',
            'digital inclusion',
            'screen reader',
            'image descriptions',
            'fediverse',
            'automated',
            'wcag'
        ]
        
        # Verify each keyword appears in the content
        for keyword in required_keywords:
            self.assertIn(keyword, page_text, 
                         f"Keyword '{keyword}' should appear naturally in content")
        
        # Test keyword density is reasonable (not keyword stuffing)
        # Count occurrences of main keyword "accessibility"
        accessibility_count = page_text.count('accessibility')
        word_count = len(page_text.split())
        
        # Keyword density should be reasonable (1-3% is good for SEO)
        keyword_density = (accessibility_count / word_count) * 100
        self.assertLess(keyword_density, 5.0, "Keyword density should not be excessive")
        self.assertGreater(keyword_density, 0.5, "Main keyword should appear sufficiently")
    
    def test_additional_seo_meta_tags(self):
        """Test additional SEO meta tags for comprehensive optimization"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Test for additional important meta tags
        robots_tag = soup.find('meta', attrs={'name': 'robots'})
        keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
        author_tag = soup.find('meta', attrs={'name': 'author'})
        canonical_link = soup.find('link', attrs={'rel': 'canonical'})
        
        self.assertIsNotNone(robots_tag, "Robots meta tag should be present")
        self.assertIsNotNone(keywords_tag, "Keywords meta tag should be present")
        self.assertIsNotNone(author_tag, "Author meta tag should be present")
        self.assertIsNotNone(canonical_link, "Canonical link should be present")
        
        # Verify robots tag allows indexing
        robots_content = robots_tag.get('content', '').lower()
        self.assertIn('index', robots_content)
        self.assertIn('follow', robots_content)
        
        # Verify keywords tag contains relevant terms
        keywords_content = keywords_tag.get('content', '').lower()
        self.assertIn('accessibility', keywords_content)
        self.assertIn('alt text', keywords_content)
        self.assertIn('ai', keywords_content)
    
    def test_mobile_seo_optimization(self):
        """Test mobile-specific SEO optimization"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Test viewport meta tag
        viewport_tag = soup.find('meta', attrs={'name': 'viewport'})
        self.assertIsNotNone(viewport_tag, "Viewport meta tag should be present")
        
        viewport_content = viewport_tag.get('content', '')
        self.assertIn('width=device-width', viewport_content)
        self.assertIn('initial-scale=1.0', viewport_content)
        
        # Test mobile-specific meta tags
        mobile_capable = soup.find('meta', attrs={'name': 'mobile-web-app-capable'})
        apple_capable = soup.find('meta', attrs={'name': 'apple-mobile-web-app-capable'})
        
        self.assertIsNotNone(mobile_capable, "Mobile web app capable tag should be present")
        self.assertIsNotNone(apple_capable, "Apple mobile web app capable tag should be present")


if __name__ == '__main__':
    unittest.main()