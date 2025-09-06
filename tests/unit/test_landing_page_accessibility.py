# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import unittest
import sys
import os
from bs4 import BeautifulSoup
import re

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class TestLandingPageAccessibility(unittest.TestCase):
    """Test accessibility features of the landing page"""
    
    def setUp(self):
        """Set up test environment"""
        # Import the Flask app
        from web_app import app
        self.app = app
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up test environment"""
        self.app_context.pop()
    
    def test_skip_to_content_link_present(self):
        """Test that skip-to-content link is present and properly configured"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        soup = BeautifulSoup(response.data, 'html.parser')
        skip_link = soup.find('a', href='#main-content')
        
        self.assertIsNotNone(skip_link, "Skip-to-content link should be present")
        # Check for either class name (base template uses 'skip-to-content', landing uses 'visually-hidden-focusable')
        classes = skip_link.get('class', [])
        self.assertTrue('skip-to-content' in classes or 'visually-hidden-focusable' in classes)
        self.assertEqual(skip_link.text.strip(), 'Skip to main content')
    
    def test_main_content_landmark(self):
        """Test that main content has proper landmark"""
        response = self.client.get('/')
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Check for main-content id (from base template)
        main_content_id = soup.find(id='main-content')
        self.assertIsNotNone(main_content_id, "Main content with id should be present")
        
        # Check for main element (from landing page)
        main_element = soup.find('main')
        self.assertIsNotNone(main_element, "Main element should be present in landing page")
    
    def test_heading_hierarchy(self):
        """Test proper heading hierarchy (h1 -> h2 -> h3)"""
        response = self.client.get('/')
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Check for h1
        h1_elements = soup.find_all('h1')
        self.assertEqual(len(h1_elements), 1, "Should have exactly one h1 element")
        self.assertIn('Vedfolnir', h1_elements[0].text)
        
        # Check for h2 elements
        h2_elements = soup.find_all('h2')
        self.assertGreater(len(h2_elements), 0, "Should have h2 elements")
        
        # Check for h3 elements in features
        h3_elements = soup.find_all('h3')
        self.assertGreater(len(h3_elements), 0, "Should have h3 elements for features")
    
    def test_aria_labels_and_landmarks(self):
        """Test ARIA labels and landmarks are properly implemented"""
        response = self.client.get('/')
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Check hero section has aria-labelledby
        hero_section = soup.find('section', class_='landing-hero')
        self.assertIsNotNone(hero_section)
        self.assertEqual(hero_section.get('aria-labelledby'), 'hero-title')
        
        # Check features section has aria-labelledby
        features_section = soup.find('section', class_='features-section')
        self.assertIsNotNone(features_section)
        self.assertEqual(features_section.get('aria-labelledby'), 'features-title')
        
        # Check audience section has aria-labelledby
        audience_section = soup.find('section', class_='audience-section')
        self.assertIsNotNone(audience_section)
        self.assertEqual(audience_section.get('aria-labelledby'), 'audience-title')
    
    def test_cta_buttons_accessibility(self):
        """Test CTA buttons have proper accessibility attributes"""
        response = self.client.get('/')
        soup = BeautifulSoup(response.data, 'html.parser')
        
        cta_buttons = soup.find_all('a', class_='cta-button')
        self.assertGreater(len(cta_buttons), 0, "Should have CTA buttons")
        
        for button in cta_buttons:
            self.assertEqual(button.get('role'), 'button')
            self.assertIsNotNone(button.get('aria-label'))
            self.assertIn('href', button.attrs)
    
    def test_feature_cards_accessibility(self):
        """Test feature cards have proper accessibility attributes"""
        response = self.client.get('/')
        soup = BeautifulSoup(response.data, 'html.parser')
        
        feature_cards = soup.find_all('article', class_='feature-card')
        self.assertEqual(len(feature_cards), 3, "Should have 3 feature cards")
        
        for i, card in enumerate(feature_cards, 1):
            self.assertEqual(card.get('role'), 'article')
            self.assertEqual(card.get('tabindex'), '0')
            self.assertEqual(card.get('aria-labelledby'), f'feature-{i}-title')
            
            # Check icon has proper role and aria-label
            icon_div = card.find('div', class_='feature-icon')
            self.assertIsNotNone(icon_div)
            self.assertEqual(icon_div.get('role'), 'img')
            self.assertIsNotNone(icon_div.get('aria-label'))
            
            # Check icon has aria-hidden
            icon = icon_div.find('i')
            self.assertEqual(icon.get('aria-hidden'), 'true')
    
    def test_audience_items_accessibility(self):
        """Test audience items have proper accessibility attributes"""
        response = self.client.get('/')
        soup = BeautifulSoup(response.data, 'html.parser')
        
        audience_items = soup.find_all('article', class_='audience-item')
        self.assertEqual(len(audience_items), 5, "Should have 5 audience items")
        
        for i, item in enumerate(audience_items, 1):
            self.assertEqual(item.get('role'), 'listitem')
            self.assertEqual(item.get('tabindex'), '0')
            self.assertEqual(item.get('aria-labelledby'), f'audience-{i}-title')
            
            # Check icon has proper role and aria-label
            icon_div = item.find('div', class_='audience-icon')
            self.assertIsNotNone(icon_div)
            self.assertEqual(icon_div.get('role'), 'img')
            self.assertIsNotNone(icon_div.get('aria-label'))
    
    def test_live_region_present(self):
        """Test ARIA live region is present for dynamic announcements"""
        response = self.client.get('/')
        soup = BeautifulSoup(response.data, 'html.parser')
        
        live_region = soup.find(id='live-region')
        self.assertIsNotNone(live_region, "ARIA live region should be present")
        self.assertEqual(live_region.get('aria-live'), 'polite')
        self.assertEqual(live_region.get('aria-atomic'), 'true')
        self.assertIn('sr-only', live_region.get('class', []))
    
    def test_logo_alt_text(self):
        """Test logo has proper alt text"""
        response = self.client.get('/')
        soup = BeautifulSoup(response.data, 'html.parser')
        
        logo_img = soup.find('img', class_='navbar-logo')
        if logo_img:  # Logo might not be present if image fails to load
            self.assertIsNotNone(logo_img.get('alt'))
            self.assertIn('Vedfolnir', logo_img.get('alt'))
            self.assertEqual(logo_img.get('role'), 'img')
    
    def test_color_contrast_css_classes(self):
        """Test that CSS includes high contrast mode support"""
        # Read the landing page template to check for high contrast CSS
        with open('templates/landing.html', 'r') as f:
            content = f.read()
        
        self.assertIn('@media (prefers-contrast: high)', content)
        self.assertIn('prefers-reduced-motion: reduce', content)
    
    def test_keyboard_navigation_attributes(self):
        """Test elements have proper keyboard navigation attributes"""
        response = self.client.get('/')
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Check interactive elements have tabindex
        interactive_elements = soup.find_all(['article'], class_=['feature-card', 'audience-item'])
        for element in interactive_elements:
            self.assertEqual(element.get('tabindex'), '0')
    
    def test_semantic_html_structure(self):
        """Test proper semantic HTML structure"""
        response = self.client.get('/')
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Check for main element
        main_element = soup.find('main')
        self.assertIsNotNone(main_element, "Should have main element")
        
        # Check for section elements
        sections = soup.find_all('section')
        self.assertGreater(len(sections), 0, "Should have section elements")
        
        # Check for article elements
        articles = soup.find_all('article')
        self.assertGreater(len(articles), 0, "Should have article elements")
    
    def test_screen_reader_descriptions(self):
        """Test screen reader specific descriptions are present"""
        response = self.client.get('/')
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Check for sr-only elements
        sr_only_elements = soup.find_all(class_='sr-only')
        self.assertGreater(len(sr_only_elements), 0, "Should have screen reader only content")
        
        # Check CTA description
        cta_description = soup.find(id='cta-description')
        self.assertIsNotNone(cta_description)
        self.assertIn('sr-only', cta_description.get('class', []))
    
    def test_touch_target_sizes(self):
        """Test that CSS includes proper touch target sizes for mobile"""
        # Read the landing page template to check for touch target CSS
        with open('templates/landing.html', 'r') as f:
            content = f.read()
        
        self.assertIn('min-height: 48px', content)
        self.assertIn('min-width: 120px', content)
        self.assertIn('touch-action: manipulation', content)
    
    def test_focus_indicators(self):
        """Test that CSS includes proper focus indicators"""
        # Read the landing page template to check for focus CSS
        with open('templates/landing.html', 'r') as f:
            content = f.read()
        
        self.assertIn('focus-visible', content)
        self.assertIn('focus-within', content)
        self.assertIn('outline:', content)


if __name__ == '__main__':
    unittest.main()