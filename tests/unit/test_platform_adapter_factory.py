# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Tests for PlatformAdapterFactory and platform adapter creation.

This module tests the platform adapter factory to ensure it correctly creates
adapters for different platforms and handles error scenarios properly.
"""

import unittest
from unittest.mock import Mock, patch
from dataclasses import dataclass
from typing import Optional

from activitypub_platforms import (
    PlatformAdapterFactory,
    PlatformAdapterError,
    UnsupportedPlatformError,
    PlatformDetectionError,
    PixelfedPlatform,
    MastodonPlatform,
    PleromaPlatform
)

@dataclass
class MockConfig:
    """Mock configuration for testing"""
    instance_url: str = "https://test.example.com"
    access_token: str = "test_token"
    api_type: Optional[str] = None
    platform_type: Optional[str] = None
    client_key: Optional[str] = None
    client_secret: Optional[str] = None

class TestPlatformAdapterFactory(unittest.TestCase):
    """Test PlatformAdapterFactory functionality"""
    
    def test_create_adapter_explicit_pixelfed(self):
        """Test creating Pixelfed adapter with explicit configuration"""
        config = MockConfig(api_type="pixelfed")
        
        adapter = PlatformAdapterFactory.create_adapter(config)
        
        self.assertTrue(isinstance(adapter, PixelfedPlatform))
        self.assertEqual(adapter.config, config)
    
    def test_create_adapter_explicit_mastodon(self):
        """Test creating Mastodon adapter with explicit configuration"""
        config = MockConfig(
            api_type="mastodon",
            client_key="test_key",
            client_secret="test_secret"
        )
        
        adapter = PlatformAdapterFactory.create_adapter(config)
        
        self.assertTrue(isinstance(adapter, MastodonPlatform))
        self.assertEqual(adapter.config, config)
    
    def test_create_adapter_explicit_pleroma(self):
        """Test creating Pleroma adapter with explicit configuration"""
        config = MockConfig(api_type="pleroma")
        
        adapter = PlatformAdapterFactory.create_adapter(config)
        
        self.assertTrue(isinstance(adapter, PleromaPlatform))
        self.assertEqual(adapter.config, config)
    
    def test_create_adapter_unsupported_platform(self):
        """Test creating adapter with unsupported platform type"""
        config = MockConfig(api_type="unsupported")
        
        with self.assertRaisesRegex(UnsupportedPlatformError, r"Unsupported platform type: unsupported"):
            PlatformAdapterFactory.create_adapter(config)
    
    def test_create_adapter_missing_instance_url(self):
        """Test creating adapter with missing instance URL"""
        config = MockConfig(instance_url="")
        
        with self.assertRaisesRegex(PlatformAdapterError, r"Configuration must have instance_url attribute"):
            PlatformAdapterFactory.create_adapter(config)
    
    def test_create_adapter_no_instance_url_attribute(self):
        """Test creating adapter with no instance_url attribute"""
        config = Mock()
        # Don't set instance_url attribute
        
        with self.assertRaisesRegex(PlatformAdapterError, r"Configuration must have instance_url attribute"):
            PlatformAdapterFactory.create_adapter(config)
    
    def test_create_adapter_legacy_platform_type(self):
        """Test creating adapter with legacy platform_type attribute"""
        config = MockConfig(platform_type="pixelfed")
        
        adapter = PlatformAdapterFactory.create_adapter(config)
        
        self.assertTrue(isinstance(adapter, PixelfedPlatform))
    
    def test_create_adapter_auto_detection_pixelfed(self):
        """Test auto-detection of Pixelfed platform"""
        config = MockConfig(instance_url="https://pixelfed.social")
        
        with patch.object(PixelfedPlatform, 'detect_platform', return_value=True):
            with patch.object(MastodonPlatform, 'detect_platform', return_value=False):
                with patch.object(PleromaPlatform, 'detect_platform', return_value=False):
                    adapter = PlatformAdapterFactory.create_adapter(config)
        
        self.assertTrue(isinstance(adapter, PixelfedPlatform))
    
    def test_create_adapter_auto_detection_mastodon(self):
        """Test auto-detection of Mastodon platform"""
        config = MockConfig(instance_url="https://mastodon.social")
        
        with patch.object(PixelfedPlatform, 'detect_platform', return_value=False):
            with patch.object(MastodonPlatform, 'detect_platform', return_value=True):
                with patch.object(PleromaPlatform, 'detect_platform', return_value=False):
                    adapter = PlatformAdapterFactory.create_adapter(config)
        
        self.assertTrue(isinstance(adapter, MastodonPlatform))
    
    def test_create_adapter_auto_detection_pleroma(self):
        """Test auto-detection of Pleroma platform"""
        config = MockConfig(instance_url="https://pleroma.social")
        
        with patch.object(PixelfedPlatform, 'detect_platform', return_value=False):
            with patch.object(MastodonPlatform, 'detect_platform', return_value=False):
                with patch.object(PleromaPlatform, 'detect_platform', return_value=True):
                    adapter = PlatformAdapterFactory.create_adapter(config)
        
        self.assertTrue(isinstance(adapter, PleromaPlatform))
    
    def test_create_adapter_auto_detection_failure(self):
        """Test auto-detection failure when no platform matches"""
        config = MockConfig(instance_url="https://unknown.social")
        
        with patch.object(PixelfedPlatform, 'detect_platform', return_value=False):
            with patch.object(MastodonPlatform, 'detect_platform', return_value=False):
                with patch.object(PleromaPlatform, 'detect_platform', return_value=False):
                    with self.assertRaisesRegex(PlatformDetectionError, r"Could not detect platform type"):
                        PlatformAdapterFactory.create_adapter(config)
    
    def test_create_adapter_detection_error_handling(self):
        """Test handling of errors during platform detection"""
        config = MockConfig(instance_url="https://error.social")
        
        with patch.object(PixelfedPlatform, 'detect_platform', side_effect=Exception("Detection error")):
            with patch.object(MastodonPlatform, 'detect_platform', return_value=False):
                with patch.object(PleromaPlatform, 'detect_platform', return_value=False):
                    with self.assertRaisesRegex(PlatformDetectionError, r"Could not detect platform type"):
                        PlatformAdapterFactory.create_adapter(config)
    
    def test_create_adapter_case_insensitive_platform_type(self):
        """Test that platform type matching is case insensitive"""
        config = MockConfig(api_type="PIXELFED")
        
        adapter = PlatformAdapterFactory.create_adapter(config)
        
        self.assertTrue(isinstance(adapter, PixelfedPlatform))
    
    def test_create_adapter_whitespace_platform_type(self):
        """Test handling of platform type with whitespace"""
        config = MockConfig(api_type="  mastodon  ")
        config.client_key = "test_key"
        config.client_secret = "test_secret"
        
        adapter = PlatformAdapterFactory.create_adapter(config)
        
        self.assertTrue(isinstance(adapter, MastodonPlatform))

class TestPlatformAdapterRegistration(unittest.TestCase):
    """Test platform adapter registration functionality"""
    
    def test_register_adapter_success(self):
        """Test successful adapter registration"""
        class TestPlatform(PixelfedPlatform):
            pass
        
        # Store original adapters to restore later
        original_adapters = PlatformAdapterFactory._adapters.copy()
        
        try:
            PlatformAdapterFactory.register_adapter("test", TestPlatform)
            
            self.assertTrue("test" in PlatformAdapterFactory._adapters)
            self.assertEqual(PlatformAdapterFactory._adapters["test"], TestPlatform)
        finally:
            # Restore original adapters
            PlatformAdapterFactory._adapters = original_adapters
    
    def test_register_adapter_invalid_class(self):
        """Test registering adapter with invalid class"""
        class InvalidPlatform:
            pass
        
        with self.assertRaisesRegex(ValueError, r"Adapter class must inherit from ActivityPubPlatform"):
            PlatformAdapterFactory.register_adapter("invalid", InvalidPlatform)
    
    def test_register_adapter_overwrite_existing(self):
        """Test overwriting existing adapter registration"""
        class NewPixelfedPlatform(PixelfedPlatform):
            pass
        
        # Store original adapters to restore later
        original_adapters = PlatformAdapterFactory._adapters.copy()
        
        try:
            PlatformAdapterFactory.register_adapter("pixelfed", NewPixelfedPlatform)
            
            self.assertEqual(PlatformAdapterFactory._adapters["pixelfed"], NewPixelfedPlatform)
        finally:
            # Restore original adapters
            PlatformAdapterFactory._adapters = original_adapters

class TestPlatformDetection(unittest.TestCase):
    """Test platform detection methods"""
    
    def test_pixelfed_detection_known_instances(self):
        """Test Pixelfed detection with known instances"""
        known_instances = [
            "https://pixelfed.social",
            "https://pixelfed.de",
            "https://pixelfed.uno",
            "https://pixey.org"
        ]
        
        for instance_url in known_instances:
            self.assertTrue(PixelfedPlatform.detect_platform(instance_url))
    
    def test_pixelfed_detection_pixelfed_in_domain(self):
        """Test Pixelfed detection with 'pixelfed' in domain"""
        test_urls = [
            "https://my-pixelfed.example.com",
            "https://pixelfed.myinstance.org"
        ]
        
        for instance_url in test_urls:
            self.assertTrue(PixelfedPlatform.detect_platform(instance_url))
    
    def test_pixelfed_detection_false_cases(self):
        """Test Pixelfed detection returns False for non-Pixelfed instances"""
        test_urls = [
            "https://mastodon.social",
            "https://pleroma.social",
            "https://example.com",
            ""
        ]
        
        for instance_url in test_urls:
            self.assertFalse(PixelfedPlatform.detect_platform(instance_url))
    
    def test_mastodon_detection_known_instances(self):
        """Test Mastodon detection with known instances"""
        known_instances = [
            "https://mastodon.social",
            "https://mastodon.online",
            "https://mstdn.social",
            "https://fosstodon.org"
        ]
        
        for instance_url in known_instances:
            self.assertTrue(MastodonPlatform.detect_platform(instance_url))
    
    def test_mastodon_detection_mastodon_in_domain(self):
        """Test Mastodon detection with 'mastodon' or 'mstdn' in domain"""
        test_urls = [
            "https://my-mastodon.example.com",
            "https://mastodon.myinstance.org",
            "https://mstdn.example.com"
        ]
        
        for instance_url in test_urls:
            self.assertTrue(MastodonPlatform.detect_platform(instance_url))
    
    def test_mastodon_detection_false_cases(self):
        """Test Mastodon detection returns False for non-Mastodon instances"""
        test_urls = [
            "https://pixelfed.social",
            "https://pleroma.social",
            "https://example.com",
            ""
        ]
        
        for instance_url in test_urls:
            self.assertFalse(MastodonPlatform.detect_platform(instance_url))
    
    def test_pleroma_detection_known_instances(self):
        """Test Pleroma detection with known instances"""
        known_instances = [
            "https://pleroma.social",
            "https://pleroma.site",
            "https://pleroma.online"
        ]
        
        for instance_url in known_instances:
            self.assertTrue(PleromaPlatform.detect_platform(instance_url))
    
    def test_pleroma_detection_pleroma_in_domain(self):
        """Test Pleroma detection with 'pleroma' in domain"""
        test_urls = [
            "https://my-pleroma.example.com",
            "https://pleroma.myinstance.org"
        ]
        
        for instance_url in test_urls:
            self.assertTrue(PleromaPlatform.detect_platform(instance_url))
    
    def test_pleroma_detection_false_cases(self):
        """Test Pleroma detection returns False for non-Pleroma instances"""
        test_urls = [
            "https://mastodon.social",
            "https://pixelfed.social",
            "https://example.com",
            ""
        ]
        
        for instance_url in test_urls:
            self.assertFalse(PleromaPlatform.detect_platform(instance_url))
    
    def test_detection_error_handling(self):
        """Test platform detection error handling"""
        # Test with malformed URLs
        malformed_urls = [
            "not-a-url",
            "ftp://invalid.com",
            None
        ]
        
        for url in malformed_urls:
            # Should not raise exceptions, just return False
            self.assertFalse(PixelfedPlatform.detect_platform(url))
            self.assertFalse(MastodonPlatform.detect_platform(url))
            self.assertFalse(PleromaPlatform.detect_platform(url))

if __name__ == "__main__":
    unittest.main()