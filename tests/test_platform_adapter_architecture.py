# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Comprehensive tests for the platform adapter architecture.

This module tests the abstract base class, platform adapters, factory pattern,
and error handling according to task 10.2 requirements.
"""

import unittest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from config import ActivityPubConfig
from activitypub_platforms import (
    ActivityPubPlatform, PixelfedPlatform, MastodonPlatform, PleromaPlatform,
    PlatformAdapterFactory, get_platform_adapter,
    PlatformAdapterError, UnsupportedPlatformError, PlatformDetectionError
)


class MockPlatformAdapter(ActivityPubPlatform):
    """Mock platform adapter for testing abstract base class compliance"""
    
    @classmethod
    def detect_platform(cls, instance_url: str) -> bool:
        return instance_url == "https://mock.example.com"
    
    async def get_user_posts(self, client, user_id: str, limit: int = 50):
        return [{"id": "test_post", "content": "test"}]
    
    async def update_media_caption(self, client, image_post_id: str, caption: str) -> bool:
        return True
    
    def extract_images_from_post(self, post):
        return [{"url": "test.jpg", "id": "test_image"}]
    
    async def get_post_by_id(self, client, post_id: str):
        return {"id": post_id, "content": "test"}
    
    async def update_post(self, client, post_id: str, updated_post) -> bool:
        return True


class TestAbstractBaseClass(unittest.TestCase):
    """Test the abstract base class interface compliance"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = MagicMock()
        self.config.instance_url = "https://test.example.com"
        self.config.access_token = "test_token"
    
    def test_abstract_base_class_cannot_be_instantiated(self):
        """Test that the abstract base class cannot be instantiated directly"""
        with self.assertRaises(TypeError):
            ActivityPubPlatform(self.config)
    
    def test_mock_adapter_implements_all_required_methods(self):
        """Test that mock adapter implements all required abstract methods"""
        adapter = MockPlatformAdapter(self.config)
        
        # Test that all abstract methods are implemented
        self.assertTrue(hasattr(adapter, 'get_user_posts'))
        self.assertTrue(hasattr(adapter, 'update_media_caption'))
        self.assertTrue(hasattr(adapter, 'extract_images_from_post'))
        self.assertTrue(hasattr(adapter, 'get_post_by_id'))
        self.assertTrue(hasattr(adapter, 'update_post'))
        self.assertTrue(hasattr(adapter, 'detect_platform'))
        
        # Test that methods are callable
        self.assertTrue(callable(adapter.get_user_posts))
        self.assertTrue(callable(adapter.update_media_caption))
        self.assertTrue(callable(adapter.extract_images_from_post))
        self.assertTrue(callable(adapter.get_post_by_id))
        self.assertTrue(callable(adapter.update_post))
        self.assertTrue(callable(adapter.detect_platform))
    
    def test_base_class_validation(self):
        """Test base class configuration validation"""
        # Test missing instance_url
        config_no_url = MagicMock()
        config_no_url.access_token = "test_token"
        del config_no_url.instance_url
        
        with self.assertRaises(PlatformAdapterError):
            MockPlatformAdapter(config_no_url)
        
        # Test missing access_token
        config_no_token = MagicMock()
        config_no_token.instance_url = "https://test.example.com"
        del config_no_token.access_token
        
        with self.assertRaises(PlatformAdapterError):
            MockPlatformAdapter(config_no_token)
    
    def test_platform_name_property(self):
        """Test platform_name property"""
        adapter = MockPlatformAdapter(self.config)
        self.assertEqual(adapter.platform_name, "mockadapter")
    
    def test_string_representations(self):
        """Test string representations of adapter"""
        adapter = MockPlatformAdapter(self.config)
        
        str_repr = str(adapter)
        self.assertIn("MockPlatformAdapter", str_repr)
        self.assertIn(self.config.instance_url, str_repr)
        
        repr_str = repr(adapter)
        self.assertIn("MockPlatformAdapter", repr_str)
        self.assertIn("config=", repr_str)
    
    def test_default_rate_limit_info(self):
        """Test default rate limit info implementation"""
        adapter = MockPlatformAdapter(self.config)
        headers = {"X-RateLimit-Limit": "100"}
        
        # Default implementation should return empty dict
        rate_info = adapter.get_rate_limit_info(headers)
        self.assertEqual(rate_info, {})
    
    def test_default_cleanup(self):
        """Test default cleanup implementation"""
        async def run_test():
            adapter = MockPlatformAdapter(self.config)
            
            # Default cleanup should not raise any exceptions
            await adapter.cleanup()
        
        # Run the async test
        asyncio.run(run_test())


class TestPixelfedPlatformAdapter(unittest.TestCase):
    """Test PixelfedPlatform adapter maintains all existing functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = MagicMock()
        self.config.instance_url = "https://pixelfed.social"
        self.config.access_token = "test_token"
    
    def test_pixelfed_adapter_creation(self):
        """Test PixelfedPlatform adapter can be created"""
        adapter = PixelfedPlatform(self.config)
        self.assertIsInstance(adapter, ActivityPubPlatform)
        self.assertEqual(adapter.platform_name, "pixelfed")
    
    def test_pixelfed_platform_detection(self):
        """Test Pixelfed platform detection"""
        # Test known Pixelfed instances
        pixelfed_urls = [
            "https://pixelfed.social",
            "https://pixelfed.de",
            "https://pixey.org",
            "https://pix.tube",
            "https://custom.pixelfed.example.com"
        ]
        
        for url in pixelfed_urls:
            with self.subTest(url=url):
                self.assertTrue(PixelfedPlatform.detect_platform(url))
        
        # Test non-Pixelfed instances
        non_pixelfed_urls = [
            "https://mastodon.social",
            "https://example.com",
            "https://pleroma.social",
            ""
        ]
        
        for url in non_pixelfed_urls:
            with self.subTest(url=url):
                self.assertFalse(PixelfedPlatform.detect_platform(url))
    
    def test_pixelfed_rate_limit_info(self):
        """Test Pixelfed rate limit info extraction"""
        adapter = PixelfedPlatform(self.config)
        
        # Test with rate limit headers
        headers = {
            "X-RateLimit-Limit": "100",
            "X-RateLimit-Remaining": "95",
            "X-RateLimit-Reset": "1640995200"
        }
        
        rate_info = adapter.get_rate_limit_info(headers)
        
        self.assertEqual(rate_info['limit'], 100)
        self.assertEqual(rate_info['remaining'], 95)
        self.assertEqual(rate_info['reset'], 1640995200)
        
        # Test with missing headers
        empty_headers = {}
        rate_info = adapter.get_rate_limit_info(empty_headers)
        self.assertEqual(rate_info, {})
    
    def test_pixelfed_config_validation(self):
        """Test Pixelfed-specific configuration validation"""
        # Pixelfed should not require additional config beyond base requirements
        adapter = PixelfedPlatform(self.config)
        self.assertEqual(adapter.config, self.config)
    
    def test_pixelfed_method_signatures(self):
        """Test that PixelfedPlatform method signatures match abstract base class"""
        adapter = PixelfedPlatform(self.config)
        
        # Check method signatures exist and are callable
        self.assertTrue(hasattr(adapter, 'get_user_posts'))
        self.assertTrue(hasattr(adapter, 'update_media_caption'))
        self.assertTrue(hasattr(adapter, 'extract_images_from_post'))
        self.assertTrue(hasattr(adapter, 'get_post_by_id'))
        self.assertTrue(hasattr(adapter, 'update_post'))
        
        # Check that methods are async where expected
        self.assertTrue(asyncio.iscoroutinefunction(adapter.get_user_posts))
        self.assertTrue(asyncio.iscoroutinefunction(adapter.update_media_caption))
        self.assertTrue(asyncio.iscoroutinefunction(adapter.get_post_by_id))
        self.assertTrue(asyncio.iscoroutinefunction(adapter.update_post))
        
        # extract_images_from_post should not be async
        self.assertFalse(asyncio.iscoroutinefunction(adapter.extract_images_from_post))


class TestMastodonPlatformAdapter(unittest.TestCase):
    """Test MastodonPlatform adapter implements all required methods"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = MagicMock()
        self.config.instance_url = "https://mastodon.social"
        self.config.access_token = "test_token"
        self.config.api_type = "mastodon"
        self.config.client_key = "test_client_key"
        self.config.client_secret = "test_client_secret"
    
    def test_mastodon_adapter_creation(self):
        """Test MastodonPlatform adapter can be created"""
        adapter = MastodonPlatform(self.config)
        self.assertIsInstance(adapter, ActivityPubPlatform)
        self.assertEqual(adapter.platform_name, "mastodon")
    
    def test_mastodon_platform_detection(self):
        """Test Mastodon platform detection"""
        # Test known Mastodon instances
        mastodon_urls = [
            "https://mastodon.social",
            "https://mastodon.online",
            "https://fosstodon.org",
            "https://mstdn.io",
            "https://custom.mastodon.example.com"
        ]
        
        for url in mastodon_urls:
            with self.subTest(url=url):
                self.assertTrue(MastodonPlatform.detect_platform(url))
        
        # Test non-Mastodon instances
        non_mastodon_urls = [
            "https://pixelfed.social",
            "https://example.com",
            "https://pleroma.social",
            ""
        ]
        
        for url in non_mastodon_urls:
            with self.subTest(url=url):
                self.assertFalse(MastodonPlatform.detect_platform(url))
    
    def test_mastodon_config_validation(self):
        """Test Mastodon-specific configuration validation"""
        # Test valid config
        adapter = MastodonPlatform(self.config)
        self.assertEqual(adapter.config, self.config)
        
        # Test missing client_key
        config_no_key = MagicMock()
        config_no_key.instance_url = "https://mastodon.social"
        config_no_key.access_token = "test_token"
        config_no_key.api_type = "mastodon"
        config_no_key.client_secret = "test_client_secret"
        del config_no_key.client_key
        
        with self.assertRaises(PlatformAdapterError):
            MastodonPlatform(config_no_key)
        
        # Test missing client_secret
        config_no_secret = MagicMock()
        config_no_secret.instance_url = "https://mastodon.social"
        config_no_secret.access_token = "test_token"
        config_no_secret.api_type = "mastodon"
        config_no_secret.client_key = "test_client_key"
        del config_no_secret.client_secret
        
        with self.assertRaises(PlatformAdapterError):
            MastodonPlatform(config_no_secret)
    
    def test_mastodon_rate_limit_info(self):
        """Test Mastodon rate limit info extraction"""
        adapter = MastodonPlatform(self.config)
        
        # Test with rate limit headers
        headers = {
            "X-RateLimit-Limit": "300",
            "X-RateLimit-Remaining": "250",
            "X-RateLimit-Reset": "1640995200"
        }
        
        rate_info = adapter.get_rate_limit_info(headers)
        
        self.assertEqual(rate_info['limit'], 300)
        self.assertEqual(rate_info['remaining'], 250)
        self.assertEqual(rate_info['reset'], 1640995200)
        
        # Test with missing headers
        empty_headers = {}
        rate_info = adapter.get_rate_limit_info(empty_headers)
        self.assertEqual(rate_info, {})
    
    def test_mastodon_method_signatures(self):
        """Test that MastodonPlatform method signatures match abstract base class"""
        adapter = MastodonPlatform(self.config)
        
        # Check method signatures exist and are callable
        self.assertTrue(hasattr(adapter, 'get_user_posts'))
        self.assertTrue(hasattr(adapter, 'update_media_caption'))
        self.assertTrue(hasattr(adapter, 'extract_images_from_post'))
        self.assertTrue(hasattr(adapter, 'get_post_by_id'))
        self.assertTrue(hasattr(adapter, 'update_post'))
        
        # Check that methods are async where expected
        self.assertTrue(asyncio.iscoroutinefunction(adapter.get_user_posts))
        self.assertTrue(asyncio.iscoroutinefunction(adapter.update_media_caption))
        self.assertTrue(asyncio.iscoroutinefunction(adapter.get_post_by_id))
        self.assertTrue(asyncio.iscoroutinefunction(adapter.update_post))
        
        # extract_images_from_post should not be async
        self.assertFalse(asyncio.iscoroutinefunction(adapter.extract_images_from_post))


class TestPlatformAdapterFactory(unittest.TestCase):
    """Test platform adapter factory creates correct adapter based on configuration"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.base_config = MagicMock()
        self.base_config.instance_url = "https://test.example.com"
        self.base_config.access_token = "test_token"
    
    def test_factory_creates_pixelfed_adapter_explicit(self):
        """Test factory creates PixelfedPlatform when explicitly specified"""
        config = MagicMock()
        config.instance_url = "https://test.example.com"
        config.access_token = "test_token"
        config.api_type = "pixelfed"
        
        adapter = PlatformAdapterFactory.create_adapter(config)
        self.assertIsInstance(adapter, PixelfedPlatform)
    
    def test_factory_creates_mastodon_adapter_explicit(self):
        """Test factory creates MastodonPlatform when explicitly specified"""
        config = MagicMock()
        config.instance_url = "https://mastodon.social"
        config.access_token = "test_token"
        config.api_type = "mastodon"
        config.client_key = "test_key"
        config.client_secret = "test_secret"
        
        adapter = PlatformAdapterFactory.create_adapter(config)
        self.assertIsInstance(adapter, MastodonPlatform)
    
    def test_factory_creates_pleroma_adapter_explicit(self):
        """Test factory creates PleromaPlatform when explicitly specified"""
        config = MagicMock()
        config.instance_url = "https://pleroma.social"
        config.access_token = "test_token"
        config.api_type = "pleroma"
        
        adapter = PlatformAdapterFactory.create_adapter(config)
        self.assertIsInstance(adapter, PleromaPlatform)
    
    def test_factory_auto_detection_pixelfed(self):
        """Test factory auto-detects Pixelfed platform"""
        config = MagicMock()
        config.instance_url = "https://pixelfed.social"
        config.access_token = "test_token"
        # No explicit api_type or platform_type
        del config.api_type
        del config.platform_type
        
        adapter = PlatformAdapterFactory.create_adapter(config)
        self.assertIsInstance(adapter, PixelfedPlatform)
    
    def test_factory_auto_detection_mastodon(self):
        """Test factory auto-detects Mastodon platform"""
        config = MagicMock()
        config.instance_url = "https://mastodon.social"
        config.access_token = "test_token"
        # No explicit api_type or platform_type
        del config.api_type
        del config.platform_type
        
        adapter = PlatformAdapterFactory.create_adapter(config)
        self.assertIsInstance(adapter, MastodonPlatform)
    
    def test_factory_legacy_platform_type_support(self):
        """Test factory supports legacy platform_type attribute"""
        config = MagicMock()
        config.instance_url = "https://test.example.com"
        config.access_token = "test_token"
        config.platform_type = "mastodon"
        config.client_key = "test_key"
        config.client_secret = "test_secret"
        del config.api_type  # No api_type, only platform_type
        
        adapter = PlatformAdapterFactory.create_adapter(config)
        self.assertIsInstance(adapter, MastodonPlatform)
    
    def test_factory_legacy_is_pixelfed_flag(self):
        """Test factory supports legacy is_pixelfed flag"""
        config = MagicMock()
        config.instance_url = "https://unknown.example.com"
        config.access_token = "test_token"
        config.is_pixelfed = True
        del config.api_type
        del config.platform_type
        
        adapter = PlatformAdapterFactory.create_adapter(config)
        self.assertIsInstance(adapter, PixelfedPlatform)
    
    def test_factory_fallback_to_pixelfed(self):
        """Test factory falls back to Pixelfed for unknown platforms"""
        config = MagicMock()
        config.instance_url = "https://unknown.example.com"
        config.access_token = "test_token"
        del config.api_type
        del config.platform_type
        del config.is_pixelfed
        
        adapter = PlatformAdapterFactory.create_adapter(config)
        self.assertIsInstance(adapter, PixelfedPlatform)
    
    def test_factory_error_handling_unsupported_platform(self):
        """Test factory error handling for unsupported platform types"""
        config = MagicMock()
        config.instance_url = "https://test.example.com"
        config.access_token = "test_token"
        config.api_type = "unsupported_platform"
        
        with self.assertRaises(UnsupportedPlatformError) as context:
            PlatformAdapterFactory.create_adapter(config)
        
        self.assertIn("unsupported_platform", str(context.exception))
        self.assertIn("Supported platforms:", str(context.exception))
    
    def test_factory_error_handling_missing_config(self):
        """Test factory error handling for missing configuration"""
        config = MagicMock()
        # Missing instance_url
        config.access_token = "test_token"
        del config.instance_url
        
        with self.assertRaises(PlatformAdapterError) as context:
            PlatformAdapterFactory.create_adapter(config)
        
        self.assertIn("instance_url", str(context.exception))
    
    def test_factory_get_supported_platforms(self):
        """Test factory returns list of supported platforms"""
        platforms = PlatformAdapterFactory.get_supported_platforms()
        
        self.assertIsInstance(platforms, list)
        self.assertIn('pixelfed', platforms)
        self.assertIn('mastodon', platforms)
        self.assertIn('pleroma', platforms)
    
    def test_factory_register_adapter(self):
        """Test factory can register new adapters"""
        # Register mock adapter
        PlatformAdapterFactory.register_adapter('mock', MockPlatformAdapter)
        
        # Test it's in supported platforms
        platforms = PlatformAdapterFactory.get_supported_platforms()
        self.assertIn('mock', platforms)
        
        # Test it can be created
        config = MagicMock()
        config.instance_url = "https://mock.example.com"
        config.access_token = "test_token"
        config.api_type = "mock"
        
        adapter = PlatformAdapterFactory.create_adapter(config)
        self.assertIsInstance(adapter, MockPlatformAdapter)
        
        # Clean up
        del PlatformAdapterFactory._adapters['mock']
    
    def test_factory_register_invalid_adapter(self):
        """Test factory rejects invalid adapter classes"""
        class InvalidAdapter:
            pass
        
        with self.assertRaises(ValueError):
            PlatformAdapterFactory.register_adapter('invalid', InvalidAdapter)


class TestBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility function"""
    
    def test_get_platform_adapter_function(self):
        """Test backward compatibility get_platform_adapter function"""
        config = MagicMock()
        config.instance_url = "https://pixelfed.social"
        config.access_token = "test_token"
        del config.api_type
        del config.platform_type
        
        adapter = get_platform_adapter(config)
        self.assertIsInstance(adapter, PixelfedPlatform)


class TestIntegrationAndBasicFunctionality(unittest.TestCase):
    """Test adapter instantiation and basic functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.pixelfed_config = MagicMock()
        self.pixelfed_config.instance_url = "https://pixelfed.social"
        self.pixelfed_config.access_token = "test_token"
        
        self.mastodon_config = MagicMock()
        self.mastodon_config.instance_url = "https://mastodon.social"
        self.mastodon_config.access_token = "test_token"
        self.mastodon_config.api_type = "mastodon"
        self.mastodon_config.client_key = "test_key"
        self.mastodon_config.client_secret = "test_secret"
    
    def test_pixelfed_adapter_instantiation(self):
        """Test PixelfedPlatform adapter instantiation"""
        adapter = PixelfedPlatform(self.pixelfed_config)
        
        self.assertIsInstance(adapter, ActivityPubPlatform)
        self.assertEqual(adapter.config, self.pixelfed_config)
        self.assertEqual(adapter.platform_name, "pixelfed")
    
    def test_mastodon_adapter_instantiation(self):
        """Test MastodonPlatform adapter instantiation"""
        adapter = MastodonPlatform(self.mastodon_config)
        
        self.assertIsInstance(adapter, ActivityPubPlatform)
        self.assertEqual(adapter.config, self.mastodon_config)
        self.assertEqual(adapter.platform_name, "mastodon")
    
    def test_adapter_cleanup_and_resource_management(self):
        """Test adapter cleanup and resource management"""
        async def test_cleanup():
            pixelfed_adapter = PixelfedPlatform(self.pixelfed_config)
            mastodon_adapter = MastodonPlatform(self.mastodon_config)
            
            # Test cleanup doesn't raise exceptions
            await pixelfed_adapter.cleanup()
            await mastodon_adapter.cleanup()
        
        # Run the async test
        asyncio.run(test_cleanup())


class TestInterfaceConsistency(unittest.TestCase):
    """Test interface consistency between adapters"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.pixelfed_config = MagicMock()
        self.pixelfed_config.instance_url = "https://pixelfed.social"
        self.pixelfed_config.access_token = "test_token"
        
        self.mastodon_config = MagicMock()
        self.mastodon_config.instance_url = "https://mastodon.social"
        self.mastodon_config.access_token = "test_token"
        self.mastodon_config.api_type = "mastodon"
        self.mastodon_config.client_key = "test_key"
        self.mastodon_config.client_secret = "test_secret"
    
    def test_adapter_method_signatures_consistency(self):
        """Test that all adapters have consistent method signatures"""
        pixelfed_adapter = PixelfedPlatform(self.pixelfed_config)
        mastodon_adapter = MastodonPlatform(self.mastodon_config)
        
        adapters = [pixelfed_adapter, mastodon_adapter]
        
        for adapter in adapters:
            with self.subTest(adapter=adapter.__class__.__name__):
                # Test all required methods exist
                self.assertTrue(hasattr(adapter, 'get_user_posts'))
                self.assertTrue(hasattr(adapter, 'update_media_caption'))
                self.assertTrue(hasattr(adapter, 'extract_images_from_post'))
                self.assertTrue(hasattr(adapter, 'get_post_by_id'))
                self.assertTrue(hasattr(adapter, 'update_post'))
                self.assertTrue(hasattr(adapter, 'detect_platform'))
                self.assertTrue(hasattr(adapter, 'get_rate_limit_info'))
                
                # Test async methods are async
                self.assertTrue(asyncio.iscoroutinefunction(adapter.get_user_posts))
                self.assertTrue(asyncio.iscoroutinefunction(adapter.update_media_caption))
                self.assertTrue(asyncio.iscoroutinefunction(adapter.get_post_by_id))
                self.assertTrue(asyncio.iscoroutinefunction(adapter.update_post))
                
                # Test sync methods are not async
                self.assertFalse(asyncio.iscoroutinefunction(adapter.extract_images_from_post))
                self.assertFalse(asyncio.iscoroutinefunction(adapter.get_rate_limit_info))
    
    def test_adapter_interface_compliance(self):
        """Test that all adapters comply with the abstract interface"""
        pixelfed_adapter = PixelfedPlatform(self.pixelfed_config)
        mastodon_adapter = MastodonPlatform(self.mastodon_config)
        
        adapters = [pixelfed_adapter, mastodon_adapter]
        
        for adapter in adapters:
            with self.subTest(adapter=adapter.__class__.__name__):
                # Test adapter is instance of base class
                self.assertIsInstance(adapter, ActivityPubPlatform)
                
                # Test platform_name property
                self.assertIsInstance(adapter.platform_name, str)
                self.assertTrue(len(adapter.platform_name) > 0)
                
                # Test string representations
                str_repr = str(adapter)
                self.assertIsInstance(str_repr, str)
                self.assertTrue(len(str_repr) > 0)
                
                repr_str = repr(adapter)
                self.assertIsInstance(repr_str, str)
                self.assertTrue(len(repr_str) > 0)


if __name__ == '__main__':
    unittest.main()