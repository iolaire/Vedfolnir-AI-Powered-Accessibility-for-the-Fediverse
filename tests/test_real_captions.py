# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import unittest
import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from caption_formatter import CaptionFormatter

class TestRealCaptions(unittest.TestCase):
    """Test the caption formatter with real-world examples"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.formatter = CaptionFormatter()
    
    def test_real_world_captions(self):
        """Test formatting of real-world captions"""
        test_cases = [
            (
                "a cat sitting on windowsill looking outside. the cat is orange and white",
                "A cat sitting on windowsill looking outside. The cat is orange and white."
            ),
            (
                "this is a landscape photo showing mountains with snow. there is a lake in foreground",
                "This is a landscape photo showing mountains with snow. There is a lake in foreground."
            ),
            (
                "woman holding coffee cup at cafe. she is smiling. the background is blurred",
                "Woman holding coffee cup at cafe. She is smiling. The background is blurred."
            ),
            (
                "sunset over ocean with silhouette of palm trees",
                "Sunset over ocean with silhouette of palm trees."
            ),
            (
                "a plate of food with pasta,tomato sauce and basil leaves",
                "A plate of food with pasta, tomato sauce and basil leaves."
            ),
            (
                "a dog playing in park. it is a golden retriever. the dog is chasing a ball",
                "A dog playing in park. It is a golden retriever. The dog is chasing a ball."
            ),
            (
                "tall skyscraper in new york city. the building has glass windows. it is a sunny day",
                "Tall skyscraper in New York City. The building has glass windows. It is a sunny day."
            ),
            (
                "basically this is a chart showing sales data for different months of the year",
                "This is a chart showing sales data for different months of the year."
            ),
            (
                "a screenshot of a website interface.it shows a login page with username and password fields",
                "A screenshot of a website interface. It shows a login page with username and password fields."
            ),
            (
                "a person hiking on mountain trail. they are wearing a red jacket. the view is spectacular",
                "A person hiking on mountain trail. They are wearing a red jacket. The view is spectacular."
            )
        ]
        
        for original, expected in test_cases:
            formatted = self.formatter.format_caption(original)
            self.assertEqual(formatted, expected, f"Failed on: {original}")
    
    def test_grammar_fixes(self):
        """Test grammar fixes in captions"""
        test_cases = [
            (
                "a apple on table next to a banana",
                "An apple on table next to a banana."
            ),
            (
                "the car is parked in front of the house.it is red",
                "The car is parked in front of the house. It is red."
            ),
            (
                "the the dog is barking at mailman",
                "The dog is barking at mailman."
            ),
            (
                "she can not see the mountain due to fog",
                "She can't see the mountain due to fog."
            ),
            (
                "they are going to the store.they will buy groceries",
                "They are going to the store. They will buy groceries."
            )
        ]
        
        for original, expected in test_cases:
            formatted = self.formatter.format_caption(original)
            self.assertEqual(formatted, expected, f"Failed on: {original}")

if __name__ == '__main__':
    unittest.main()