# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import logging
import os
import re
from typing import Dict, Tuple, List, Optional, Any

# Configure logging
logger = logging.getLogger(__name__)

class SimpleCaptionQualityAssessor:
    """
    Simple caption quality assessor that doesn't rely on image classification
    """
    
    def __init__(self, config=None):
        """Initialize the quality assessor"""
        self.config = config
        self.max_length = int(os.getenv("CAPTION_MAX_LENGTH", "500"))
        self.optimal_min_length = int(os.getenv("CAPTION_OPTIMAL_MIN_LENGTH", "80"))
        self.optimal_max_length = int(os.getenv("CAPTION_OPTIMAL_MAX_LENGTH", "200"))
    
    def assess_caption_quality(self, caption: str, prompt_used: str = None) -> Dict[str, Any]:
        """
        Assess the quality of a caption using simple heuristics
        
        Args:
            caption: The caption text to assess
            prompt_used: Optional prompt used to generate the caption
            
        Returns:
            Dictionary containing quality metrics and overall score
        """
        if not caption:
            return {
                'overall_score': 0,
                'quality_level': 'poor',
                'needs_review': True,
                'feedback': 'Caption is empty or missing.',
                'length_score': 0,
                'content_score': 0,
                'clarity_score': 0
            }
        
        # Length assessment
        length_score = self._assess_length(caption)
        
        # Content assessment
        content_score = self._assess_content(caption)
        
        # Clarity assessment
        clarity_score = self._assess_clarity(caption)
        
        # Calculate overall score
        overall_score = int((length_score + content_score + clarity_score) / 3)
        
        # Determine quality level
        if overall_score >= 90:
            quality_level = 'excellent'
        elif overall_score >= 70:
            quality_level = 'good'
        elif overall_score >= 40:
            quality_level = 'fair'
        else:
            quality_level = 'poor'
        
        # Determine if needs review
        needs_review = overall_score < 70 or self._has_quality_issues(caption)
        
        # Generate feedback
        feedback = self._generate_feedback(caption, length_score, content_score, clarity_score)
        
        return {
            'overall_score': overall_score,
            'quality_level': quality_level,
            'needs_review': needs_review,
            'feedback': feedback,
            'length_score': length_score,
            'content_score': content_score,
            'clarity_score': clarity_score
        }
    
    def _assess_length(self, caption: str) -> int:
        """Assess caption length"""
        length = len(caption)
        
        if length < 20:
            return 20  # Too short
        elif length < self.optimal_min_length:
            return 60  # Short but acceptable
        elif length <= self.optimal_max_length:
            return 100  # Optimal length
        elif length <= self.max_length:
            return 80  # Long but acceptable
        else:
            return 40  # Too long
    
    def _assess_content(self, caption: str) -> int:
        """Assess caption content quality"""
        score = 70  # Start with a lower base score
        
        # Check for problematic phrases
        problematic_phrases = [
            "I can't see", "I don't know", "unclear", "not sure",
            "cannot determine", "unable to", "difficult to", "hard to tell"
        ]
        
        for phrase in problematic_phrases:
            if phrase.lower() in caption.lower():
                score -= 40
                break
        
        # Check for very generic descriptions
        generic_phrases = [
            "this is an image", "this image shows", "the image contains",
            "there is", "there are", "this appears to be", "a picture of"
        ]
        
        generic_count = sum(1 for phrase in generic_phrases if phrase.lower() in caption.lower())
        if generic_count > 0:
            score -= 30  # More penalty for generic phrases
        
        # Check for very short descriptions
        if len(caption.split()) < 5:
            score -= 25
        
        # Check for descriptive content
        descriptive_words = [
            "color", "bright", "dark", "large", "small", "beautiful", "detailed",
            "wearing", "holding", "standing", "sitting", "walking", "running"
        ]
        
        descriptive_count = sum(1 for word in descriptive_words if word.lower() in caption.lower())
        if descriptive_count >= 3:
            score += 20
        elif descriptive_count == 0:
            score -= 20
        
        return max(0, min(100, score))
    
    def _assess_clarity(self, caption: str) -> int:
        """Assess caption clarity"""
        score = 90  # Start with a lower base score
        
        # Check for vague language
        vague_phrases = [
            "something", "might be", "looks like", "appears to", "seems to",
            "kind of", "sort of", "maybe", "possibly"
        ]
        
        vague_count = sum(1 for phrase in vague_phrases if phrase.lower() in caption.lower())
        if vague_count > 0:
            score -= 30  # Heavy penalty for vague language
        
        # Check sentence structure
        sentences = caption.split('.')
        if len(sentences) < 2:
            score -= 10  # Single sentence might lack detail
        
        # Check for proper capitalization
        if not caption[0].isupper():
            score -= 10
        
        # Check for ending punctuation
        if not caption.rstrip().endswith(('.', '!', '?')):
            score -= 10
        
        # Check for excessive repetition
        words = caption.lower().split()
        word_counts = {}
        for word in words:
            if len(word) > 3:  # Only check longer words
                word_counts[word] = word_counts.get(word, 0) + 1
        
        max_repetition = max(word_counts.values()) if word_counts else 1
        if max_repetition > 3:
            score -= 25
        
        return max(0, min(100, score))
    
    def _has_quality_issues(self, caption: str) -> bool:
        """Check for specific quality issues that require review"""
        issues = [
            len(caption) < 20,
            len(caption) > self.max_length - 50,  # Flag earlier for length
            "I can't" in caption.lower(),
            "I don't know" in caption.lower(),
            "unclear" in caption.lower(),
            "not sure" in caption.lower(),
            "a picture of" in caption.lower(),
            "this is an image" in caption.lower()
        ]
        
        return any(issues)
    
    def _generate_feedback(self, caption: str, length_score: int, content_score: int, clarity_score: int) -> str:
        """Generate feedback based on assessment scores"""
        feedback_parts = []
        
        # Length feedback
        length = len(caption)
        if length < 20:
            feedback_parts.append("Caption is too short. Consider adding more descriptive details.")
        elif length > self.max_length:
            feedback_parts.append(f"Caption exceeds maximum length of {self.max_length} characters.")
        elif length > self.optimal_max_length:
            feedback_parts.append("Caption is quite long. Consider making it more concise.")
        
        # Content feedback
        if content_score < 70:
            if any(phrase in caption.lower() for phrase in ["I can't", "I don't know", "unclear"]):
                feedback_parts.append("Caption contains uncertainty phrases. Try to be more definitive.")
            if caption.lower().count("this image") > 1:
                feedback_parts.append("Avoid repetitive phrases like 'this image'.")
        
        # Clarity feedback
        if clarity_score < 70:
            if not caption.rstrip().endswith(('.', '!', '?')):
                feedback_parts.append("Caption should end with proper punctuation.")
            if not caption[0].isupper():
                feedback_parts.append("Caption should start with a capital letter.")
        
        if not feedback_parts:
            feedback_parts.append("Caption quality looks good!")
        
        return " ".join(feedback_parts)

class CaptionQualityManager:
    """
    Manages caption quality assessment and provides utilities for working with caption quality metrics.
    
    This class serves as a central point for caption quality assessment, providing methods to:
    - Assess caption quality using simple heuristics
    - Format quality feedback for display in the UI
    - Generate quality badges and visual indicators
    - Filter and sort captions based on quality metrics
    """
    
    def __init__(self):
        """Initialize the caption quality manager"""
        logger.info("Initializing caption quality manager")
        self.quality_assessor = SimpleCaptionQualityAssessor()
        
    def assess_caption_quality(self, caption: str, image_category: str = None, 
                              prompt_used: str = None) -> Dict[str, Any]:
        """
        Assess the quality of a caption
        
        Args:
            caption: The caption text to assess
            image_category: Optional category of the image (ignored in simplified version)
            prompt_used: Optional prompt used to generate the caption
            
        Returns:
            Dictionary containing quality metrics and overall score
        """
        return self.quality_assessor.assess_caption_quality(
            caption=caption,
            prompt_used=prompt_used
        )
    
    def get_quality_badge_class(self, score: int) -> str:
        """
        Get the appropriate CSS class for a quality score badge
        
        Args:
            score: The quality score (0-100)
            
        Returns:
            CSS class name for the badge
        """
        if score >= 90:
            return "bg-success"
        elif score >= 70:
            return "bg-info"
        elif score >= 40:
            return "bg-warning"
        else:
            return "bg-danger"
    
    def get_quality_level_description(self, quality_level: str) -> str:
        """
        Get a user-friendly description of a quality level
        
        Args:
            quality_level: The quality level string (poor, fair, good, excellent)
            
        Returns:
            User-friendly description
        """
        descriptions = {
            "excellent": "This caption is excellent and ready for use.",
            "good": "This caption is good and likely suitable for use.",
            "fair": "This caption is acceptable but could be improved.",
            "poor": "This caption needs significant improvement."
        }
        
        return descriptions.get(quality_level, "Quality assessment not available.")
    
    def format_feedback_for_display(self, feedback: str) -> str:
        """
        Format feedback for display in the UI
        
        Args:
            feedback: The raw feedback string
            
        Returns:
            HTML-formatted feedback
        """
        if not feedback:
            return ""
        
        # Split into paragraphs
        paragraphs = feedback.split("\n\n")
        
        # Format each paragraph
        formatted_paragraphs = []
        for paragraph in paragraphs:
            # Convert bullet points
            if "• " in paragraph:
                items = paragraph.split("• ")
                bullet_list = "<ul>"
                for item in items:
                    if item.strip():
                        bullet_list += f"<li>{item.strip()}</li>"
                bullet_list += "</ul>"
                formatted_paragraphs.append(bullet_list)
            else:
                formatted_paragraphs.append(f"<p>{paragraph}</p>")
        
        return "".join(formatted_paragraphs)
    
    def get_quality_summary(self, metrics: Dict[str, Any]) -> str:
        """
        Get a concise summary of quality metrics
        
        Args:
            metrics: The quality metrics dictionary
            
        Returns:
            Concise summary string
        """
        if not metrics:
            return "Quality assessment not available"
        
        score = metrics.get('overall_score', 0)
        level = metrics.get('quality_level', 'unknown')
        
        summary = f"Quality: {score}/100 ({level.capitalize()})"
        
        if metrics.get('needs_review', False):
            summary += " - Needs review"
            
        return summary
    
    def should_flag_for_review(self, caption: str, metrics: Dict[str, Any] = None) -> bool:
        """
        Determine if a caption should be flagged for special review
        
        Args:
            caption: The caption text
            metrics: Optional quality metrics dictionary
            
        Returns:
            True if the caption should be flagged for review
        """
        # If we have metrics, use the needs_review flag
        if metrics and 'needs_review' in metrics:
            return metrics['needs_review']
        
        # Otherwise, apply some basic heuristics
        if not caption or len(caption) < 20:
            return True
            
        # Check if close to the maximum character limit (within 15 characters)
        max_length = int(os.getenv("CAPTION_MAX_LENGTH", "500"))
        if len(caption) > max_length - 15:
            return True
            
        # Check for potential issues
        potential_issues = [
            "I can't see", 
            "I don't know",
            "unclear",
            "not sure",
            "cannot determine",
            "unable to",
            "difficult to",
            "hard to tell"
        ]
        
        for issue in potential_issues:
            if issue.lower() in caption.lower():
                return True
                
        return False