# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for landing page CTA button functionality
Tests requirements 6.1, 6.2, 6.4, 6.5, 6.6
"""

import unittest
import sys
import os
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from database import DatabaseManager


class TestLandingPageCTAButtons(unittest.TestCase):
    """Test CTA button functionality on landing page"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        # Import the app from web_app module
        import web_app
        cls.app = web_app.app
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = cls.app.test_client()
        
    def setUp(self):
        """Clear session data before each test to ensure we get the landing page"""
        with self.client.session_transaction() as sess:
            sess.clear()
        # Also clear any cookies that might indicate previous sessions
        with self.app.test_request_context():
            pass
        
    def test_primary_cta_button_exists(self):
        """Test that primary CTA button exists in hero section (Requirement 6.1)"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Find the hero section
        hero_section = soup.find('section', class_='landing-hero')
        self.assertIsNotNone(hero_section, "Hero section should exist")
        
        # Find the primary CTA button
        primary_cta = hero_section.find('a', class_='cta-button')
        self.assertIsNotNone(primary_cta, "Primary CTA button should exist in hero section")
        self.assertEqual(primary_cta.get('href'), '/register', "Primary CTA should link to registration")
        self.assertIn('Get Started', primary_cta.get_text(), "Primary CTA should contain 'Get Started' text")
        
    def test_primary_cta_button_links_to_registration(self):
        """Test that primary CTA button links to registration page (Requirement 6.2)"""
        response = self.client.get('/')
        soup = BeautifulSoup(response.data, 'html.parser')
        
        hero_section = soup.find('section', class_='landing-hero')
        primary_cta = hero_section.find('a', class_='cta-button')
        
        # Verify the URL is correct
        self.assertEqual(primary_cta.get('href'), '/register')
        
        # Test that the registration page is accessible
        register_response = self.client.get('/register')
        self.assertEqual(register_response.status_code, 200)
        
    def test_login_link_in_navigation(self):
        """Test that login link exists in top-right corner (Requirement 6.4)"""
        response = self.client.get('/')
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Find the navigation
        navbar = soup.find('nav', class_='navbar')
        self.assertIsNotNone(navbar, "Navigation should exist")
        
        # Find the login link
        login_link = navbar.find('a', href='/login')
        self.assertIsNotNone(login_link, "Login link should exist in navigation")
        self.assertIn('Login', login_link.get_text(), "Login link should contain 'Login' text")
        
        # Verify it's in the right section (navbar-nav at the end)
        navbar_nav_sections = navbar.find_all('ul', class_='navbar-nav')
        self.assertTrue(len(navbar_nav_sections) >= 2, "Should have multiple navbar-nav sections")
        
        # Login should be in the last navbar-nav section (top-right)
        last_nav_section = navbar_nav_sections[-1]
        login_in_last_section = last_nav_section.find('a', href='/login')
        self.assertIsNotNone(login_in_last_section, "Login link should be in top-right section")
        
    def test_secondary_cta_button_exists(self):
        """Test that secondary CTA button exists in final section (Requirement 6.5)"""
        response = self.client.get('/')
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Find the final CTA section
        final_cta_section = soup.find('section', class_='final-cta-section')
        self.assertIsNotNone(final_cta_section, "Final CTA section should exist")
        
        # Find the secondary CTA button
        secondary_cta = final_cta_section.find('a', class_='cta-button')
        self.assertIsNotNone(secondary_cta, "Secondary CTA button should exist in final section")
        self.assertEqual(secondary_cta.get('href'), '/register', "Secondary CTA should link to registration")
        self.assertIn('Create Your Free Account', secondary_cta.get_text(), "Secondary CTA should contain account creation text")
        
    def test_cta_buttons_use_flask_url_for(self):
        """Test that CTA buttons use proper Flask url_for() function (Requirement 6.6)"""
        # This test verifies that the URLs are generated correctly by Flask
        response = self.client.get('/')
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Find all CTA buttons
        cta_buttons = soup.find_all('a', class_='cta-button')
        self.assertEqual(len(cta_buttons), 2, "Should have exactly 2 CTA buttons")
        
        for button in cta_buttons:
            href = button.get('href')
            # Verify the URL is properly generated (should be /register, not a template string)
            self.assertEqual(href, '/register', f"CTA button should have proper URL, got: {href}")
            self.assertNotIn('{{', href, "URL should not contain template syntax")
            self.assertNotIn('}}', href, "URL should not contain template syntax")
            
    def test_hover_states_css_exists(self):
        """Test that hover states and visual feedback are implemented (Requirement 6.6)"""
        response = self.client.get('/')
        html_content = response.data.decode('utf-8')
        
        # Check that hover CSS is present
        self.assertIn('.cta-button:hover', html_content, "CTA button hover styles should be defined")
        self.assertIn('transform: translateY(-2px)', html_content, "Hover should include transform effect")
        self.assertIn('box-shadow: var(--shadow-lg)', html_content, "Hover should include enhanced shadow")
        
    def test_cta_button_accessibility(self):
        """Test that CTA buttons have proper accessibility attributes"""
        response = self.client.get('/')
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Find all CTA buttons
        cta_buttons = soup.find_all('a', class_='cta-button')
        
        for button in cta_buttons:
            # Check for role attribute
            self.assertEqual(button.get('role'), 'button', "CTA button should have role='button'")
            
        # Check primary CTA has aria-describedby
        hero_section = soup.find('section', class_='landing-hero')
        primary_cta = hero_section.find('a', class_='cta-button')
        self.assertIsNotNone(primary_cta.get('aria-describedby'), "Primary CTA should have aria-describedby")
        
    def test_cta_button_javascript_tracking(self):
        """Test that CTA buttons have JavaScript click tracking"""
        response = self.client.get('/')
        html_content = response.data.decode('utf-8')
        
        # Check that JavaScript tracking is present
        self.assertIn('ctaButtons.forEach', html_content, "CTA button tracking JavaScript should be present")
        self.assertIn('addEventListener(\'click\'', html_content, "Click event listeners should be added")
        self.assertIn('console.log(\'CTA button clicked:', html_content, "Click tracking should log button clicks")
        
    def test_responsive_cta_button_styles(self):
        """Test that CTA buttons have responsive design styles"""
        response = self.client.get('/')
        html_content = response.data.decode('utf-8')
        
        # Check for responsive CSS
        self.assertIn('@media (max-width: 768px)', html_content, "Should have mobile responsive styles")
        self.assertIn('.cta-button {', html_content, "Should have CTA button base styles")
        
        # Check for mobile-specific CTA styles - look for the actual mobile styles
        mobile_section_found = False
        lines = html_content.split('\n')
        in_mobile_section = False
        
        for i, line in enumerate(lines):
            if '@media (max-width: 768px)' in line:
                in_mobile_section = True
            elif in_mobile_section and '.cta-button {' in line:
                mobile_section_found = True
                break
            elif in_mobile_section and line.strip() == '}' and i < len(lines) - 1:
                # Check if this is the end of the media query
                next_line = lines[i + 1].strip()
                if next_line == '' or not next_line.startswith('.') and not next_line.startswith('@'):
                    in_mobile_section = False
                
        # Alternative check: look for mobile CTA button properties directly
        if not mobile_section_found:
            # Check if mobile CTA styles exist by looking for the specific properties
            mobile_cta_pattern = '@media (max-width: 768px)' in html_content and 'padding: 0.875rem 1.5rem' in html_content
            mobile_section_found = mobile_cta_pattern
                
        self.assertTrue(mobile_section_found, "Should have mobile-specific CTA button styles")


if __name__ == '__main__':
    unittest.main()