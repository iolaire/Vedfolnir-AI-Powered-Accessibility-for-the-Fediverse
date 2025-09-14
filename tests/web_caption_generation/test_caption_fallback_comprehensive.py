#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Comprehensive tests for caption generation fallback mechanisms.
"""
import unittest
import asyncio
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock, mock_open
import logging

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from caption_fallback import CaptionFallbackManager, FallbackConfig
from app.utils.processing.ollama_caption_generator import OllamaCaptionGenerator
from config import OllamaConfig, RetryConfig

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestFallbackConfig(unittest.TestCase):
    """Test FallbackConfig functionality"""
    
    def test_default_config(self):
        """Test default fallback configuration"""
        config = FallbackConfig()
        
        self.assertTrue(config.enabled)
        self.assertEqual(config.max_fallback_attempts, 2)
        self.assertTrue(config.use_simplified_prompts)
        self.assertTrue(config.use_backup_model)
        self.assertEqual(config.backup_model_name, "llava:13b-v1.6")
    
    def test_custom_config(self):
        """Test custom fallback configuration"""
        config = FallbackConfig(
            enabled=False,
            max_fallback_attempts=3,
            use_simplified_prompts=False,
            use_backup_model=False,
            backup_model_name="llava:34b"
        )
        
        self.assertFalse(config.enabled)
        self.assertEqual(config.max_fallback_attempts, 3)
        self.assertFalse(config.use_simplified_prompts)
        self.assertFalse(config.use_backup_model)
        self.assertEqual(config.backup_model_name, "llava:34b")
    
    def test_config_from_env(self):
        """Test creating config from environment variables"""
        env_vars = {
            "FALLBACK_ENABLED": "false",
            "FALLBACK_MAX_ATTEMPTS": "4",
            "FALLBACK_USE_SIMPLIFIED_PROMPTS": "false",
            "FALLBACK_USE_BACKUP_MODEL": "true",
            "FALLBACK_BACKUP_MODEL": "llava:34b"
        }
        
        with patch.dict(os.environ, env_vars):
            config = FallbackConfig.from_env()
            
            self.assertFalse(config.enabled)
            self.assertEqual(config.max_fallback_attempts, 4)
            self.assertFalse(config.use_simplified_prompts)
            self.assertTrue(config.use_backup_model)
            self.assertEqual(config.backup_model_name, "llava:34b")

class TestCaptionFallbackManager(unittest.TestCase):
    """Test CaptionFallbackManager functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = FallbackConfig(
            enabled=True,
            max_fallback_attempts=3,
            use_simplified_prompts=True,
            use_backup_model=True,
            backup_model_name="llava:13b-v1.6"
        )
        self.manager = CaptionFallbackManager(self.config)
    
    def test_manager_initialization(self):
        """Test fallback manager initialization"""
        self.assertEqual(self.manager.config, self.config)
        self.assertTrue(self.manager.config.enabled)
    
    def test_get_fallback_prompt_first_attempt(self):
        """Test getting fallback prompt for first attempt"""
        # Test portrait category
        prompt = self.manager.get_fallback_prompt("portrait", 1)
        self.assertIsNotNone(prompt)
        self.assertIn("person or people", prompt)
        self.assertIn("255 characters", prompt)
        
        # Test landscape category
        prompt = self.manager.get_fallback_prompt("landscape", 1)
        self.assertIsNotNone(prompt)
        self.assertIn("landscape or outdoor scene", prompt)
        
        # Test food category
        prompt = self.manager.get_fallback_prompt("food", 1)
        self.assertIsNotNone(prompt)
        self.assertIn("food or drink", prompt)
        
        # Test animal category
        prompt = self.manager.get_fallback_prompt("animal", 1)
        self.assertIsNotNone(prompt)
        self.assertIn("animal", prompt)
        
        # Test unknown category (should default to general)
        prompt = self.manager.get_fallback_prompt("unknown_category", 1)
        self.assertIsNotNone(prompt)
        self.assertEqual(prompt, self.manager.SIMPLIFIED_PROMPTS["general"])
    
    def test_get_fallback_prompt_final_attempt(self):
        """Test getting fallback prompt for final attempt"""
        prompt = self.manager.get_fallback_prompt("portrait", 3)
        self.assertEqual(prompt, self.manager.ULTRA_SIMPLIFIED_PROMPT)
        
        prompt = self.manager.get_fallback_prompt("landscape", 3)
        self.assertEqual(prompt, self.manager.ULTRA_SIMPLIFIED_PROMPT)
    
    def test_get_fallback_prompt_disabled(self):
        """Test getting fallback prompt when simplified prompts are disabled"""
        config = FallbackConfig(use_simplified_prompts=False)
        manager = CaptionFallbackManager(config)
        
        prompt = manager.get_fallback_prompt("portrait", 1)
        self.assertIsNone(prompt)
    
    def test_get_fallback_model_first_attempt(self):
        """Test getting fallback model for first attempt"""
        model = self.manager.get_fallback_model("llava:7b", 1)
        self.assertIsNone(model)  # Should not use backup model on first attempt
    
    def test_get_fallback_model_second_attempt(self):
        """Test getting fallback model for second attempt"""
        model = self.manager.get_fallback_model("llava:7b", 2)
        self.assertEqual(model, "llava:13b-v1.6")
    
    def test_get_fallback_model_same_as_original(self):
        """Test getting fallback model when backup is same as original"""
        model = self.manager.get_fallback_model("llava:13b-v1.6", 2)
        self.assertIsNone(model)  # Should not use same model as backup
    
    def test_get_fallback_model_disabled(self):
        """Test getting fallback model when backup model is disabled"""
        config = FallbackConfig(use_backup_model=False)
        manager = CaptionFallbackManager(config)
        
        model = manager.get_fallback_model("llava:7b", 2)
        self.assertIsNone(model)
    
    def test_map_to_simplified_category(self):
        """Test mapping specific categories to simplified categories"""
        # Test portrait mappings
        self.assertEqual(self.manager._map_to_simplified_category("portrait"), "portrait")
        self.assertEqual(self.manager._map_to_simplified_category("selfie"), "portrait")
        self.assertEqual(self.manager._map_to_simplified_category("group_photo"), "portrait")
        self.assertEqual(self.manager._map_to_simplified_category("person"), "portrait")
        
        # Test landscape mappings
        self.assertEqual(self.manager._map_to_simplified_category("landscape"), "landscape")
        self.assertEqual(self.manager._map_to_simplified_category("nature"), "landscape")
        self.assertEqual(self.manager._map_to_simplified_category("sunset"), "landscape")
        self.assertEqual(self.manager._map_to_simplified_category("beach"), "landscape")
        
        # Test food mappings
        self.assertEqual(self.manager._map_to_simplified_category("food"), "food")
        self.assertEqual(self.manager._map_to_simplified_category("dessert"), "food")
        self.assertEqual(self.manager._map_to_simplified_category("drink"), "food")
        
        # Test animal mappings
        self.assertEqual(self.manager._map_to_simplified_category("animal"), "animal")
        self.assertEqual(self.manager._map_to_simplified_category("pet"), "animal")
        self.assertEqual(self.manager._map_to_simplified_category("wildlife"), "animal")
        
        # Test artwork mappings
        self.assertEqual(self.manager._map_to_simplified_category("artwork"), "artwork")
        self.assertEqual(self.manager._map_to_simplified_category("abstract"), "artwork")
        self.assertEqual(self.manager._map_to_simplified_category("meme"), "artwork")
        
        # Test text mappings
        self.assertEqual(self.manager._map_to_simplified_category("document"), "text")
        self.assertEqual(self.manager._map_to_simplified_category("chart"), "text")
        self.assertEqual(self.manager._map_to_simplified_category("screenshot"), "text")
        
        # Test unknown category
        self.assertEqual(self.manager._map_to_simplified_category("unknown"), "general")
        self.assertEqual(self.manager._map_to_simplified_category("random_category"), "general")
    
    def test_should_use_fallback_with_error(self):
        """Test should_use_fallback with error"""
        should_fallback = self.manager.should_use_fallback(error=ConnectionError("Test error"))
        self.assertTrue(should_fallback)
        
        should_fallback = self.manager.should_use_fallback(error=TimeoutError("Timeout"))
        self.assertTrue(should_fallback)
    
    def test_should_use_fallback_with_poor_quality(self):
        """Test should_use_fallback with poor quality metrics"""
        # Test with needs_review flag
        should_fallback = self.manager.should_use_fallback(quality_metrics={
            "overall_score": 60,
            "needs_review": True
        })
        self.assertTrue(should_fallback)
        
        # Test with low quality score
        should_fallback = self.manager.should_use_fallback(quality_metrics={
            "overall_score": 30,
            "needs_review": False
        })
        self.assertTrue(should_fallback)
    
    def test_should_use_fallback_with_good_quality(self):
        """Test should_use_fallback with good quality metrics"""
        should_fallback = self.manager.should_use_fallback(quality_metrics={
            "overall_score": 80,
            "needs_review": False
        })
        self.assertFalse(should_fallback)
    
    def test_should_use_fallback_disabled(self):
        """Test should_use_fallback when fallback is disabled"""
        config = FallbackConfig(enabled=False)
        manager = CaptionFallbackManager(config)
        
        # Should not use fallback even with error
        should_fallback = manager.should_use_fallback(error=ConnectionError("Test"))
        self.assertFalse(should_fallback)
        
        # Should not use fallback even with poor quality
        should_fallback = manager.should_use_fallback(quality_metrics={
            "overall_score": 20,
            "needs_review": True
        })
        self.assertFalse(should_fallback)

class TestOllamaCaptionGeneratorFallback(unittest.IsolatedAsyncioTestCase):
    """Test fallback mechanisms in OllamaCaptionGenerator"""
    
    def setUp(self):
        """Set up test environment"""
        retry_config = RetryConfig(max_attempts=2)
        fallback_config = FallbackConfig(
            enabled=True,
            max_fallback_attempts=2,
            use_simplified_prompts=True,
            use_backup_model=True,
            backup_model_name="llava:13b-v1.6"
        )
        
        ollama_config = OllamaConfig(
            url="http://test:11434",
            model_name="llava:7b",
            timeout=30.0,
            retry=retry_config,
            fallback=fallback_config
        )
        
        self.generator = OllamaCaptionGenerator(ollama_config)
        self.generator.connection_validated = True  # Skip validation
        
        # Mock external dependencies
        self.generator._try_generate_caption = AsyncMock()
        # Classification removed - using general prompt only
    
    async def test_generate_caption_primary_success(self):
        """Test generate_caption when primary attempt succeeds"""
        test_image_path = "test_image.jpg"
        expected_result = ("Primary caption (AI-generated)", {
            "overall_score": 85,
            "quality_level": "good",
            "needs_review": False
        })
        
        # Mock successful primary attempt
        self.generator._try_generate_caption.return_value = expected_result
        
        with patch("builtins.open", mock_open(read_data=b"fake_image_data")):
            with patch("base64.b64encode", return_value=b"encoded_data"):
                result = await self.generator.generate_caption(test_image_path)
        
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "Primary caption (AI-generated)")
        self.assertEqual(self.generator._try_generate_caption.call_count, 1)
        
        # Verify no fallback was used
        self.assertEqual(self.generator.fallback_stats["fallback_attempts"], 0)
    
    async def test_generate_caption_fallback_after_failure(self):
        """Test generate_caption with fallback after primary failure"""
        test_image_path = "test_image.jpg"
        
        # Mock primary failure, fallback success
        self.generator._try_generate_caption.side_effect = [
            None,  # Primary fails
            ("Fallback caption", {
                "overall_score": 75,
                "quality_level": "good",
                "needs_review": False
            })  # Fallback succeeds
        ]
        
        with patch("builtins.open", mock_open(read_data=b"fake_image_data")):
            with patch("base64.b64encode", return_value=b"encoded_data"):
                result = await self.generator.generate_caption(test_image_path)
        
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "Fallback caption (AI-generated)")
        self.assertEqual(self.generator._try_generate_caption.call_count, 2)
        
        # Verify fallback stats
        self.assertEqual(self.generator.fallback_stats["fallback_attempts"], 1)
        self.assertEqual(self.generator.fallback_stats["fallback_successes"], 1)
    
    async def test_generate_caption_fallback_after_poor_quality(self):
        """Test generate_caption with fallback after poor quality result"""
        test_image_path = "test_image.jpg"
        
        # Mock poor quality primary, good quality fallback
        self.generator._try_generate_caption.side_effect = [
            ("Poor caption", {
                "overall_score": 25,
                "quality_level": "poor",
                "needs_review": True
            }),  # Poor quality primary
            ("Better caption", {
                "overall_score": 80,
                "quality_level": "good",
                "needs_review": False
            })  # Good quality fallback
        ]
        
        with patch("builtins.open", mock_open(read_data=b"fake_image_data")):
            with patch("base64.b64encode", return_value=b"encoded_data"):
                result = await self.generator.generate_caption(test_image_path)
        
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "Better caption (AI-generated)")
        self.assertEqual(self.generator._try_generate_caption.call_count, 2)
        
        # Verify fallback stats
        self.assertEqual(self.generator.fallback_stats["fallback_attempts"], 1)
        self.assertEqual(self.generator.fallback_stats["fallback_successes"], 1)
    
    async def test_generate_caption_multiple_fallbacks(self):
        """Test generate_caption with multiple fallback attempts"""
        test_image_path = "test_image.jpg"
        
        # Mock primary failure, first fallback failure, second fallback success
        self.generator._try_generate_caption.side_effect = [
            None,  # Primary fails
            None,  # First fallback fails
            ("Final caption", {
                "overall_score": 70,
                "quality_level": "acceptable",
                "needs_review": False
            })  # Second fallback succeeds
        ]
        
        with patch("builtins.open", mock_open(read_data=b"fake_image_data")):
            with patch("base64.b64encode", return_value=b"encoded_data"):
                result = await self.generator.generate_caption(test_image_path)
        
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "Final caption (AI-generated)")
        self.assertEqual(self.generator._try_generate_caption.call_count, 3)
        
        # Verify fallback stats
        self.assertEqual(self.generator.fallback_stats["fallback_attempts"], 2)
        self.assertEqual(self.generator.fallback_stats["fallback_successes"], 1)
    
    async def test_generate_caption_all_fallbacks_fail(self):
        """Test generate_caption when all fallbacks fail"""
        test_image_path = "test_image.jpg"
        
        # Mock all attempts failing
        self.generator._try_generate_caption.return_value = None
        
        with patch("builtins.open", mock_open(read_data=b"fake_image_data")):
            with patch("base64.b64encode", return_value=b"encoded_data"):
                result = await self.generator.generate_caption(test_image_path)
        
        self.assertIsNone(result)
        self.assertEqual(self.generator._try_generate_caption.call_count, 3)  # Primary + 2 fallbacks
        
        # Verify fallback stats
        self.assertEqual(self.generator.fallback_stats["fallback_attempts"], 2)
        self.assertEqual(self.generator.fallback_stats["fallback_failures"], 1)
        self.assertEqual(self.generator.fallback_stats["fallback_successes"], 0)
    
    async def test_generate_caption_with_different_prompts(self):
        """Test that fallback uses different prompts"""
        test_image_path = "test_image.jpg"
        
        # Track the prompts used
        prompts_used = []
        
        async def mock_try_generate_caption(image_path, image_data, model_name, prompt):
            prompts_used.append(prompt)
            if len(prompts_used) < 3:
                return None  # Fail first two attempts
            return ("Success", {"overall_score": 80, "needs_review": False})
        
        self.generator._try_generate_caption.side_effect = mock_try_generate_caption
        
        with patch("builtins.open", mock_open(read_data=b"fake_image_data")):
            with patch("base64.b64encode", return_value=b"encoded_data"):
                result = await self.generator.generate_caption(test_image_path)
        
        self.assertIsNotNone(result)
        self.assertEqual(len(prompts_used), 3)
        
        # Verify that different prompts were used
        self.assertEqual(prompts_used[0], "Test prompt")  # Original prompt
        self.assertNotEqual(prompts_used[1], prompts_used[0])  # First fallback prompt
        self.assertNotEqual(prompts_used[2], prompts_used[1])  # Second fallback prompt
        
        # The final prompt should be the ultra-simplified one
        self.assertEqual(prompts_used[2], self.generator.fallback_manager.ULTRA_SIMPLIFIED_PROMPT)
    
    async def test_generate_caption_with_backup_model(self):
        """Test that fallback uses backup model when configured"""
        test_image_path = "test_image.jpg"
        
        # Track the models used
        models_used = []
        
        async def mock_try_generate_caption(image_path, image_data, model_name, prompt):
            models_used.append(model_name or self.generator.config.model_name)
            if len(models_used) < 3:
                return None  # Fail first two attempts
            return ("Success", {"overall_score": 80, "needs_review": False})
        
        self.generator._try_generate_caption.side_effect = mock_try_generate_caption
        
        with patch("builtins.open", mock_open(read_data=b"fake_image_data")):
            with patch("base64.b64encode", return_value=b"encoded_data"):
                result = await self.generator.generate_caption(test_image_path)
        
        self.assertIsNotNone(result)
        self.assertEqual(len(models_used), 3)
        
        # Verify model usage
        self.assertEqual(models_used[0], "llava:7b")      # Original model
        self.assertEqual(models_used[1], "llava:7b")      # First fallback (same model, different prompt)
        self.assertEqual(models_used[2], "llava:13b-v1.6")  # Second fallback (backup model)

if __name__ == "__main__":
    unittest.main()