# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import unittest
import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from caption_formatter import CaptionFormatter

class TestCaptionFormatter(unittest.TestCase):
    """Test the caption formatter functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.formatter = CaptionFormatter()
    
    def test_capitalization(self):
        """Test capitalization fixes"""
        # Test first letter capitalization
        self.assertEqual(
            self.formatter._fix_capitalization("this should be capitalized."),
            "This should be capitalized."
        )
        
        # Test capitalization after periods
        self.assertEqual(
            self.formatter._fix_capitalization("First sentence. second sentence."),
            "First sentence. Second sentence."
        )
        
        # Test proper noun capitalization
        self.assertEqual(
            self.formatter._fix_capitalization("i went to new york on monday."),
            "I went to new york on Monday."
        )
    
    def test_punctuation(self):
        """Test punctuation fixes"""
        # Test adding final period
        self.assertEqual(
            self.formatter.format_caption("This needs a period"),
            "This needs a period."
        )
        
        # Test spacing after punctuation
        self.assertEqual(
            self.formatter.format_caption("Hello,world"),
            "Hello, world"
        )
        
        # Test multiple spaces
        self.assertEqual(
            self.formatter.format_caption("Too  many    spaces"),
            "Too many spaces"
        )
        
        # Test spaces before punctuation
        self.assertEqual(
            self.formatter.format_caption("Wrong space ."),
            "Wrong space."
        )
    
    def test_common_errors(self):
        """Test common error fixes"""
        # Test a/an usage directly with format_caption
        self.assertEqual(
            self.formatter.format_caption("a apple"),
            "an apple"
        )
        self.assertEqual(
            self.formatter.format_caption("an banana"),
            "a banana"
        )
        
        # Test contractions
        self.assertEqual(
            self.formatter.format_caption("I can not see it"),
            "I can't see it"
        )
        self.assertEqual(
            self.formatter.format_caption("It is raining"),
            "It's raining"
        )
    
    def test_sentence_structure(self):
        """Test sentence structure improvements"""
        # Test redundant phrase removal
        self.assertEqual(
            self.formatter.format_caption("Basically, the image shows a cat."),
            "The image shows a cat."
        )
        
        # Test double word removal
        self.assertEqual(
            self.formatter.format_caption("The the cat is sleeping."),
            "The cat is sleeping."
        )
    
    def test_format_caption_integration(self):
        """Test the full caption formatting process"""
        original_caption = "a image of a cat sitting on a windowsill. it is looking outside. the cat is orange and white in color"
        expected_caption = "An image of a cat sitting on a windowsill. It is looking outside. The cat is orange and white in color."
        
        formatted_caption = self.formatter.format_caption(original_caption)
        self.assertEqual(formatted_caption, expected_caption)
    
    def test_long_caption_truncation(self):
        """Test truncation of long captions"""
        # Create a very long caption
        long_caption = "This is a very long caption that exceeds the maximum length allowed for alt text. " * 5
        
        formatted_caption = self.formatter.format_caption(long_caption)
        # Use configurable max length or default
        max_length = int(os.getenv("CAPTION_MAX_LENGTH", "500"))
        self.assertLessEqual(len(formatted_caption), max_length)
        self.assertTrue(formatted_caption.endswith("..."))

if __name__ == '__main__':
    unittest.main()