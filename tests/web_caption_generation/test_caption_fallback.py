# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import unittest
import asyncio
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock
import logging

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from caption_fallback import CaptionFallbackManager, FallbackConfig
from app.utils.processing.ollama_caption_generator import OllamaCaptionGenerator
from config import OllamaConfig, RetryConfig

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestCaptionFallback(unittest.TestCase):
    """Test the caption fallback mechanisms"""
    
    def setUp(self):
        """Set up test environment"""
        # Create a fallback config for testing
        self.fallback_config = FallbackConfig(
            enabled=True,
            max_fallback_attempts=2,
            use_simplified_prompts=True,
            use_backup_model=True,
            backup_model_name="llava:13b-v1.6"
        )
        
        # Create a fallback manager
        self.fallback_manager = CaptionFallbackManager(self.fallback_config)
    
    def test_fallback_config_from_env(self):
        """Test creating fallback config from environment variables"""
        with patch.dict(os.environ, {
            "FALLBACK_ENABLED": "true",
            "FALLBACK_MAX_ATTEMPTS": "3",
            "FALLBACK_USE_SIMPLIFIED_PROMPTS": "true",
            "FALLBACK_USE_BACKUP_MODEL": "true",
            "FALLBACK_BACKUP_MODEL": "llava:13b-v1.6"
        }):
            config = FallbackConfig.from_env()
            
            self.assertTrue(config.enabled)
            self.assertEqual(config.max_fallback_attempts, 3)
            self.assertTrue(config.use_simplified_prompts)
            self.assertTrue(config.use_backup_model)
            self.assertEqual(config.backup_model_name, "llava:13b-v1.6")
    
    def test_get_fallback_prompt(self):
        """Test getting fallback prompts"""
        # Test first fallback attempt with portrait category
        prompt = self.fallback_manager.get_fallback_prompt("portrait", 1)
        self.assertIsNotNone(prompt)
        self.assertIn("person or people", prompt)
        
        # Test first fallback attempt with landscape category
        prompt = self.fallback_manager.get_fallback_prompt("sunset", 1)
        self.assertIsNotNone(prompt)
        self.assertIn("landscape or outdoor scene", prompt)
        
        # Test final fallback attempt (should use ultra-simplified prompt)
        prompt = self.fallback_manager.get_fallback_prompt("portrait", 2)
        self.assertEqual(prompt, self.fallback_manager.ULTRA_SIMPLIFIED_PROMPT)
    
    def test_get_fallback_model(self):
        """Test getting fallback models"""
        # Test first fallback attempt (should not use backup model)
        model = self.fallback_manager.get_fallback_model("llava:7b", 1)
        self.assertIsNone(model)
        
        # Test second fallback attempt (should use backup model)
        model = self.fallback_manager.get_fallback_model("llava:7b", 2)
        self.assertEqual(model, "llava:13b-v1.6")
        
        # Test when backup model is the same as original (should not use backup)
        model = self.fallback_manager.get_fallback_model("llava:13b-v1.6", 2)
        self.assertIsNone(model)
    
    def test_should_use_fallback(self):
        """Test determining if fallback should be used"""
        # Test with error (should use fallback)
        should_fallback = self.fallback_manager.should_use_fallback(error=Exception("Test error"))
        self.assertTrue(should_fallback)
        
        # Test with poor quality metrics (should use fallback)
        should_fallback = self.fallback_manager.should_use_fallback(quality_metrics={
            "overall_score": 30,
            "needs_review": True
        })
        self.assertTrue(should_fallback)
        
        # Test with good quality metrics (should not use fallback)
        should_fallback = self.fallback_manager.should_use_fallback(quality_metrics={
            "overall_score": 80,
            "needs_review": False
        })
        self.assertFalse(should_fallback)
    
    def test_map_to_simplified_category(self):
        """Test mapping specific categories to simplified categories"""
        # Test portrait categories
        self.assertEqual(self.fallback_manager._map_to_simplified_category("portrait"), "portrait")
        self.assertEqual(self.fallback_manager._map_to_simplified_category("selfie"), "portrait")
        self.assertEqual(self.fallback_manager._map_to_simplified_category("group_photo"), "portrait")
        
        # Test landscape categories
        self.assertEqual(self.fallback_manager._map_to_simplified_category("landscape"), "landscape")
        self.assertEqual(self.fallback_manager._map_to_simplified_category("beach"), "landscape")
        self.assertEqual(self.fallback_manager._map_to_simplified_category("sunset"), "landscape")
        
        # Test food categories
        self.assertEqual(self.fallback_manager._map_to_simplified_category("food"), "food")
        self.assertEqual(self.fallback_manager._map_to_simplified_category("dessert"), "food")
        
        # Test animal categories
        self.assertEqual(self.fallback_manager._map_to_simplified_category("animal"), "animal")
        self.assertEqual(self.fallback_manager._map_to_simplified_category("pet"), "animal")
        
        # Test artwork categories
        self.assertEqual(self.fallback_manager._map_to_simplified_category("artwork"), "artwork")
        self.assertEqual(self.fallback_manager._map_to_simplified_category("abstract"), "artwork")
        
        # Test text categories
        self.assertEqual(self.fallback_manager._map_to_simplified_category("document"), "text")
        self.assertEqual(self.fallback_manager._map_to_simplified_category("chart"), "text")
        
        # Test unknown category
        self.assertEqual(self.fallback_manager._map_to_simplified_category("unknown"), "general")

class TestOllamaCaptionGeneratorFallback(unittest.TestCase):
    """Test the fallback mechanisms in OllamaCaptionGenerator"""
    
    def setUp(self):
        """Set up test environment"""
        # Create configs for testing
        retry_config = RetryConfig(max_attempts=2)
        fallback_config = FallbackConfig(
            enabled=True,
            max_fallback_attempts=2,
            use_simplified_prompts=True,
            use_backup_model=True,
            backup_model_name="llava:13b-v1.6"
        )
        
        ollama_config = OllamaConfig(
            url="http://10.0.1.56:11434",
            model_name="llava:7b",
            timeout=30.0,
            retry=retry_config,
            fallback=fallback_config
        )
        
        # Create a mock OllamaCaptionGenerator
        self.generator = OllamaCaptionGenerator(ollama_config)
        self.generator.connection_validated = True  # Skip validation
        
        # Mock methods that make external calls
        self.generator._try_generate_caption = AsyncMock()
        # Classification removed - using general prompt only
    
    def test_generate_caption_with_fallback(self):
        """Test generate_caption with fallback mechanisms"""
        # Set up the test case
        test_image_path = "test_image.jpg"
        
        # Mock open to avoid actual file operations
        with patch("builtins.open", MagicMock()):
            with patch("base64.b64encode", MagicMock(return_value=b"test_image_data")):
                # Configure the mock to fail on first attempt and succeed on fallback
                self.generator._try_generate_caption.side_effect = [
                    None,  # Primary attempt fails
                    ("Fallback caption", {"overall_score": 80, "quality_level": "good", "needs_review": False})  # Fallback succeeds
                ]
                
                # Run the test
                result = asyncio.run(self.generator.generate_caption(test_image_path))
                
                # Verify the result
                self.assertIsNotNone(result)
                self.assertEqual(result[0], "Fallback caption")
                
                # Verify that _try_generate_caption was called twice
                self.assertEqual(self.generator._try_generate_caption.call_count, 2)
                
                # Verify fallback stats were updated
                self.assertEqual(self.generator.fallback_stats["fallback_attempts"], 1)
                self.assertEqual(self.generator.fallback_stats["fallback_successes"], 1)
    
    def test_generate_caption_with_low_quality(self):
        """Test generate_caption with low quality initial result"""
        # Set up the test case
        test_image_path = "test_image.jpg"
        
        # Mock open to avoid actual file operations
        with patch("builtins.open", MagicMock()):
            with patch("base64.b64encode", MagicMock(return_value=b"test_image_data")):
                # Configure the mock to return low quality caption first, then good quality
                self.generator._try_generate_caption.side_effect = [
                    ("Low quality caption", {"overall_score": 30, "quality_level": "poor", "needs_review": True}),  # Low quality
                    ("Better caption", {"overall_score": 80, "quality_level": "good", "needs_review": False})  # Good quality
                ]
                
                # Mock should_use_fallback to return True for the first result
                self.generator.fallback_manager.should_use_fallback = MagicMock(
                    side_effect=[True, False]  # First result needs fallback, second doesn't
                )
                
                # Run the test
                result = asyncio.run(self.generator.generate_caption(test_image_path))
                
                # Verify the result
                self.assertIsNotNone(result)
                self.assertEqual(result[0], "Better caption")
                
                # Verify that _try_generate_caption was called twice
                self.assertEqual(self.generator._try_generate_caption.call_count, 2)
                
                # Verify fallback stats were updated
                self.assertEqual(self.generator.fallback_stats["fallback_attempts"], 1)
                self.assertEqual(self.generator.fallback_stats["fallback_successes"], 1)
    
    def test_generate_caption_all_fallbacks_fail(self):
        """Test generate_caption when all fallbacks fail"""
        # Set up the test case
        test_image_path = "test_image.jpg"
        
        # Mock open to avoid actual file operations
        with patch("builtins.open", MagicMock()):
            with patch("base64.b64encode", MagicMock(return_value=b"test_image_data")):
                # Configure the mock to fail on all attempts
                self.generator._try_generate_caption.return_value = None
                
                # Run the test
                result = asyncio.run(self.generator.generate_caption(test_image_path))
                
                # Verify the result
                self.assertIsNone(result)
                
                # Verify that _try_generate_caption was called for primary + all fallback attempts
                self.assertEqual(self.generator._try_generate_caption.call_count, 3)  # Primary + 2 fallbacks
                
                # Verify fallback stats were updated
                self.assertEqual(self.generator.fallback_stats["fallback_attempts"], 2)
                self.assertEqual(self.generator.fallback_stats["fallback_failures"], 1)
                self.assertEqual(self.generator.fallback_stats["fallback_successes"], 0)

if __name__ == "__main__":
    unittest.main()