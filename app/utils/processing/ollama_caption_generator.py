# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import logging
import os
import httpx
import base64
import json
import time
from PIL import Image
from typing import Optional, List, Dict, Tuple, Any
import asyncio
from app.utils.processing.caption_quality_assessment import SimpleCaptionQualityAssessor
from app.utils.processing.caption_formatter import CaptionFormatter
from app.utils.processing.caption_fallback import CaptionFallbackManager
from app.utils.helpers.utils import get_retry_stats_summary

logger = logging.getLogger(__name__)

class OllamaCaptionGenerator:
    """Generate image captions using Ollama with llava:7b model"""
    
    def __init__(self, config):
        self.config = config
        self.ollama_url = config.url
        self.model_name = config.model_name
        self.timeout = config.timeout
        self.retry_config = config.retry
        self.fallback_config = config.fallback
        self.caption_quality_assessor = SimpleCaptionQualityAssessor(config.caption)
        self.caption_formatter = CaptionFormatter(config.caption)
        self.fallback_manager = CaptionFallbackManager(config.fallback, config.caption)
        self.model_info = None
        self.connection_validated = False
        self.retry_stats = {
            "attempts": 0,
            "successes": 0,
            "failures": 0,
            "total_retry_time": 0
        }
        self.fallback_stats = {
            "fallback_attempts": 0,
            "fallback_successes": 0,
            "fallback_failures": 0,
            "simplified_prompt_used": 0,
            "backup_model_used": 0
        }
    
    async def initialize(self):
        """Initialize connection to Ollama and validate model availability"""
        try:
            logger.info(f"Connecting to Ollama at {self.ollama_url}")
            logger.info(f"Using model: {self.model_name}")
            logger.info(f"Connection timeout: {self.timeout}s")
            logger.info(f"Model context size: {self.config.context_size}")
            
            # Test connection to Ollama API
            await self._validate_connection()
            
            # Check if the specified model is available
            await self._validate_model()
            
            self.connection_validated = True
            logger.info(f"Successfully connected to Ollama and validated model {self.model_name}")
            
        except httpx.ConnectError as e:
            logger.error(f"Failed to connect to Ollama at {self.ollama_url}: {e}")
            logger.error("Please check that the Ollama server is running and accessible")
            raise
        except httpx.TimeoutException as e:
            logger.error(f"Connection to Ollama timed out: {e}")
            logger.error("Consider increasing the OLLAMA_TIMEOUT value in your environment configuration")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Ollama caption generator: {e}")
            raise
    
    async def _validate_connection(self):
        """Validate connection to Ollama API"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.ollama_url}/api/tags")
                response.raise_for_status()
                
                # Log available models
                models = response.json().get("models", [])
                if models:
                    logger.info(f"Available models on Ollama server: {', '.join([m.get('name', 'unknown') for m in models])}")
                else:
                    logger.warning("No models found on Ollama server")
                
        except Exception as e:
            logger.error(f"Failed to validate connection to Ollama: {e}")
            raise
    
    async def _validate_model(self):
        """Validate that the specified model is available"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Check if model exists using the tags endpoint
                response = await client.get(f"{self.ollama_url}/api/tags")
                response.raise_for_status()
                
                models_data = response.json()
                models = models_data.get("models", [])
                
                # Check if our model is in the list of available models
                model_exists = any(m.get('name') == self.model_name for m in models)
                
                if not model_exists:
                    logger.warning(f"Model {self.model_name} not found in available models")
                    logger.info(f"You may need to pull the model using: ollama pull {self.model_name}")
                else:
                    # Model exists, set basic info
                    matching_model = next((m for m in models if m.get('name') == self.model_name), None)
                    if matching_model:
                        self.model_info = matching_model
                        logger.info(f"Model {self.model_name} is available")
                        
                        # Log model details if available
                        if self.model_info:
                            model_size = self.model_info.get("size", "unknown")
                            model_modified = self.model_info.get("modified_at", "unknown")
                            logger.info(f"Model details - Size: {model_size}, Last modified: {model_modified}")
                    else:
                        logger.info(f"Model {self.model_name} is available but details could not be retrieved")
                
        except Exception as e:
            logger.error(f"Failed to validate model {self.model_name}: {e}")
            raise
    
    def cleanup(self):
        """Clean up resources and log statistics"""
        # Log retry statistics
        if self.retry_stats["attempts"] > 0:
            logger.info("Ollama API call statistics:")
            logger.info(self.get_retry_stats_summary())
        
        # Log fallback statistics
        if self.fallback_stats["fallback_attempts"] > 0:
            logger.info("Fallback mechanism statistics:")
            logger.info(self.get_fallback_stats_summary())
            
        logger.info("Ollama caption generator cleanup completed")
        
    def get_fallback_stats(self) -> Dict[str, Any]:
        """
        Get statistics about fallback attempts
        
        Returns:
            Dictionary with fallback statistics
        """
        stats = self.fallback_stats.copy()
        
        # Calculate success rate
        total_attempts = stats["fallback_attempts"]
        if total_attempts > 0:
            stats["success_rate"] = (stats["fallback_successes"] / total_attempts) * 100
        else:
            stats["success_rate"] = 0
            
        return stats
        
    def get_fallback_stats_summary(self) -> str:
        """
        Get a human-readable summary of fallback statistics
        
        Returns:
            String with fallback statistics summary
        """
        stats = self.get_fallback_stats()
        
        summary = [
            f"Fallback Attempts: {stats['fallback_attempts']} total, {stats['fallback_successes']} successes, {stats['fallback_failures']} failures",
            f"Success Rate: {stats['success_rate']:.1f}%",
            f"Simplified Prompts Used: {stats['simplified_prompt_used']} times",
            f"Backup Models Used: {stats['backup_model_used']} times"
        ]
            
        return "\n".join(summary)
    
    async def generate_caption(self, image_path: str, prompt: str = None) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Generate caption for an image using Ollama with retry and fallback logic"""
        start_time = time.time()
        original_model = self.model_name
        
        # Load and encode image once for all attempts
        try:
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            logger.debug(f"Successfully loaded and encoded image: {image_path}")
        except Exception as e:
            logger.error(f"Failed to load image {image_path}: {e}")
            return None
        
        # Ensure connection is validated before proceeding
        if not self.connection_validated:
            try:
                logger.warning("Connection to Ollama not validated. Initializing...")
                await self.initialize()
            except Exception as e:
                logger.error(f"Failed to initialize Ollama connection: {e}")
                return None
        
        # Use a general prompt if none provided
        if prompt is None:
            prompt = "Describe this image in detail for someone who cannot see it. Focus on the main subjects, their actions, the setting, colors, and any important details that would help someone understand what's happening in the image."
            logger.info(f"Using general prompt for image {image_path}")
        else:
            logger.info(f"Using provided prompt for image {image_path}")
        
        # Try with primary model and prompt first
        result = await self._try_generate_caption(
            image_path=image_path,
            image_data=image_data,
            model_name=self.model_name,
            prompt=prompt
        )
        
        # If primary attempt succeeded, return the result
        if result is not None and result[0] is not None:
            caption, quality_metrics = result
            
            # Check if we should use fallback based on quality
            if not self.fallback_manager.should_use_fallback(quality_metrics=quality_metrics):
                return result
            
            logger.info(f"Primary caption generation succeeded but quality is low. Trying fallback mechanisms.")
        else:
            logger.warning(f"Primary caption generation failed. Trying fallback mechanisms.")
        
        # Try fallback mechanisms if enabled
        if self.fallback_config and self.fallback_config.enabled:
            max_fallback_attempts = self.fallback_config.max_fallback_attempts
            
            for fallback_attempt in range(1, max_fallback_attempts + 1):
                self.fallback_stats["fallback_attempts"] += 1
                logger.info(f"Using fallback mechanism (attempt {fallback_attempt}/{max_fallback_attempts})")
                
                # Get fallback prompt if enabled
                fallback_prompt = None
                if self.fallback_config.use_simplified_prompts:
                    fallback_prompt = self.fallback_manager.get_fallback_prompt(
                        original_category="general",
                        fallback_attempt=fallback_attempt
                    )
                    
                    if fallback_prompt:
                        logger.info(f"Using simplified fallback prompt: {fallback_prompt[:50]}...")
                        self.fallback_stats["simplified_prompt_used"] += 1
                
                # Get fallback model if enabled and this is the appropriate attempt
                fallback_model = None
                if self.fallback_config.use_backup_model:
                    fallback_model = self.fallback_manager.get_fallback_model(
                        original_model=original_model,
                        fallback_attempt=fallback_attempt
                    )
                    
                    if fallback_model:
                        logger.info(f"Using backup model: {fallback_model}")
                        self.fallback_stats["backup_model_used"] += 1
                
                # Use the fallback prompt and/or model
                current_prompt = fallback_prompt or prompt
                current_model = fallback_model or self.model_name
                
                # Try with fallback settings
                fallback_result = await self._try_generate_caption(
                    image_path=image_path,
                    image_data=image_data,
                    model_name=current_model,
                    prompt=current_prompt
                )
                
                # If fallback succeeded, return the result
                if fallback_result is not None and fallback_result[0] is not None:
                    self.fallback_stats["fallback_successes"] += 1
                    logger.info(f"Fallback caption generation succeeded on attempt {fallback_attempt}")
                    return fallback_result
            
            # All fallback attempts failed
            self.fallback_stats["fallback_failures"] += 1
            logger.error(f"All fallback attempts failed for {image_path}")
        
        # If we got here, all attempts (primary and fallbacks) failed
        return None
    
    async def _try_generate_caption(self, image_path: str, image_data: str, model_name: str, 
                                   prompt: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Try to generate a caption with specific model and prompt
        
        Args:
            image_path: Path to the image file
            image_data: Base64-encoded image data
            model_name: Model name to use
            prompt: Prompt to use
            
        Returns:
            Tuple of (caption, quality_metrics) or None if failed
        """
        start_time = time.time()
        
        # Prepare request for Ollama
        payload = {
            "model": model_name,
            "prompt": prompt,
            "images": [image_data],
            "stream": False,
            "options": {
                "num_ctx": self.config.context_size
            }
        }
        
        logger.debug(f"Sending request to Ollama API at {self.ollama_url}/api/generate")
        logger.debug(f"Using model: {model_name}")
        logger.debug(f"Prompt length: {len(prompt)} characters")
        logger.debug(f"Context size (num_ctx): {self.config.context_size}")
        
        # Send request to Ollama with retry logic
        max_attempts = self.retry_config.max_attempts if self.retry_config else 3
        base_delay = self.retry_config.base_delay if self.retry_config else 1.0
        max_delay = self.retry_config.max_delay if self.retry_config else 30.0
        backoff_factor = self.retry_config.backoff_factor if self.retry_config else 2.0
        jitter = self.retry_config.jitter if self.retry_config else True
        jitter_factor = self.retry_config.jitter_factor if self.retry_config else 0.1
        
        attempt = 0
        last_error = None
        
        while attempt < max_attempts:
            attempt += 1
            self.retry_stats["attempts"] += 1
            
            try:
                logger.debug(f"Caption generation attempt {attempt}/{max_attempts} for {image_path}")
                
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.ollama_url}/api/generate",
                        json=payload
                    )
                    response.raise_for_status()
                    
                    result = response.json()
                    generated_text = result.get('response', '').strip()
                    
                    # Log model performance metrics if available
                    if 'eval_count' in result:
                        logger.debug(f"Model metrics - Eval count: {result.get('eval_count')}, " +
                                    f"Eval duration: {result.get('eval_duration', 0)}ms")
                    
                    # Clean up the caption
                    caption = self._clean_caption(generated_text)
                    
                    # Log the generated caption
                    logger.info(f"Generated caption: {caption[:100]}...")
                    
                    # Assess caption quality
                    quality_metrics = self.assess_caption_quality(
                        caption=caption,
                        prompt_used=prompt
                    )
                    
                    logger.info(f"Caption quality score: {quality_metrics['overall_score']}/100 ({quality_metrics['quality_level']})")
                    if quality_metrics['needs_review']:
                        logger.warning(f"Caption flagged for special review: {quality_metrics['feedback']}")
                    
                    # Update retry stats
                    self.retry_stats["successes"] += 1
                    
                    # Log performance
                    duration = time.time() - start_time
                    logger.debug(f"Caption generation for {image_path} completed in {duration:.2f}s")
                    
                    # Return caption with quality metrics
                    return caption, quality_metrics
                    
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_error = e
                logger.warning(f"Connection error on attempt {attempt}/{max_attempts}: {e}")
                
                if attempt >= max_attempts:
                    break
                    
                # Calculate backoff delay with optional jitter
                delay = min(base_delay * (backoff_factor ** (attempt - 1)), max_delay)
                
                if jitter:
                    # Add jitter to avoid thundering herd problem
                    jitter_amount = delay * jitter_factor
                    delay = delay + (jitter_amount * (2 * asyncio.get_event_loop().time() % 1 - 1))
                
                logger.info(f"Retrying in {delay:.2f}s...")
                await asyncio.sleep(delay)
                
            except httpx.HTTPStatusError as e:
                last_error = e
                logger.warning(f"HTTP error on attempt {attempt}/{max_attempts}: {e}")
                
                # Check if we should retry based on status code
                status_code = e.response.status_code
                retry_on_server_error = self.retry_config.retry_on_server_error if self.retry_config else True
                
                if status_code >= 500 and retry_on_server_error and attempt < max_attempts:
                    delay = min(base_delay * (backoff_factor ** (attempt - 1)), max_delay)
                    logger.info(f"Server error {status_code}, retrying in {delay:.2f}s...")
                    await asyncio.sleep(delay)
                else:
                    # Don't retry client errors or if we've reached max attempts
                    logger.error(f"HTTP error {status_code}, not retrying: {e}")
                    break
                    
            except Exception as e:
                last_error = e
                logger.error(f"Unexpected error on attempt {attempt}/{max_attempts}: {e}")
                
                if attempt >= max_attempts:
                    break
                    
                # Calculate backoff delay
                delay = min(base_delay * (backoff_factor ** (attempt - 1)), max_delay)
                logger.info(f"Retrying in {delay:.2f}s...")
                await asyncio.sleep(delay)
        
        # All attempts failed
        self.retry_stats["failures"] += 1
        self.retry_stats["total_retry_time"] += (time.time() - start_time)
        
        logger.error(f"Failed to generate caption after {max_attempts} attempts for {image_path}")
        logger.error(f"Last error: {last_error}")
        
        return None
    
    def _clean_caption(self, caption: str) -> str:
        """Clean and format the generated caption"""
        # Remove common artifacts
        caption = caption.strip()
        
        # Remove repeated phrases
        lines = caption.split('\n')
        caption = lines[0] if lines else caption
        
        # Basic cleaning before passing to formatter
        max_length = self.config.caption.max_length if self.config.caption else int(os.getenv("CAPTION_MAX_LENGTH", "500"))
        
        # Reserve space for "(AI-generated)" suffix (15 characters)
        ai_suffix = " (AI-generated)"
        effective_max_length = max_length - len(ai_suffix)
        
        if len(caption) > effective_max_length:
            # Try to cut at a sentence boundary
            sentences = caption.split('. ')
            if len(sentences) > 1:
                truncated = sentences[0] + '.'
                if len(truncated) <= effective_max_length:
                    caption = truncated
                else:
                    caption = caption[:effective_max_length - 3] + '...'
            else:
                caption = caption[:effective_max_length - 3] + '...'
        
        # Apply enhanced formatting and grammar checking
        logger.debug(f"Original caption after basic cleaning: {caption}")
        formatted_caption = self.caption_formatter.format_caption(caption)
        logger.debug(f"Caption after enhanced formatting: {formatted_caption}")
        
        # Append AI-generated suffix
        final_caption = formatted_caption + ai_suffix
        logger.debug(f"Final caption with AI-generated suffix: {final_caption}")
        
        return final_caption
    
    async def generate_multiple_captions(self, image_paths: List[str]) -> List[Tuple[Optional[str], Optional[Dict[str, Any]]]]:
        """Generate captions for multiple images
        
        Returns:
            List of tuples containing (caption, quality_metrics) for each image
        """
        results = []
        
        for image_path in image_paths:
            result = await self.generate_caption(image_path)
            
            # Handle both new format (caption, quality_metrics) and old format (just caption)
            if isinstance(result, tuple) and len(result) == 2:
                caption, quality_metrics = result
            else:
                caption = result
                quality_metrics = None
                
            results.append((caption, quality_metrics))
            
            # Small delay to prevent overwhelming Ollama
            await asyncio.sleep(0.5)
        
        return results

    def get_retry_stats(self) -> Dict[str, Any]:
        """
        Get statistics about retry attempts
        
        Returns:
            Dictionary with retry statistics
        """
        stats = self.retry_stats.copy()
        
        # Calculate success rate
        total_attempts = stats["attempts"]
        if total_attempts > 0:
            stats["success_rate"] = (stats["successes"] / total_attempts) * 100
        else:
            stats["success_rate"] = 0
            
        # Calculate average retry time
        if stats["failures"] > 0:
            stats["avg_retry_time"] = stats["total_retry_time"] / stats["failures"]
        else:
            stats["avg_retry_time"] = 0
            
        return stats
        
    def get_retry_stats_summary(self) -> str:
        """
        Get a human-readable summary of retry statistics
        
        Returns:
            String with retry statistics summary
        """
        stats = self.get_retry_stats()
        
        summary = [
            f"Ollama API Calls: {stats['attempts']} attempts, {stats['successes']} successes, {stats['failures']} failures",
            f"Success Rate: {stats['success_rate']:.1f}%"
        ]
        
        if stats["failures"] > 0:
            summary.append(f"Average Retry Time: {stats['avg_retry_time']:.2f}s")
            
        return "\n".join(summary)
        
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model
        
        Returns:
            Dictionary with model information or None if not available
        """
        return self.model_info
        
    def assess_caption_quality(self, caption: str, prompt_used: str = None) -> Dict[str, Any]:
        """
        Assess the quality of a generated caption
        
        Args:
            caption: The caption text to assess
            prompt_used: Optional prompt used to generate the caption
            
        Returns:
            Dictionary containing quality metrics and overall score
        """
        return self.caption_quality_assessor.assess_caption_quality(
            caption=caption,
            prompt_used=prompt_used
        )
    
    async def test_connection(self) -> bool:
        """
        Test connection to Ollama service
        
        Returns:
            bool: True if connection is successful
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.ollama_url}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.debug(f"Connection test failed: {e}")
            return False
    
    async def test_model_availability(self) -> bool:
        """
        Test if the configured model is available
        
        Returns:
            bool: True if model is available
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.ollama_url}/api/tags")
                if response.status_code != 200:
                    return False
                
                data = response.json()
                models = data.get('models', [])
                
                # Check if our model is in the list
                for model in models:
                    if model.get('name', '').startswith(self.model_name):
                        return True
                
                return False
                
        except Exception as e:
            logger.debug(f"Model availability test failed: {e}")
            return False