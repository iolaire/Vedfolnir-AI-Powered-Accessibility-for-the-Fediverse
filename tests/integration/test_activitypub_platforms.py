# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Tests for the ActivityPub platform adapters
"""

import unittest
import asyncio
from unittest.mock import MagicMock, patch
from config import ActivityPubConfig, Config
from activitypub_platforms import (
    ActivityPubPlatform, PixelfedPlatform, MastodonPlatform, PleromaPlatform,
    get_platform_adapter, detect_platform_type
)

class TestActivityPubPlatforms(unittest.TestCase):
    """Test cases for ActivityPub platform adapters"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = MagicMock()
        self.config.instance_url = "https://pixelfed.example.com"
        self.config.access_token = "test_token"
        
    def test_platform_detection_pixelfed(self):
        """Test detection of Pixelfed platforms"""
        pixelfed_urls = [
            "https://pixelfed.social",
            "https://pixelfed.de",
            "https://pixey.org",
            "https://instance.pixelfed.eu",
            "https://pix.tube"
        ]
        
        for url in pixelfed_urls:
            self.config.instance_url = url
            self.assertTrue(
                PixelfedPlatform.detect_platform(url),
                f"Failed to detect Pixelfed instance: {url}"
            )
    
    def test_platform_detection_mastodon(self):
        """Test detection of Mastodon platforms"""
        mastodon_urls = [
            "https://mastodon.social",
            "https://mastodon.online",
            "https://fosstodon.org",
            "https://mstdn.io",
            "https://instance.mastodon.xyz"
        ]
        
        for url in mastodon_urls:
            self.config.instance_url = url
            self.assertTrue(
                MastodonPlatform.detect_platform(url),
                f"Failed to detect Mastodon instance: {url}"
            )
    
    def test_platform_detection_pleroma(self):
        """Test detection of Pleroma platforms"""
        pleroma_urls = [
            "https://pleroma.social",
            "https://pleroma.site",
            "https://pleroma.xyz",
            "https://instance.pleroma.online"
        ]
        
        for url in pleroma_urls:
            self.config.instance_url = url
            self.assertTrue(
                PleromaPlatform.detect_platform(url),
                f"Failed to detect Pleroma instance: {url}"
            )
    
    def test_get_platform_adapter_explicit(self):
        """Test getting platform adapter with explicit platform type"""
        # Test Pixelfed
        self.config.platform_type = "pixelfed"
        adapter = get_platform_adapter(self.config)
        self.assertIsInstance(adapter, PixelfedPlatform)
        
        # Test Mastodon
        self.config.platform_type = "mastodon"
        adapter = get_platform_adapter(self.config)
        self.assertIsInstance(adapter, MastodonPlatform)
        
        # Test Pleroma
        self.config.platform_type = "pleroma"
        adapter = get_platform_adapter(self.config)
        self.assertIsInstance(adapter, PleromaPlatform)
    
    def test_get_platform_adapter_auto_detect(self):
        """Test getting platform adapter with auto-detection"""
        # Test Pixelfed auto-detection
        self.config.platform_type = None
        self.config.instance_url = "https://pixelfed.social"
        self.config.is_pixelfed = False
        adapter = get_platform_adapter(self.config)
        self.assertIsInstance(adapter, PixelfedPlatform)
        
        # Create separate config objects for each test to avoid interference
        mastodon_config = MagicMock()
        mastodon_config.platform_type = None
        mastodon_config.instance_url = "https://mastodon.social"
        mastodon_config.is_pixelfed = False
        adapter = get_platform_adapter(mastodon_config)
        self.assertIsInstance(adapter, MastodonPlatform)
        
        # Test Pleroma auto-detection
        pleroma_config = MagicMock()
        pleroma_config.platform_type = None
        pleroma_config.instance_url = "https://pleroma.social"
        pleroma_config.is_pixelfed = False
        adapter = get_platform_adapter(pleroma_config)
        self.assertIsInstance(adapter, PleromaPlatform)
    
    def test_legacy_is_pixelfed_flag(self):
        """Test that the legacy is_pixelfed flag works"""
        self.config.platform_type = None
        self.config.instance_url = "https://example.com"  # Not a known Pixelfed instance
        self.config.is_pixelfed = True
        
        adapter = get_platform_adapter(self.config)
        self.assertIsInstance(adapter, PixelfedPlatform)
    
    def test_platform_detection_fallback(self):
        """Test platform detection fallback methods"""
        # Test simple URL-based detection for Pixelfed
        self.assertTrue(PixelfedPlatform.detect_platform("https://pixelfed.social"))
        self.assertTrue(PixelfedPlatform.detect_platform("https://pixey.org"))
        
        # Test simple URL-based detection for Mastodon
        self.assertTrue(MastodonPlatform.detect_platform("https://mastodon.social"))
        self.assertTrue(MastodonPlatform.detect_platform("https://mstdn.io"))
        
        # Test simple URL-based detection for Pleroma
        self.assertTrue(PleromaPlatform.detect_platform("https://pleroma.social"))
        self.assertTrue(PleromaPlatform.detect_platform("https://pleroma.site"))
        
        # Test unknown platform
        self.assertFalse(PixelfedPlatform.detect_platform("https://example.com"))
        self.assertFalse(MastodonPlatform.detect_platform("https://example.com"))
        self.assertFalse(PleromaPlatform.detect_platform("https://example.com"))

if __name__ == '__main__':
    unittest.main()