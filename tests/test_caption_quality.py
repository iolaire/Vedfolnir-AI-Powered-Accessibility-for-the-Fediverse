# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import unittest
import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from caption_quality_assessment import CaptionQualityManager, SimpleCaptionQualityAssessor

class TestCaptionQuality(unittest.TestCase):
    """Test cases for caption quality assessment"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.quality_manager = CaptionQualityManager()
        self.quality_assessor = SimpleCaptionQualityAssessor()
        
    def test_quality_assessment_basic(self):
        """Test basic caption quality assessment"""
        # Test with a good caption
        good_caption = "A beautiful sunset over the ocean with orange and purple clouds reflected in the calm water."
        good_metrics = self.quality_assessor.assess_caption_quality(good_caption)
        
        self.assertIsNotNone(good_metrics)
        self.assertIn('overall_score', good_metrics)
        self.assertIn('quality_level', good_metrics)
        self.assertIn('needs_review', good_metrics)
        self.assertGreaterEqual(good_metrics['overall_score'], 70)  # Should be a good score
        
        # Test with a poor caption
        poor_caption = "Image."
        poor_metrics = self.quality_assessor.assess_caption_quality(poor_caption)
        
        self.assertIsNotNone(poor_metrics)
        self.assertIn('overall_score', poor_metrics)
        self.assertLessEqual(poor_metrics['overall_score'], 50)  # Should be a poor score
        self.assertTrue(poor_metrics['needs_review'])  # Should need review
        
    def test_quality_assessment_length(self):
        """Test caption quality assessment based on length"""
        # Test with a very short caption
        short_caption = "A dog."
        short_metrics = self.quality_assessor.assess_caption_quality(short_caption)
        
        self.assertLessEqual(short_metrics['length_score'], 50)  # Should have a low length score
        self.assertTrue(short_metrics['needs_review'])  # Should need review
        
        # Test with an optimal length caption
        optimal_caption = "A golden retriever dog sitting on a green lawn in a backyard, looking at the camera with its tongue out."
        optimal_metrics = self.quality_assessor.assess_caption_quality(optimal_caption)
        
        self.assertGreaterEqual(optimal_metrics['length_score'], 80)  # Should have a high length score
        
        # Test with a too long caption
        long_caption = "A golden retriever dog with a shiny coat sitting on a perfectly manicured green lawn in a spacious backyard surrounded by colorful flowers and tall trees, looking directly at the camera with its tongue hanging out and its tail wagging enthusiastically while the sun shines brightly overhead casting a warm glow on the scene and creating a perfect summer day atmosphere that makes you want to join in and play with this friendly canine companion who seems to be enjoying the beautiful weather and inviting you to come over and pet him."
        long_metrics = self.quality_assessor.assess_caption_quality(long_caption)
        
        self.assertLessEqual(long_metrics['length_score'], 50)  # Should have a low length score
        self.assertTrue(long_metrics['needs_review'])  # Should need review
        
    def test_quality_assessment_content(self):
        """Test caption quality assessment based on content"""
        # Test with a caption lacking content
        basic_caption = "A picture of a building."
        basic_metrics = self.quality_assessor.assess_caption_quality(basic_caption)
        
        self.assertLessEqual(basic_metrics['content_score'], 70)  # Should have a low content score
        
        # Test with a detailed caption
        detailed_caption = "A tall modern skyscraper with a glass facade reflecting the blue sky and surrounding buildings. The distinctive curved design stands out against the city skyline."
        detailed_metrics = self.quality_assessor.assess_caption_quality(detailed_caption)
        
        self.assertGreaterEqual(detailed_metrics['content_score'], 50)  # Should have a high content score
        
    def test_quality_assessment_clarity(self):
        """Test caption quality assessment based on clarity"""
        # Test with a caption lacking clarity
        unclear_caption = "something in the image that looks like it might be a thing"
        unclear_metrics = self.quality_assessor.assess_caption_quality(unclear_caption)
        
        self.assertLessEqual(unclear_metrics['clarity_score'], 70)  # Should have a low clarity score
        
        # Test with a clear caption
        clear_caption = "A red apple sitting on a wooden table next to a glass of water."
        clear_metrics = self.quality_assessor.assess_caption_quality(clear_caption)
        
        self.assertGreaterEqual(clear_metrics['clarity_score'], 80)  # Should have a high clarity score
        
    def test_quality_badge_class(self):
        """Test getting the appropriate CSS class for quality badges"""
        self.assertEqual(self.quality_manager.get_quality_badge_class(95), "bg-success")
        self.assertEqual(self.quality_manager.get_quality_badge_class(75), "bg-info")
        self.assertEqual(self.quality_manager.get_quality_badge_class(50), "bg-warning")
        self.assertEqual(self.quality_manager.get_quality_badge_class(30), "bg-danger")
        
    def test_should_flag_for_review(self):
        """Test determining if a caption should be flagged for review"""
        # Test with explicit metrics
        metrics_needs_review = {'needs_review': True, 'overall_score': 30}
        self.assertTrue(self.quality_manager.should_flag_for_review("A caption", metrics_needs_review))
        
        metrics_no_review = {'needs_review': False, 'overall_score': 80}
        self.assertFalse(self.quality_manager.should_flag_for_review("A caption", metrics_no_review))
        
        # Test with heuristics
        self.assertTrue(self.quality_manager.should_flag_for_review(""))  # Empty caption
        self.assertTrue(self.quality_manager.should_flag_for_review("Too short"))  # Short caption
        self.assertTrue(self.quality_manager.should_flag_for_review("I can't see what's in this image clearly"))  # Uncertainty
        self.assertTrue(self.quality_manager.should_flag_for_review("A" * 490))  # Too long caption (over 500-15)
        
        # Test with good caption
        good_caption = "A red apple on a wooden table."
        self.assertFalse(self.quality_manager.should_flag_for_review(good_caption))
        
if __name__ == '__main__':
    unittest.main()