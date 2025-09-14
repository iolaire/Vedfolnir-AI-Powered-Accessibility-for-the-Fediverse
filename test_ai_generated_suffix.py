# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test script to verify that the AI-generated suffix is properly appended to captions
"""

import sys
import os
from unittest.mock import Mock, patch

# Add the project root to the path
sys.path.insert(0, os.path.abspath('.'))

from app.utils.processing.ollama_caption_generator import OllamaCaptionGenerator
from config import Config

def test_ai_generated_suffix():
    """Test that the AI-generated suffix is properly appended"""
    
    # Create a mock config
    config = Mock()
    config.url = "http://localhost:11434"
    config.model_name = "llava:7b"
    config.timeout = 30.0
    config.context_size = 4096
    config.retry = Mock()
    config.retry.max_attempts = 3
    config.retry.base_delay = 1.0
    config.retry.max_delay = 30.0
    config.retry.backoff_factor = 2.0
    config.retry.jitter = True
    config.retry.jitter_factor = 0.1
    config.retry.retry_on_server_error = True
    config.fallback = Mock()
    config.fallback.enabled = False
    config.caption = Mock()
    config.caption.max_length = 500
    
    # Create the caption generator
    generator = OllamaCaptionGenerator(config)
    
    # Test the _clean_caption method directly
    test_captions = [
        "A beautiful sunset over the mountains",
        "A person walking in the park",
        "This is a very long caption that might need to be truncated because it exceeds the maximum length limit and should be cut off appropriately while still maintaining readability and ensuring that the AI-generated suffix is properly appended at the end of the caption text"
    ]
    
    print("Testing AI-generated suffix appending...")
    
    for i, original_caption in enumerate(test_captions, 1):
        print(f"\nTest {i}:")
        print(f"Original: {original_caption}")
        
        # Mock the caption formatter to return the input unchanged for simplicity
        with patch.object(generator.caption_formatter, 'format_caption', return_value=original_caption):
            cleaned_caption = generator._clean_caption(original_caption)
            
        print(f"Cleaned:  {cleaned_caption}")
        
        # Verify the suffix is appended
        if cleaned_caption.endswith(" (AI-generated)"):
            print("✅ AI-generated suffix correctly appended")
        else:
            print("❌ AI-generated suffix missing!")
            return False
        
        # Verify the total length doesn't exceed the maximum
        if len(cleaned_caption) <= config.caption.max_length:
            print(f"✅ Length check passed ({len(cleaned_caption)}/{config.caption.max_length})")
        else:
            print(f"❌ Length check failed ({len(cleaned_caption)}/{config.caption.max_length})")
            return False
    
    print("\n🎉 All tests passed! AI-generated suffix is working correctly.")
    return True

if __name__ == "__main__":
    success = test_ai_generated_suffix()
    sys.exit(0 if success else 1)