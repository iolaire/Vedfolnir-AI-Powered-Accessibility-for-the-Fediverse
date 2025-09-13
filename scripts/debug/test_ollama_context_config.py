#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test script to verify OLLAMA_MODEL_CONTEXT configuration is working correctly.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config

def test_ollama_context_config():
    """Test that OLLAMA_MODEL_CONTEXT is properly loaded and configured"""
    print("=== Testing Ollama Context Configuration ===")
    
    # Load configuration
    try:
        config = Config()
        print("✅ Configuration loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        return False
    
    # Check if ollama config exists
    if not hasattr(config, 'ollama'):
        print("❌ Ollama configuration not found")
        return False
    
    print("✅ Ollama configuration found")
    
    # Check context_size attribute
    if not hasattr(config.ollama, 'context_size'):
        print("❌ context_size attribute not found in ollama config")
        return False
    
    print("✅ context_size attribute found")
    
    # Display configuration values
    print(f"\n📋 Ollama Configuration:")
    print(f"   URL: {config.ollama.url}")
    print(f"   Model: {config.ollama.model_name}")
    print(f"   Timeout: {config.ollama.timeout}s")
    print(f"   Context Size: {config.ollama.context_size}")
    
    # Check environment variable
    env_context = os.getenv('OLLAMA_MODEL_CONTEXT')
    print(f"\n🔧 Environment Variable:")
    print(f"   OLLAMA_MODEL_CONTEXT: {env_context}")
    
    # Verify the value matches
    expected_context = int(env_context) if env_context else 4096
    if config.ollama.context_size == expected_context:
        print(f"✅ Context size matches expected value: {expected_context}")
    else:
        print(f"❌ Context size mismatch. Expected: {expected_context}, Got: {config.ollama.context_size}")
        return False
    
    # Test payload generation (simulate what would be sent to Ollama)
    print(f"\n📤 Simulated Ollama API Payload:")
    payload = {
        "model": config.ollama.model_name,
        "prompt": "Test prompt",
        "images": ["base64_image_data_here"],
        "stream": False,
        "options": {
            "num_ctx": config.ollama.context_size
        }
    }
    
    for key, value in payload.items():
        if key == "images":
            print(f"   {key}: ['<base64_image_data>']")
        else:
            print(f"   {key}: {value}")
    
    print(f"\n✅ All tests passed! Context size configuration is working correctly.")
    return True

if __name__ == "__main__":
    success = test_ollama_context_config()
    sys.exit(0 if success else 1)