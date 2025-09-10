# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
from logging import getLogger
import os
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from app.core.security.core.security_utils import sanitize_for_log

logger = getLogger(__name__)

@dataclass
class FallbackConfig:
    """Configuration for caption generation fallback mechanisms"""
    enabled: bool = True
    max_fallback_attempts: int = 2
    use_simplified_prompts: bool = True
    use_backup_model: bool = True
    backup_model_name: str = "llava:13b-v1.6"  # Default backup model
    
    @classmethod
    def from_env(cls):
        """Create a FallbackConfig from environment variables"""
        return cls(
            enabled=os.getenv("FALLBACK_ENABLED", "true").lower() == "true",
            max_fallback_attempts=int(os.getenv("FALLBACK_MAX_ATTEMPTS", "2")),
            use_simplified_prompts=os.getenv("FALLBACK_USE_SIMPLIFIED_PROMPTS", "true").lower() == "true",
            use_backup_model=os.getenv("FALLBACK_USE_BACKUP_MODEL", "true").lower() == "true",
            backup_model_name=os.getenv("FALLBACK_BACKUP_MODEL", "llava:13b-v1.6"),
        )

class CaptionFallbackManager:
    """
    Manages fallback mechanisms for caption generation
    
    This class provides fallback strategies when the primary caption generation fails:
    1. Retry with the same model but a simplified prompt
    2. Try with a backup model if available
    """
    
    def __init__(self, config: FallbackConfig = None, caption_config=None):
        """
        Initialize the fallback manager
        
        Args:
            config: Optional fallback configuration
            caption_config: Optional caption configuration for max length
        """
        self.config = config or FallbackConfig.from_env()
        
        # Set max length from caption config or environment
        if caption_config:
            self.max_length = caption_config.max_length
        else:
            self.max_length = int(os.getenv("CAPTION_MAX_LENGTH", "500"))
        
        # Simplified prompts for fallback (using configurable max length)
        self.SIMPLIFIED_PROMPTS = {
            "general": f"Describe this image briefly for someone who cannot see it. Keep it under {self.max_length} characters.",
            "portrait": f"Describe this photo of a person or people briefly. Keep it under {self.max_length} characters.",
            "landscape": f"Describe this landscape or outdoor scene briefly. Keep it under {self.max_length} characters.",
            "food": f"Describe this food or drink briefly. Keep it under {self.max_length} characters.",
            "animal": f"Describe this animal briefly. Keep it under {self.max_length} characters.",
            "object": f"Describe this object briefly. Keep it under {self.max_length} characters.",
            "artwork": f"Describe this artwork briefly. Keep it under {self.max_length} characters.",
            "text": f"Describe this text-containing image briefly without transcribing all text. Keep it under {self.max_length} characters."
        }
        
        logger.info(f"Initializing caption fallback manager (enabled: {self.config.enabled}, max_length: {self.max_length})")
        
        if self.config.enabled:
            logger.info(f"Fallback config: max attempts={self.config.max_fallback_attempts}, "
                       f"use simplified prompts={self.config.use_simplified_prompts}, "
                       f"use backup model={self.config.use_backup_model}, "
                       f"backup model={self.config.backup_model_name}")
    
    # Simplified prompts for fallback (moved to __init__ to use configurable max length)
    # SIMPLIFIED_PROMPTS will be set in __init__
    
    # Ultra-simplified fallback prompt as last resort
    ULTRA_SIMPLIFIED_PROMPT = "Describe what you see in this image in a single sentence."

    def get_fallback_prompt(self, original_category: str, fallback_attempt: int) -> str:
        """
        Get a fallback prompt based on the original category and attempt number
        
        Args:
            original_category: The original image category
            fallback_attempt: The current fallback attempt number (1-based)
            
        Returns:
            A simplified prompt for fallback
        """
        if not self.config.use_simplified_prompts:
            return None
            
        # For the last attempt, use the ultra-simplified prompt
        if fallback_attempt >= self.config.max_fallback_attempts:
            logger.info(f"Using ultra-simplified prompt for final fallback attempt")
            return self.ULTRA_SIMPLIFIED_PROMPT
            
        # Map the original category to a simplified category
        simplified_category = self._map_to_simplified_category(original_category)
        
        # Get the simplified prompt
        simplified_prompt = self.SIMPLIFIED_PROMPTS.get(simplified_category, self.SIMPLIFIED_PROMPTS["general"])
        logger.info(f"Using simplified prompt for category '{sanitize_for_log(simplified_category)}' (original: '{sanitize_for_log(original_category)}')")
        
        return simplified_prompt
    
    def get_fallback_model(self, original_model: str, fallback_attempt: int) -> Optional[str]:
        """
        Get a fallback model based on the original model and attempt number
        
        Args:
            original_model: The original model name
            fallback_attempt: The current fallback attempt number (1-based)
            
        Returns:
            A backup model name or None if no backup should be used
        """
        if not self.config.use_backup_model:
            return None
            
        # Only use backup model on the second fallback attempt
        if fallback_attempt < 2:
            return None
            
        # Don't use the same model as backup
        if self.config.backup_model_name == original_model:
            logger.warning(f"Backup model '{self.config.backup_model_name}' is the same as original model, skipping model fallback")
            return None
            
        logger.info(f"Using backup model '{sanitize_for_log(self.config.backup_model_name)}' (original: '{sanitize_for_log(original_model)}')")
        return self.config.backup_model_name
    
    def _map_to_simplified_category(self, category: str) -> str:
        """
        Map a specific category to a more general simplified category
        
        Args:
            category: The original category
            
        Returns:
            A simplified category
        """
        # Map specific categories to more general ones
        portrait_categories = ["portrait", "selfie", "group_photo", "person", "people"]
        landscape_categories = ["landscape", "nature", "cityscape", "beach", "mountain", 
                               "forest", "sunset", "aerial", "underwater", "night"]
        food_categories = ["food", "dessert", "drink", "recipe"]
        animal_categories = ["animal", "pet", "wildlife"]
        artwork_categories = ["artwork", "abstract", "meme", "comic"]
        text_categories = ["document", "chart", "infographic", "screenshot", "quote"]
        
        category = category.lower()
        
        if any(cat in category for cat in portrait_categories):
            return "portrait"
        elif any(cat in category for cat in landscape_categories):
            return "landscape"
        elif any(cat in category for cat in food_categories):
            return "food"
        elif any(cat in category for cat in animal_categories):
            return "animal"
        elif any(cat in category for cat in artwork_categories):
            return "artwork"
        elif any(cat in category for cat in text_categories):
            return "text"
        else:
            return "general"
    
    def should_use_fallback(self, error: Exception = None, quality_metrics: Dict[str, Any] = None) -> bool:
        """
        Determine if fallback mechanisms should be used
        
        Args:
            error: Optional exception that occurred during caption generation
            quality_metrics: Optional quality metrics for a generated caption
            
        Returns:
            True if fallback should be used
        """
        if not self.config.enabled:
            return False
            
        # If there was an error, always use fallback
        if error is not None:
            return True
            
        # If quality metrics indicate poor quality, use fallback
        if quality_metrics is not None:
            # Check if the caption was flagged for review
            if quality_metrics.get('needs_review', False):
                logger.info(f"Caption flagged for review, using fallback (quality score: {sanitize_for_log(str(quality_metrics.get('overall_score', 0)))})")
                return True
                
            # Check if the quality score is below threshold
            score = quality_metrics.get('overall_score', 0)
            if score < 40:  # Poor quality threshold
                logger.info(f"Caption quality below threshold ({sanitize_for_log(str(score))}/100), using fallback")
                return True
                
        return False