# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Simple Ollama Connection Test

This script tests the Ollama connection without the complex TaskGroup setup
to isolate the connection issue.
"""

import asyncio
import httpx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_ollama_simple():
    """Simple test of Ollama connection"""
    ollama_url = "http://localhost:11434"
    timeout = 60.0
    
    try:
        logger.info(f"Testing connection to {ollama_url}")
        
        # Test 1: Basic connection
        async with httpx.AsyncClient(timeout=timeout) as client:
            logger.info("Testing /api/tags endpoint...")
            response = await client.get(f"{ollama_url}/api/tags")
            response.raise_for_status()
            
            models = response.json().get("models", [])
            logger.info(f"Found {len(models)} models")
            
            for model in models:
                logger.info(f"  - {model.get('name', 'unknown')}")
        
        # Test 2: Model validation
        async with httpx.AsyncClient(timeout=timeout) as client:
            logger.info("Testing model validation...")
            response = await client.get(f"{ollama_url}/api/tags")
            response.raise_for_status()
            
            models_data = response.json()
            models = models_data.get("models", [])
            
            target_model = "llava:7b"
            model_exists = any(m.get('name') == target_model for m in models)
            
            if model_exists:
                logger.info(f"✅ Model {target_model} is available")
            else:
                logger.warning(f"❌ Model {target_model} not found")
        
        logger.info("✅ All tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_ollama_simple())
    exit(0 if success else 1)