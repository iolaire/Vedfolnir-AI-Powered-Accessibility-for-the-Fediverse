# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import unittest
import os
import sys
from unittest.mock import patch

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import CaptionConfig
from app.utils.processing.caption_quality_assessment import SimpleCaptionQualityAssessor, CaptionQualityManager

class TestCaptionConfigIntegration(unittest.TestCase):
    """Test caption configuration integration with quality assessment"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Store original environment variables
        self.original_env = {}
        for var in ['CAPTION_MAX_LENGTH', 'CAPTION_OPTIMAL_MIN_LENGTH', 'CAPTION_OPTIMAL_MAX_LENGTH']:
            self.original_env[var] = os.environ.get(var)
    
    def tearDown(self):
        """Clean up after tests"""
        # Restore original environment variables
        for var, value in self.original_env.items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]
    
    def test_caption_config_default_values(self):
        """Test that CaptionConfig uses correct default values"""
        # Clear environment variables to test defaults
        for var in ['CAPTION_MAX_LENGTH', 'CAPTION_OPTIMAL_MIN_LENGTH', 'CAPTION_OPTIMAL_MAX_LENGTH']:
            if var in os.environ:
                del os.environ[var]
        
        config = CaptionConfig.from_env()
        
        self.assertEqual(config.max_length, 500)
        self.assertEqual(config.optimal_min_length, 80)  # Default in code
        self.assertEqual(config.optimal_max_length, 200)
    
    def test_caption_config_with_new_env_values(self):
        """Test CaptionConfig with updated environment values from .env.example"""
        # Set environment variables to match new .env.example values
        os.environ['CAPTION_MAX_LENGTH'] = '500'
        os.environ['CAPTION_OPTIMAL_MIN_LENGTH'] = '150'  # New value
        os.environ['CAPTION_OPTIMAL_MAX_LENGTH'] = '450'  # Updated value from .env.example
        
        config = CaptionConfig.from_env()
        
        self.assertEqual(config.max_length, 500)
        self.assertEqual(config.optimal_min_length, 150)  # New value
        self.assertEqual(config.optimal_max_length, 450)  # Updated value
    
    def test_quality_assessor_with_new_optimal_min_length(self):
        """Test that SimpleCaptionQualityAssessor uses the new optimal min length"""
        # Set the new optimal min length
        os.environ['CAPTION_OPTIMAL_MIN_LENGTH'] = '150'
        os.environ['CAPTION_OPTIMAL_MAX_LENGTH'] = '450'
        
        assessor = SimpleCaptionQualityAssessor()
        
        self.assertEqual(assessor.optimal_min_length, 150)
        self.assertEqual(assessor.optimal_max_length, 450)
    
    def test_length_assessment_with_new_thresholds(self):
        """Test length assessment with the new optimal min length threshold"""
        os.environ['CAPTION_OPTIMAL_MIN_LENGTH'] = '150'
        os.environ['CAPTION_OPTIMAL_MAX_LENGTH'] = '450'
        
        assessor = SimpleCaptionQualityAssessor()
        
        # Test captions of different lengths
        short_caption = "A dog sitting."  # ~15 chars - too short
        medium_short_caption = "A golden retriever dog sitting on grass in a park during a sunny afternoon."  # ~80 chars - now below optimal
        optimal_caption = "A golden retriever dog with a shiny coat sitting on green grass in a beautiful park during a sunny afternoon, looking happy and relaxed with its tongue out."  # ~150+ chars - optimal
        long_caption = "A" * 460  # Long but acceptable
        too_long_caption = "A" * 510  # Too long
        
        # Test short caption
        short_result = assessor._assess_length(short_caption)
        self.assertEqual(short_result, 20)  # Too short
        
        # Test medium-short caption (now below new optimal min)
        medium_short_result = assessor._assess_length(medium_short_caption)
        self.assertEqual(medium_short_result, 60)  # Short but acceptable
        
        # Test optimal length caption
        optimal_result = assessor._assess_length(optimal_caption)
        self.assertEqual(optimal_result, 100)  # Optimal length
        
        # Test long caption
        long_result = assessor._assess_length(long_caption)
        self.assertEqual(long_result, 80)  # Long but acceptable
        
        # Test too long caption
        too_long_result = assessor._assess_length(too_long_caption)
        self.assertEqual(too_long_result, 40)  # Too long
    
    def test_quality_assessment_with_new_thresholds(self):
        """Test complete quality assessment with new length thresholds"""
        os.environ['CAPTION_OPTIMAL_MIN_LENGTH'] = '150'
        os.environ['CAPTION_OPTIMAL_MAX_LENGTH'] = '450'
        
        assessor = SimpleCaptionQualityAssessor()
        
        # Test a caption that was previously optimal but is now short
        previously_optimal = "A beautiful golden retriever dog sitting on green grass in a sunny park."  # ~80 chars
        result = assessor.assess_caption_quality(previously_optimal)
        
        # Should have lower length score due to new threshold
        self.assertEqual(result['length_score'], 60)  # Short but acceptable
        
        # Test a caption that meets the new optimal length
        new_optimal = "A beautiful golden retriever dog with a shiny golden coat sitting peacefully on lush green grass in a sunny park, looking directly at the camera with a friendly expression and its tongue slightly visible."  # ~200+ chars
        result = assessor.assess_caption_quality(new_optimal)
        
        # Should have high length score
        self.assertEqual(result['length_score'], 100)  # Optimal length
    
    def test_backward_compatibility_with_old_thresholds(self):
        """Test that the system still works with old threshold values"""
        # Set old threshold values
        os.environ['CAPTION_OPTIMAL_MIN_LENGTH'] = '80'
        os.environ['CAPTION_OPTIMAL_MAX_LENGTH'] = '200'
        
        assessor = SimpleCaptionQualityAssessor()
        
        # Test with a caption that was optimal under old system
        old_optimal = "A golden retriever dog sitting on grass in a park."  # ~50 chars
        result = assessor.assess_caption_quality(old_optimal)
        
        # Should still work correctly with old thresholds
        self.assertIsNotNone(result)
        self.assertIn('length_score', result)
        self.assertIn('overall_score', result)
    
    def test_quality_manager_with_new_config(self):
        """Test CaptionQualityManager with new configuration values"""
        os.environ['CAPTION_OPTIMAL_MIN_LENGTH'] = '150'
        os.environ['CAPTION_OPTIMAL_MAX_LENGTH'] = '450'
        
        manager = CaptionQualityManager()
        
        # Test with different caption lengths
        short_caption = "A dog."
        medium_caption = "A golden retriever sitting in a park on a sunny day."  # ~55 chars
        optimal_caption = "A beautiful golden retriever dog with a shiny coat sitting peacefully on lush green grass in a sunny park, wagging its tail and looking happy with bright eyes."  # ~160+ chars
        truly_optimal_caption = "A magnificent golden retriever dog with a lustrous golden coat sitting gracefully on emerald green grass in a picturesque park, looking directly at the camera with bright, intelligent eyes and a gentle, welcoming expression."  # ~220+ chars
        
        # Test short caption flagging
        self.assertTrue(manager.should_flag_for_review(short_caption))
        
        # Test medium caption (now considered short with new thresholds)
        medium_result = manager.assess_caption_quality(medium_caption)
        self.assertEqual(medium_result['length_score'], 60)  # Short but acceptable
        
        # Test optimal caption
        optimal_result = manager.assess_caption_quality(optimal_caption)
        self.assertEqual(optimal_result['length_score'], 100)  # Optimal (159 chars >= 150 min)
        
        # Test truly optimal caption
        truly_optimal_result = manager.assess_caption_quality(truly_optimal_caption)
        self.assertEqual(truly_optimal_result['length_score'], 100)  # Optimal (220+ chars)
    
    def test_env_example_values_integration(self):
        """Test integration with the exact values from .env.example"""
        # Set values exactly as they appear in .env.example
        os.environ['CAPTION_MAX_LENGTH'] = '500'
        os.environ['CAPTION_OPTIMAL_MIN_LENGTH'] = '150'
        os.environ['CAPTION_OPTIMAL_MAX_LENGTH'] = '450'
        
        # Test config creation
        config = CaptionConfig.from_env()
        self.assertEqual(config.max_length, 500)
        self.assertEqual(config.optimal_min_length, 150)
        self.assertEqual(config.optimal_max_length, 450)
        
        # Test quality assessor
        assessor = SimpleCaptionQualityAssessor()
        self.assertEqual(assessor.max_length, 500)
        self.assertEqual(assessor.optimal_min_length, 150)
        self.assertEqual(assessor.optimal_max_length, 450)
        
        # Test with a caption that should be optimal under new settings
        test_caption = "A magnificent golden retriever dog with a lustrous coat sitting gracefully on emerald green grass in a picturesque park setting, gazing directly at the camera with bright, intelligent eyes and a gentle, welcoming expression that conveys both friendliness and calm confidence."  # ~300+ chars
        
        result = assessor.assess_caption_quality(test_caption)
        
        # Should be within optimal range
        self.assertEqual(result['length_score'], 100)
        self.assertGreaterEqual(result['overall_score'], 70)
        self.assertIn(result['quality_level'], ['good', 'excellent'])
    
    def test_config_validation_with_invalid_values(self):
        """Test that configuration handles invalid environment values gracefully"""
        # Test with non-numeric values
        os.environ['CAPTION_OPTIMAL_MIN_LENGTH'] = 'invalid'
        
        with self.assertRaises(ValueError):
            SimpleCaptionQualityAssessor()
        
        # Test with negative values
        os.environ['CAPTION_OPTIMAL_MIN_LENGTH'] = '-10'
        
        assessor = SimpleCaptionQualityAssessor()
        # Should still create assessor but with negative value
        self.assertEqual(assessor.optimal_min_length, -10)
    
    def test_length_score_boundary_conditions(self):
        """Test length scoring at boundary conditions with new thresholds"""
        os.environ['CAPTION_OPTIMAL_MIN_LENGTH'] = '150'
        os.environ['CAPTION_OPTIMAL_MAX_LENGTH'] = '450'
        
        assessor = SimpleCaptionQualityAssessor()
        
        # Test exactly at boundaries
        exactly_min_optimal = "A" * 150
        exactly_max_optimal = "A" * 450
        exactly_max_length = "A" * 500
        
        self.assertEqual(assessor._assess_length(exactly_min_optimal), 100)  # Optimal
        self.assertEqual(assessor._assess_length(exactly_max_optimal), 100)  # Optimal
        self.assertEqual(assessor._assess_length(exactly_max_length), 80)   # Long but acceptable
        
        # Test just outside boundaries
        just_below_min = "A" * 149
        just_above_max_optimal = "A" * 451
        just_above_max = "A" * 501
        
        self.assertEqual(assessor._assess_length(just_below_min), 60)      # Short but acceptable
        self.assertEqual(assessor._assess_length(just_above_max_optimal), 80)  # Long but acceptable
        self.assertEqual(assessor._assess_length(just_above_max), 40)      # Too long

if __name__ == '__main__':
    unittest.main()