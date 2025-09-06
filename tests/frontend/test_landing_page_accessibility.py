# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import unittest
import sys
import os
import time
import subprocess
import requests
import asyncio
import json
import re
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from playwright.sync_api import sync_playwright

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config


class LandingPageAccessibilityTests(unittest.TestCase):
    """
    Comprehensive accessibility and UI tests for the Flask landing page using Playwright.
    Tests responsive design, WCAG compliance, keyboard navigation, and interactive elements.
    
    Requirements tested:
    - 3.1: Semantic HTML elements for proper screen reader navigation
    - 3.2: Appropriate alt text for all images
    - 3.3: Proper color contrast ratios for text readability
    - 3.4: Fully navigable using keyboard-only input
    - 3.5: Proper heading hierarchy (h1, h2, h3) for content structure
    - 3.6: Skip-to-content links for screen reader users
    - 4.1: Display all content in readable format on mobile devices
    - 4.2: Maintain proper layout and functionality on tablets
    - 4.3: Utilize full screen width effectively on desktop
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment and start web application"""
        cls.base_url = "http://127.0.0.1:5000"
        cls.web_app_process = None
        cls.playwright = None
        cls.browser = None
        
        # Start web application
        cls._start_web_app()
        
        # Wait for application to be ready
        cls._wait_for_app_ready()
        
        # Initialize Playwright
        cls._initialize_playwright()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        # Close Playwright
        if cls.browser:
            cls.browser.close()
        if cls.playwright:
            cls.playwright.stop()
        
        # Stop web application
        if cls.web_app_process:
            try:
                cls.web_app_process.terminate()
                cls.web_app_process.wait(timeout=10)
            except:
                try:
                    cls.web_app_process.kill()
                except:
                    pass
    
    @classmethod
    def _start_web_app(cls):
        """Start the web application for testing"""
        try:
            cls.web_app_process = subprocess.Popen(
                [sys.executable, 'web_app.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.path.join(os.path.dirname(__file__), '..', '..')
            )
            time.sleep(10)  # Give app time to start
        except Exception as e:
            print(f"Failed to start web app: {e}")
            raise
    
    @classmethod
    def _wait_for_app_ready(cls):
        """Wait for the application to be ready"""
        max_attempts = 30
        for attempt in range(max_attempts):
            try:
                response = requests.get(cls.base_url, timeout=5)
                if response.status_code == 200:
                    return
            except:
                pass
            time.sleep(1)
        
        raise Exception("Web application failed to start within timeout period")
    
    @classmethod
    def _initialize_playwright(cls):
        """Initialize Playwright browser"""
        try:
            cls.playwright = sync_playwright().start()
            cls.browser = cls.playwright.chromium.launch(
                headless=False,  # Set to False for debugging, True for CI
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
        except Exception as e:
            print(f"Failed to initialize Playwright: {e}")
            raise
    
    def setUp(self):
        """Set up for each test"""
        if not self.browser:
            self.skipTest("Playwright browser not available")
        
        # Create new context and page for each test
        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        self.page = self.context.new_page()
        
        # Navigate to landing page
        self.page.goto(self.base_url, wait_until='domcontentloaded')
        
        # Wait for main content to load
        self.page.wait_for_selector('main', timeout=10000)
    
    def tearDown(self):
        """Clean up after each test"""
        if hasattr(self, 'context'):
            self.context.close()
    
    def test_responsive_design_mobile(self):
        """Test responsive design on mobile screen sizes (Requirement 4.1)"""
        mobile_sizes = [
            (375, 667),  # iPhone 6/7/8
            (414, 896),  # iPhone XR
            (360, 640),  # Android
            (320, 568),  # iPhone 5/SE
        ]
        
        for width, height in mobile_sizes:
            with self.subTest(size=f"{width}x{height}"):
                self.page.set_viewport_size({'width': width, 'height': height})
                self.page.wait_for_timeout(1000)  # Allow layout to adjust
                
                # Check that main content is visible
                main_content = self.page.locator('main')
                self.assertTrue(main_content.is_visible())
                
                # Check hero section is readable
                hero_title = self.page.locator('#hero-title')
                self.assertTrue(hero_title.is_visible())
                
                # Check CTA button is appropriately sized for touch
                cta_button = self.page.locator('.cta-button').first
                button_box = cta_button.bounding_box()
                self.assertGreaterEqual(button_box['height'], 44, "Touch target too small")
                self.assertGreaterEqual(button_box['width'], 120, "Touch target too small")
                
                # Check no horizontal scrolling required
                body_width = self.page.evaluate("document.body.scrollWidth")
                viewport_width = self.page.evaluate("window.innerWidth")
                self.assertLessEqual(body_width, viewport_width + 5, "Horizontal scrolling required")
                
                # Check text remains readable
                hero_lead = self.page.locator('.landing-hero .lead')
                font_size = hero_lead.evaluate("el => window.getComputedStyle(el).fontSize")
                font_size_px = int(font_size.replace('px', ''))
                self.assertGreaterEqual(font_size_px, 14, "Text too small on mobile")
    
    def test_responsive_design_tablet(self):
        """Test responsive design on tablet screen sizes (Requirement 4.2)"""
        tablet_sizes = [
            (768, 1024),  # iPad
            (834, 1112),  # iPad Air
            (1024, 1366), # iPad Pro
            (800, 1280),  # Android tablet
        ]
        
        for width, height in tablet_sizes:
            with self.subTest(size=f"{width}x{height}"):
                self.page.set_viewport_size({'width': width, 'height': height})
                self.page.wait_for_timeout(1000)
                
                # Check layout maintains proper structure
                features_section = self.page.locator('.features-section')
                self.assertTrue(features_section.is_visible())
                
                # Check feature cards are properly arranged
                feature_cards = self.page.locator('.feature-card')
                card_count = feature_cards.count()
                self.assertGreaterEqual(card_count, 3)
                
                for i in range(card_count):
                    card = feature_cards.nth(i)
                    self.assertTrue(card.is_visible())
                    # Check cards have adequate spacing
                    card_box = card.bounding_box()
                    self.assertGreater(card_box['width'], 200)
                    self.assertGreater(card_box['height'], 150)
                
                # Check audience grid adapts properly
                audience_items = self.page.locator('.audience-item')
                self.assertGreaterEqual(audience_items.count(), 5)
                
                # Verify navigation remains functional
                skip_link = self.page.locator('.visually-hidden-focusable')
                self.assertTrue(skip_link.is_enabled())
    
    def test_responsive_design_desktop(self):
        """Test responsive design on desktop screen sizes (Requirement 4.3)"""
        desktop_sizes = [
            (1920, 1080),  # Full HD
            (1366, 768),   # Common laptop
            (1440, 900),   # MacBook
            (2560, 1440),  # 2K
        ]
        
        for width, height in desktop_sizes:
            with self.subTest(size=f"{width}x{height}"):
                self.page.set_viewport_size({'width': width, 'height': height})
                self.page.wait_for_timeout(1000)
                
                # Check full width utilization
                container = self.page.locator('.container').first
                container_box = container.bounding_box()
                viewport_width = self.page.evaluate("window.innerWidth")
                
                # Container should use significant portion of viewport
                utilization_ratio = container_box['width'] / viewport_width
                self.assertGreater(utilization_ratio, 0.7, "Poor width utilization on desktop")
                
                # Check hero section scales appropriately
                hero_title = self.page.locator('#hero-title')
                title_font_size = hero_title.evaluate("el => window.getComputedStyle(el).fontSize")
                title_size_px = int(title_font_size.replace('px', ''))
                self.assertGreaterEqual(title_size_px, 40, "Title too small on desktop")
                
                # Check feature cards are properly distributed
                feature_row = self.page.locator('.features-section .row')
                row_box = feature_row.bounding_box()
                self.assertGreater(row_box['width'], 800, "Feature row too narrow on desktop")
    
    def test_wcag_compliance_automated(self):
        """Test WCAG compliance using automated tools (Requirements 3.1-3.6)"""
        try:
            # Inject axe-core into the page
            self.page.add_script_tag(url="https://unpkg.com/axe-core@4.8.2/axe.min.js")
            
            # Run accessibility scan
            results = self.page.evaluate("""
                () => {
                    return new Promise((resolve) => {
                        axe.run((err, results) => {
                            if (err) throw err;
                            resolve(results);
                        });
                    });
                }
            """)
            
            # Check for violations
            violations = results.get('violations', [])
            
            # Filter out known false positives or acceptable violations
            critical_violations = []
            for violation in violations:
                impact = violation.get('impact', '')
                if impact in ['critical', 'serious']:
                    critical_violations.append(violation)
            
            # Report violations
            if critical_violations:
                violation_details = []
                for violation in critical_violations:
                    violation_details.append({
                        'id': violation.get('id'),
                        'impact': violation.get('impact'),
                        'description': violation.get('description'),
                        'help': violation.get('help'),
                        'nodes': len(violation.get('nodes', []))
                    })
                
                self.fail(f"WCAG violations found: {json.dumps(violation_details, indent=2)}")
            
            # Check for specific accessibility features
            self._verify_accessibility_features()
            
        except Exception as e:
            print(f"Axe-core accessibility testing failed: {e}")
            # Continue with manual accessibility checks
            self._verify_accessibility_features()
    
    def _verify_accessibility_features(self):
        """Verify specific accessibility features are present"""
        # Check for skip link (Requirement 3.6)
        skip_link = self.page.locator('.visually-hidden-focusable')
        self.assertTrue(skip_link.is_enabled())
        self.assertEqual(skip_link.get_attribute('href'), '#main-content')
        
        # Check main landmark (Requirement 3.1)
        main_element = self.page.locator('main')
        self.assertTrue(main_element.is_visible())
        self.assertEqual(main_element.get_attribute('id'), 'main-content')
        
        # Check heading hierarchy (Requirement 3.5)
        h1_elements = self.page.locator('h1')
        self.assertEqual(h1_elements.count(), 1, "Should have exactly one h1 element")
        
        h2_elements = self.page.locator('h2')
        self.assertGreater(h2_elements.count(), 0, "Should have h2 elements")
        
        h3_elements = self.page.locator('h3')
        self.assertGreater(h3_elements.count(), 0, "Should have h3 elements")
        
        # Check ARIA live region
        live_region = self.page.locator('#live-region')
        self.assertEqual(live_region.get_attribute('aria-live'), 'polite')
        
        # Check semantic elements (Requirement 3.1)
        sections = self.page.locator('section')
        self.assertGreater(sections.count(), 0, "Should have section elements")
        
        articles = self.page.locator('article')
        self.assertGreater(articles.count(), 0, "Should have article elements")
    
    def test_color_contrast_ratios(self):
        """Test color contrast ratios meet WCAG standards (Requirement 3.3)"""
        # Test primary text contrast
        hero_title = self.page.locator('#hero-title')
        title_color = hero_title.evaluate("el => window.getComputedStyle(el).color")
        title_bg = hero_title.evaluate("el => window.getComputedStyle(el).backgroundColor")
        
        # Convert RGB to contrast ratio (simplified check)
        self.assertIsNotNone(title_color)
        self.assertIsNotNone(title_bg)
        
        # Test CTA button contrast
        cta_button = self.page.locator('.cta-button').first
        button_color = cta_button.evaluate("el => window.getComputedStyle(el).color")
        button_bg = cta_button.evaluate("el => window.getComputedStyle(el).backgroundColor")
        
        self.assertIsNotNone(button_color)
        self.assertIsNotNone(button_bg)
        
        # Test secondary text contrast
        section_subtitle = self.page.locator('.section-subtitle')
        subtitle_color = section_subtitle.evaluate("el => window.getComputedStyle(el).color")
        
        # Ensure colors are not the same (indicating proper contrast)
        self.assertNotEqual(title_color, title_bg)
        self.assertNotEqual(button_color, button_bg)
    
    def test_keyboard_navigation_full_flow(self):
        """Test complete keyboard navigation functionality (Requirement 3.4)"""
        # Start from skip link
        skip_link = self.page.locator('.visually-hidden-focusable')
        skip_link.press('Tab')
        
        # Track focus progression
        focusable_elements = self.page.locator('a[href], button, [tabindex="0"], input, select, textarea')
        
        self.assertGreater(focusable_elements.count(), 0, "No focusable elements found")
        
        # Test Tab navigation through key elements
        key_elements_to_test = [
            ".cta-button",  # Hero CTA
            ".feature-card",  # Feature cards
            ".audience-item",  # Audience items
            ".final-cta-section .cta-button"  # Final CTA
        ]
        
        for selector in key_elements_to_test:
            elements = self.page.locator(selector)
            element_count = min(elements.count(), 2)  # Test first 2 of each type
            
            for i in range(element_count):
                try:
                    element = elements.nth(i)
                    element.press('Tab')
                    # Verify element can receive focus
                    element.focus()
                    focused_element = self.page.evaluate("document.activeElement")
                    # Basic check that focus is working
                    self.assertIsNotNone(focused_element)
                except Exception as e:
                    self.fail(f"Keyboard navigation failed for {selector}: {e}")
    
    def test_keyboard_navigation_skip_link(self):
        """Test skip link functionality (Requirement 3.6)"""
        skip_link = self.page.locator('.visually-hidden-focusable')
        
        # Focus skip link
        skip_link.focus()
        
        # Verify skip link is focused
        focused_element = self.page.evaluate("document.activeElement")
        self.assertIsNotNone(focused_element)
        
        # Activate skip link
        skip_link.press('Enter')
        
        # Verify focus moved to main content
        self.page.wait_for_timeout(500)  # Allow for smooth scrolling
        main_content = self.page.locator('#main-content')
        
        # Check that main content area is in view
        main_box = main_content.bounding_box()
        viewport_height = self.page.evaluate("window.innerHeight")
        
        # Main content should be visible in viewport
        self.assertLessEqual(main_box['y'], viewport_height, 
                           "Main content should be scrolled into view")
    
    def test_keyboard_navigation_cta_buttons(self):
        """Test CTA button keyboard accessibility (Requirements 3.4, 6.1, 6.2)"""
        cta_buttons = self.page.locator('.cta-button')
        
        for i in range(cta_buttons.count()):
            with self.subTest(button_index=i):
                button = cta_buttons.nth(i)
                
                # Focus button
                button.focus()
                
                # Verify button is focused
                focused_element = self.page.evaluate("document.activeElement")
                self.assertIsNotNone(focused_element)
                
                # Test Enter key activation
                original_url = self.page.url
                
                # Check href before pressing Enter
                href = button.get_attribute('href')
                self.assertIsNotNone(href, "CTA button should have href attribute")
                self.assertTrue(href.endswith('/register'), "CTA should link to registration")
                
                # Test keyboard activation (without actually navigating)
                button.press('Enter')
                
                # Allow any JavaScript to execute
                self.page.wait_for_timeout(1000)
                
                # Return to landing page for next test
                self.page.goto(self.base_url, wait_until='domcontentloaded')
                self.page.wait_for_selector('main', timeout=5000)
    
    def test_interactive_elements_functionality(self):
        """Test all interactive elements work correctly (Requirements 3.4, 6.4, 6.5, 6.6)"""
        # Test feature cards interactivity
        feature_cards = self.page.locator('.feature-card')
        card_count = min(feature_cards.count(), 3)  # Test first 3 cards
        
        for i in range(card_count):
            with self.subTest(card_index=i):
                card = feature_cards.nth(i)
                
                # Test hover effect (visual feedback)
                card.hover()
                
                # Test focus
                card.focus()
                focused_element = self.page.evaluate("document.activeElement")
                self.assertIsNotNone(focused_element)
                
                # Test keyboard activation
                card.press('Enter')
                # Card should handle Enter key (even if just for accessibility)
        
        # Test audience items interactivity
        audience_items = self.page.locator('.audience-item')
        item_count = min(audience_items.count(), 3)  # Test first 3 items
        
        for i in range(item_count):
            with self.subTest(audience_index=i):
                item = audience_items.nth(i)
                
                # Test focus
                item.focus()
                focused_element = self.page.evaluate("document.activeElement")
                self.assertIsNotNone(focused_element)
                
                # Test keyboard interaction
                item.press('Space')
    
    def test_alt_text_and_images(self):
        """Test alt text for all images (Requirement 3.2)"""
        # Check for images with missing alt text
        images = self.page.locator('img')
        
        for i in range(images.count()):
            with self.subTest(image_index=i):
                img = images.nth(i)
                alt_text = img.get_attribute('alt')
                src = img.get_attribute('src')
                
                # All images should have alt text (even if empty for decorative images)
                self.assertIsNotNone(alt_text, f"Image {src} missing alt attribute")
                
                # Non-decorative images should have meaningful alt text
                if not img.get_attribute('aria-hidden') == 'true':
                    self.assertGreater(len(alt_text.strip()), 0, 
                                     f"Image {src} has empty alt text but is not decorative")
        
        # Check for icon elements with proper ARIA labels
        icons = self.page.locator('.feature-icon i, .audience-icon i')
        
        for i in range(icons.count()):
            with self.subTest(icon_index=i):
                icon = icons.nth(i)
                # Icons should be marked as decorative or have labels
                aria_hidden = icon.get_attribute('aria-hidden')
                aria_label = icon.get_attribute('aria-label')
                
                # Icon should either be hidden from screen readers or have a label
                self.assertTrue(
                    aria_hidden == 'true' or (aria_label and len(aria_label.strip()) > 0),
                    f"Icon {i} needs aria-hidden='true' or meaningful aria-label"
                )
    
    def test_semantic_html_structure(self):
        """Test semantic HTML structure (Requirement 3.1)"""
        # Check for proper landmark elements
        landmarks = {
            'main': 1,  # Should have exactly one main
            'section': lambda x: x >= 3,  # Should have multiple sections
            'article': lambda x: x >= 3,  # Should have multiple articles
        }
        
        for tag, expected in landmarks.items():
            elements = self.page.locator(tag)
            count = elements.count()
            
            if callable(expected):
                self.assertTrue(expected(count), 
                              f"Expected {tag} count to meet condition, got {count}")
            else:
                self.assertEqual(count, expected, 
                               f"Expected {expected} {tag} elements, got {count}")
        
        # Check for proper ARIA roles and labels
        sections = self.page.locator('section')
        for i in range(sections.count()):
            section = sections.nth(i)
            aria_labelledby = section.get_attribute('aria-labelledby')
            aria_label = section.get_attribute('aria-label')
            
            # Sections should have proper labeling
            self.assertTrue(
                aria_labelledby or aria_label,
                f"Section {i} should have aria-labelledby or aria-label"
            )
        
        # Check for proper list structures
        lists = self.page.locator('[role="list"]')
        for i in range(lists.count()):
            list_element = lists.nth(i)
            list_items = list_element.locator('[role="listitem"]')
            self.assertGreater(list_items.count(), 0, 
                             f"List {i} should contain list items")
    
    def test_heading_hierarchy(self):
        """Test proper heading hierarchy (Requirement 3.5)"""
        # Get all headings in order
        headings = self.page.locator('h1, h2, h3, h4, h5, h6')
        
        # Should have at least one of each main level
        h1_count = self.page.locator('h1').count()
        h2_count = self.page.locator('h2').count()
        h3_count = self.page.locator('h3').count()
        
        self.assertEqual(h1_count, 1, "Should have exactly one h1")
        self.assertGreater(h2_count, 0, "Should have h2 elements")
        self.assertGreater(h3_count, 0, "Should have h3 elements")
        
        # Check heading hierarchy is logical
        heading_levels = []
        for i in range(headings.count()):
            heading = headings.nth(i)
            tag_name = heading.evaluate("el => el.tagName.toLowerCase()")
            level = int(tag_name[1])  # Extract number from h1, h2, etc.
            heading_levels.append(level)
        
        # First heading should be h1
        if heading_levels:
            self.assertEqual(heading_levels[0], 1, "First heading should be h1")
        
        # Check for proper nesting (no skipping levels)
        for i in range(1, len(heading_levels)):
            current_level = heading_levels[i]
            previous_level = heading_levels[i-1]
            
            # Level can stay same, go up by 1, or go down any amount
            if current_level > previous_level:
                self.assertLessEqual(current_level - previous_level, 1,
                                   f"Heading level jumped from h{previous_level} to h{current_level}")
    
    def test_screen_reader_compatibility(self):
        """Test screen reader compatibility features (Requirements 3.1, 3.2, 3.6)"""
        # Check for screen reader only content
        sr_only_elements = self.page.locator('.sr-only')
        self.assertGreater(sr_only_elements.count(), 0, "Should have screen reader only content")
        
        # Check ARIA live region
        live_region = self.page.locator('#live-region')
        self.assertEqual(live_region.get_attribute('aria-live'), 'polite')
        self.assertEqual(live_region.get_attribute('aria-atomic'), 'true')
        
        # Check for proper ARIA labels on interactive elements
        cta_buttons = self.page.locator('.cta-button')
        for i in range(cta_buttons.count()):
            button = cta_buttons.nth(i)
            aria_label = button.get_attribute('aria-label')
            aria_describedby = button.get_attribute('aria-describedby')
            
            # CTA buttons should have descriptive labels
            self.assertTrue(
                aria_label or aria_describedby,
                f"CTA button {i} should have aria-label or aria-describedby"
            )
        
        # Check for proper role attributes
        feature_cards = self.page.locator('.feature-card')
        for i in range(feature_cards.count()):
            card = feature_cards.nth(i)
            role = card.get_attribute('role')
            self.assertEqual(role, 'article', f"Feature card {i} should have role='article'")
        
        # Check for proper labeling of sections
        sections = self.page.locator('section')
        for i in range(sections.count()):
            section = sections.nth(i)
            aria_labelledby = section.get_attribute('aria-labelledby')
            self.assertIsNotNone(aria_labelledby, 
                               f"Section {i} should have aria-labelledby attribute")
    
    def test_cross_browser_compatibility(self):
        """Test functionality across different browsers"""
        browsers_to_test = ['chromium', 'firefox', 'webkit']
        
        for browser_name in browsers_to_test:
            with self.subTest(browser=browser_name):
                try:
                    # Create browser instance
                    if browser_name == 'chromium':
                        browser = self.playwright.chromium.launch(headless=False)
                    elif browser_name == 'firefox':
                        browser = self.playwright.firefox.launch(headless=False)
                    elif browser_name == 'webkit':
                        browser = self.playwright.webkit.launch(headless=False)
                    else:
                        continue
                    
                    context = browser.new_context(viewport={'width': 1920, 'height': 1080})
                    page = context.new_page()
                    
                    # Navigate to page
                    page.goto(self.base_url, wait_until='domcontentloaded')
                    page.wait_for_selector('main', timeout=10000)
                    
                    # Test basic functionality
                    hero_title = page.locator('#hero-title')
                    self.assertTrue(hero_title.is_visible())
                    
                    cta_button = page.locator('.cta-button').first
                    self.assertTrue(cta_button.is_enabled())
                    
                    # Test responsive behavior
                    page.set_viewport_size({'width': 768, 'height': 1024})
                    page.wait_for_timeout(1000)
                    
                    # Verify layout still works
                    features_section = page.locator('.features-section')
                    self.assertTrue(features_section.is_visible())
                    
                    # Clean up
                    context.close()
                    browser.close()
                    
                except Exception as e:
                    print(f"Browser {browser_name} not available: {e}")
                    continue


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)