#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test script for Server-Sent Events implementation
"""

import requests
import time

def test_sse_endpoint():
    """Test the SSE endpoint"""
    print("Testing SSE endpoint...")
    
    # Test with a dummy task ID
    url = "http://localhost:5000/api/progress_stream/test-task-123"
    
    try:
        response = requests.get(url, stream=True, timeout=10)
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("SSE endpoint is working!")
            print("Streaming data:")
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    print(f"  {line}")
                    # Stop after a few lines for testing
                    break
        else:
            print(f"Error: {response.status_code} - {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_sse_endpoint()