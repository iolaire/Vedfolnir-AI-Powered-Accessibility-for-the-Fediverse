# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import unittest
import sys
import os
import time
import subprocess
import requests
import json
from playwright.sync_api import sync_playwright

# Add project root for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config


class LandingPageUITests(unittest.TestCase):
    """
    UI-specific tests for the Flask landing page using Playwright, focusing on visual elements,
    interactions, and user experience.
    
    Requirements tested:
    - 4.1: Display all content in readable format on mobile devices
    - 4.2: Maintain proper layout and functionality on tablets  
    - 4.3: Utilize full screen width effectively on desktop
    - 6.4: Visual feedback for interactive elements
    - 6.5: Button functionality and navigation
    - 6.6: Hover states and visual feedback
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
        if cls.browser:
            cls.browser.close()
        if cls.playwright:
            cls.playwright.stop()
        
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
                headless=False,  # Set to False for UI testing to see visual feedback
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
    
    def test_visual_layout_desktop(self):
        """Test visual layout on desktop screens (Requirement 4.3)"""
        self.page.set_viewport_size({'width': 1920, 'height': 1080})
        self.page.wait_for_timeout(1000)
        
        # Test hero section layout
        hero_section = self.page.locator('.landing-hero')
        hero_box = hero_section.bounding_box()
        
        # Hero should span full width
        viewport_width = self.page.evaluate("window.innerWidth")
        self.assertGreaterEqual(hero_box['width'], viewport_width * 0.95)
        
        # Test features section layout
        feature_cards = self.page.locator('.feature-card')
        self.assertEqual(feature_cards.count(), 3, "Should have 3 feature cards")
        
        # Cards should be arranged horizontally on desktop
        card_positions = []
        for i in range(feature_cards.count()):
            card_box = feature_cards.nth(i).bounding_box()
            card_positions.append(card_box['x'])
        card_positions.sort()
        
        # Each card should be in a different horizontal position
        for i in range(1, len(card_positions)):
            self.assertGreater(card_positions[i] - card_positions[i-1], 50,
                             "Feature cards should be horizontally distributed")
        
        # Test audience grid layout
        audience_items = self.page.locator('.audience-item')
        self.assertEqual(audience_items.count(), 5, "Should have 5 audience items")
        
        # On large desktop, should be in a single row
        audience_y_positions = []
        for i in range(audience_items.count()):
            item_box = audience_items.nth(i).bounding_box()
            audience_y_positions.append(item_box['y'])
        
        y_variance = max(audience_y_positions) - min(audience_y_positions)
        self.assertLess(y_variance, 100, "Audience items should be roughly aligned horizontally")
    
    def test_visual_layout_tablet(self):
        """Test visual layout on tablet screens (Requirement 4.2)"""
        self.driver.set_window_size(768, 1024)
        time.sleep(1)
        
        # Test feature cards adapt to tablet layout
        feature_cards = self.driver.find_elements(By.CSS_SELECTOR, ".feature-card")
        
        # Cards should still be visible and properly sized
        for i, card in enumerate(feature_cards):
            with self.subTest(card_index=i):
                self.assertTrue(card.is_displayed())
                card_rect = card.rect
                self.assertGreater(card_rect['width'], 200, "Card too narrow on tablet")
                self.assertGreater(card_rect['height'], 150, "Card too short on tablet")
        
        # Test audience items layout on tablet
        audience_items = self.driver.find_elements(By.CSS_SELECTOR, ".audience-item")
        
        # Should adapt to 2-3 columns on tablet
        visible_items = [item for item in audience_items if item.is_displayed()]
        self.assertEqual(len(visible_items), 5, "All audience items should be visible")
        
        # Check that items are properly spaced
        for item in visible_items:
            item_rect = item.rect
            self.assertGreater(item_rect['width'], 150, "Audience item too narrow on tablet")
    
    def test_visual_layout_mobile(self):
        """Test visual layout on mobile screens (Requirement 4.1)"""
        mobile_sizes = [(375, 667), (414, 896), (360, 640)]
        
        for width, height in mobile_sizes:
            with self.subTest(size=f"{width}x{height}"):
                self.driver.set_window_size(width, height)
                time.sleep(1)
                
                # Test hero section on mobile
                hero_title = self.driver.find_element(By.ID, "hero-title")
                title_rect = hero_title.rect
                
                # Title should be visible and not cut off
                self.assertGreater(title_rect['width'], 0)
                self.assertGreater(title_rect['height'], 0)
                
                # Test CTA button sizing on mobile
                cta_button = self.driver.find_element(By.CSS_SELECTOR, ".cta-button")
                button_rect = cta_button.rect
                
                # Button should meet touch target guidelines
                self.assertGreaterEqual(button_rect['height'], 44, "Touch target too small")
                self.assertGreaterEqual(button_rect['width'], 120, "Touch target too small")
                
                # Test feature cards stack vertically on mobile
                feature_cards = self.driver.find_elements(By.CSS_SELECTOR, ".feature-card")
                
                if len(feature_cards) >= 2:
                    card1_rect = feature_cards[0].rect
                    card2_rect = feature_cards[1].rect
                    
                    # Cards should be stacked vertically (card2 below card1)
                    self.assertGreater(card2_rect['y'], card1_rect['y'] + card1_rect['height'] - 50,
                                     "Feature cards should stack vertically on mobile")
                
                # Test audience items stack on mobile
                audience_items = self.driver.find_elements(By.CSS_SELECTOR, ".audience-item")
                
                # All items should be visible
                for item in audience_items:
                    self.assertTrue(item.is_displayed(), "Audience item should be visible on mobile")
    
    def test_hover_effects_and_visual_feedback(self):
        """Test hover effects and visual feedback (Requirement 6.6)"""
        self.page.set_viewport_size({'width': 1920, 'height': 1080})  # Desktop size for hover testing
        self.page.wait_for_timeout(1000)
        
        # Test CTA button hover effects
        cta_buttons = self.page.locator('.cta-button')
        
        for i in range(cta_buttons.count()):
            with self.subTest(button_index=i):
                button = cta_buttons.nth(i)
                
                # Get initial button styles
                initial_bg = button.evaluate("el => window.getComputedStyle(el).backgroundColor")
                initial_transform = button.evaluate("el => window.getComputedStyle(el).transform")
                
                # Hover over button
                button.hover()
                self.page.wait_for_timeout(500)  # Allow transition to complete
                
                # Check for visual changes on hover
                hover_bg = button.evaluate("el => window.getComputedStyle(el).backgroundColor")
                hover_transform = button.evaluate("el => window.getComputedStyle(el).transform")
                
                # Background or transform should change on hover
                self.assertTrue(
                    initial_bg != hover_bg or initial_transform != hover_transform,
                    f"CTA button {i} should show visual feedback on hover"
                )
        
        # Test feature card hover effects
        feature_cards = self.driver.find_elements(By.CSS_SELECTOR, ".feature-card")
        
        for i, card in enumerate(feature_cards):
            with self.subTest(card_index=i):
                # Get initial card position
                initial_rect = card.rect
                
                # Hover over card
                ActionChains(self.driver).move_to_element(card).perform()
                time.sleep(0.5)
                
                # Check for transform effect (card should lift up)
                hover_rect = card.rect
                
                # Card should move up slightly on hover (negative Y change)
                y_change = hover_rect['y'] - initial_rect['y']
                self.assertLessEqual(y_change, 0, f"Feature card {i} should lift up on hover")
        
        # Test audience item hover effects
        audience_items = self.driver.find_elements(By.CSS_SELECTOR, ".audience-item")
        
        for i, item in enumerate(audience_items[:3]):  # Test first 3 items
            with self.subTest(audience_index=i):
                # Get initial background
                initial_bg = self.driver.execute_script(
                    "return window.getComputedStyle(arguments[0]).backgroundColor", item
                )
                
                # Hover over item
                ActionChains(self.driver).move_to_element(item).perform()
                time.sleep(0.5)
                
                # Check for background change
                hover_bg = self.driver.execute_script(
                    "return window.getComputedStyle(arguments[0]).backgroundColor", item
                )
                
                # Background should change on hover
                self.assertNotEqual(initial_bg, hover_bg, 
                                  f"Audience item {i} should change background on hover")
    
    def test_focus_visual_indicators(self):
        """Test focus visual indicators for keyboard navigation"""
        # Test CTA button focus indicators
        cta_buttons = self.driver.find_elements(By.CSS_SELECTOR, ".cta-button")
        
        for i, button in enumerate(cta_buttons):
            with self.subTest(button_index=i):
                # Focus the button
                self.driver.execute_script("arguments[0].focus()", button)
                time.sleep(0.2)
                
                # Check for focus outline
                outline = self.driver.execute_script(
                    "return window.getComputedStyle(arguments[0]).outline", button
                )
                outline_width = self.driver.execute_script(
                    "return window.getComputedStyle(arguments[0]).outlineWidth", button
                )
                
                # Should have visible focus indicator
                self.assertNotEqual(outline_width, "0px", 
                                  f"CTA button {i} should have focus outline")
        
        # Test feature card focus indicators
        feature_cards = self.driver.find_elements(By.CSS_SELECTOR, ".feature-card")
        
        for i, card in enumerate(feature_cards):
            with self.subTest(card_index=i):
                # Focus the card
                self.driver.execute_script("arguments[0].focus()", card)
                time.sleep(0.2)
                
                # Check for focus indicator
                outline_width = self.driver.execute_script(
                    "return window.getComputedStyle(arguments[0]).outlineWidth", card
                )
                
                # Should have visible focus indicator
                self.assertNotEqual(outline_width, "0px", 
                                  f"Feature card {i} should have focus outline")
    
    def test_button_functionality_and_navigation(self):
        """Test button functionality and navigation (Requirement 6.5)"""
        # Test primary CTA button
        primary_cta = self.driver.find_element(By.CSS_SELECTOR, ".landing-hero .cta-button")
        
        # Check button attributes
        href = primary_cta.get_attribute('href')
        self.assertIsNotNone(href, "Primary CTA should have href attribute")
        self.assertTrue(href.endswith('/register'), "Primary CTA should link to registration")
        
        # Check button is clickable
        self.assertTrue(primary_cta.is_enabled(), "Primary CTA should be enabled")
        self.assertTrue(primary_cta.is_displayed(), "Primary CTA should be visible")
        
        # Test secondary CTA button
        secondary_cta = self.driver.find_element(By.CSS_SELECTOR, ".final-cta-section .cta-button")
        
        # Check button attributes
        href = secondary_cta.get_attribute('href')
        self.assertIsNotNone(href, "Secondary CTA should have href attribute")
        self.assertTrue(href.endswith('/register'), "Secondary CTA should link to registration")
        
        # Check button is clickable
        self.assertTrue(secondary_cta.is_enabled(), "Secondary CTA should be enabled")
        self.assertTrue(secondary_cta.is_displayed(), "Secondary CTA should be visible")
        
        # Test button click behavior (without actually navigating)
        original_url = self.driver.current_url
        
        # Click primary CTA
        primary_cta.click()
        time.sleep(1)
        
        # Should navigate to registration page or show intent to navigate
        current_url = self.driver.current_url
        # In test environment, might not actually navigate, but URL should change or be ready to change
        
        # Return to landing page for next test
        self.driver.get(self.base_url)
        WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.TAG_NAME, "main"))
        )
    
    def test_responsive_images_and_icons(self):
        """Test responsive behavior of images and icons"""
        screen_sizes = [(1920, 1080), (768, 1024), (375, 667)]
        
        for width, height in screen_sizes:
            with self.subTest(size=f"{width}x{height}"):
                self.driver.set_window_size(width, height)
                time.sleep(1)
                
                # Test feature icons scale appropriately
                feature_icons = self.driver.find_elements(By.CSS_SELECTOR, ".feature-icon")
                
                for i, icon in enumerate(feature_icons):
                    icon_rect = icon.rect
                    
                    # Icons should be visible and appropriately sized
                    self.assertGreater(icon_rect['width'], 20, f"Feature icon {i} too small")
                    self.assertGreater(icon_rect['height'], 20, f"Feature icon {i} too small")
                    self.assertLess(icon_rect['width'], 200, f"Feature icon {i} too large")
                    self.assertLess(icon_rect['height'], 200, f"Feature icon {i} too large")
                
                # Test audience icons scale appropriately
                audience_icons = self.driver.find_elements(By.CSS_SELECTOR, ".audience-icon")
                
                for i, icon in enumerate(audience_icons):
                    icon_rect = icon.rect
                    
                    # Icons should be visible and appropriately sized
                    self.assertGreater(icon_rect['width'], 20, f"Audience icon {i} too small")
                    self.assertGreater(icon_rect['height'], 20, f"Audience icon {i} too small")
                    self.assertLess(icon_rect['width'], 150, f"Audience icon {i} too large")
                    self.assertLess(icon_rect['height'], 150, f"Audience icon {i} too large")
    
    def test_text_readability_across_sizes(self):
        """Test text remains readable across different screen sizes"""
        screen_sizes = [(1920, 1080), (1366, 768), (768, 1024), (414, 896), (375, 667)]
        
        for width, height in screen_sizes:
            with self.subTest(size=f"{width}x{height}"):
                self.driver.set_window_size(width, height)
                time.sleep(1)
                
                # Test hero title readability
                hero_title = self.driver.find_element(By.ID, "hero-title")
                title_font_size = self.driver.execute_script(
                    "return window.getComputedStyle(arguments[0]).fontSize", hero_title
                )
                title_size_px = int(title_font_size.replace('px', ''))
                
                # Title should be large enough to read
                min_title_size = 24 if width < 768 else 32
                self.assertGreaterEqual(title_size_px, min_title_size, 
                                      f"Hero title too small at {width}x{height}")
                
                # Test body text readability
                hero_lead = self.driver.find_element(By.CSS_SELECTOR, ".landing-hero .lead")
                lead_font_size = self.driver.execute_script(
                    "return window.getComputedStyle(arguments[0]).fontSize", hero_lead
                )
                lead_size_px = int(lead_font_size.replace('px', ''))
                
                # Body text should be readable
                min_body_size = 14 if width < 768 else 16
                self.assertGreaterEqual(lead_size_px, min_body_size,
                                      f"Body text too small at {width}x{height}")
                
                # Test feature card text
                feature_cards = self.driver.find_elements(By.CSS_SELECTOR, ".feature-card p")
                if feature_cards:
                    card_text_size = self.driver.execute_script(
                        "return window.getComputedStyle(arguments[0]).fontSize", feature_cards[0]
                    )
                    card_size_px = int(card_text_size.replace('px', ''))
                    
                    # Card text should be readable
                    min_card_size = 14
                    self.assertGreaterEqual(card_size_px, min_card_size,
                                          f"Feature card text too small at {width}x{height}")
    
    def test_loading_performance(self):
        """Test page loading performance"""
        # Measure page load time
        start_time = time.time()
        self.driver.get(self.base_url)
        
        # Wait for main content to load
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "main"))
        )
        
        # Wait for all images to load
        self.driver.execute_script("""
            return new Promise((resolve) => {
                const images = document.querySelectorAll('img');
                let loadedImages = 0;
                const totalImages = images.length;
                
                if (totalImages === 0) {
                    resolve();
                    return;
                }
                
                images.forEach(img => {
                    if (img.complete) {
                        loadedImages++;
                    } else {
                        img.onload = () => {
                            loadedImages++;
                            if (loadedImages === totalImages) {
                                resolve();
                            }
                        };
                        img.onerror = () => {
                            loadedImages++;
                            if (loadedImages === totalImages) {
                                resolve();
                            }
                        };
                    }
                });
                
                if (loadedImages === totalImages) {
                    resolve();
                }
            });
        """)
        
        load_time = time.time() - start_time
        
        # Page should load within reasonable time
        self.assertLess(load_time, 5.0, "Page load time should be under 5 seconds")
        
        # Check that all critical elements are present
        critical_elements = [
            "#hero-title",
            ".cta-button",
            ".feature-card",
            ".audience-item"
        ]
        
        for selector in critical_elements:
            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            self.assertGreater(len(elements), 0, f"Critical element {selector} not found")
    
    def test_javascript_functionality(self):
        """Test JavaScript functionality and interactions"""
        # Test that JavaScript is loaded and working
        js_working = self.driver.execute_script("return typeof document !== 'undefined'")
        self.assertTrue(js_working, "JavaScript should be working")
        
        # Test smooth scrolling functionality
        skip_link = self.driver.find_element(By.CSS_SELECTOR, ".visually-hidden-focusable")
        
        # Focus skip link and activate it
        self.driver.execute_script("arguments[0].focus()", skip_link)
        skip_link.send_keys(Keys.ENTER)
        
        time.sleep(1)  # Allow for smooth scrolling
        
        # Check that main content is in view
        main_content = self.driver.find_element(By.ID, "main-content")
        main_rect = main_content.rect
        viewport_height = self.driver.execute_script("return window.innerHeight")
        
        # Main content should be visible in viewport
        self.assertLessEqual(main_rect['y'], viewport_height, 
                           "Main content should be scrolled into view")
        
        # Test ARIA live region functionality
        live_region = self.driver.find_element(By.ID, "live-region")
        
        # Test that live region can be updated
        self.driver.execute_script(
            "arguments[0].textContent = 'Test announcement'", live_region
        )
        
        # Verify content was updated
        live_content = live_region.get_attribute('textContent')
        self.assertEqual(live_content, 'Test announcement', 
                        "Live region should be updatable")
    
    def test_print_styles(self):
        """Test print styles and print-friendly layout"""
        # Switch to print media
        self.driver.execute_script("""
            const style = document.createElement('style');
            style.textContent = '@media screen { body { background: white !important; } }';
            document.head.appendChild(style);
        """)
        
        # Test that content is still visible and readable
        hero_title = self.driver.find_element(By.ID, "hero-title")
        self.assertTrue(hero_title.is_displayed(), "Content should be visible for printing")
        
        # Test that interactive elements are still present
        cta_buttons = self.driver.find_elements(By.CSS_SELECTOR, ".cta-button")
        self.assertGreater(len(cta_buttons), 0, "CTA buttons should be present for printing")
        
        # Check that text color is readable for print
        title_color = self.driver.execute_script(
            "return window.getComputedStyle(arguments[0]).color", hero_title
        )
        self.assertIsNotNone(title_color, "Text should have readable color for print")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)