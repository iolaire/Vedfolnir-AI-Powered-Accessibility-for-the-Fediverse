# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
Comprehensive tests for Mastodon media processing functionality.

This module tests the Mastodon platform adapter's media processing capabilities
according to task 10.3.3 requirements.
"""

import unittest
from unittest.mock import MagicMock, patch
from app.services.activitypub.components.activitypub_platforms import MastodonPlatform, PixelfedPlatform, PlatformAdapterError

class TestMastodonMediaProcessing(unittest.TestCase):
    """Test Mastodon media attachment processing functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = MagicMock()
        self.config.instance_url = "https://mastodon.social"
        self.config.access_token = "test_token"
        self.config.api_type = "mastodon"
        self.config.client_key = "test_client_key"
        self.config.client_secret = "test_client_secret"
        
        self.adapter = MastodonPlatform(self.config)
    
    def test_parse_mastodon_media_attachment_json_structure(self):
        """Test parsing of Mastodon media attachment JSON structure"""
        # Standard Mastodon media attachment structure
        post = {
            "id": "https://mastodon.social/@user/123456789",
            "type": "Note",
            "content": "Test post with image",
            "published": "2023-01-01T12:00:00Z",
            "attachment": [
                {
                    "type": "Document",
                    "mediaType": "image/jpeg",
                    "url": "https://mastodon.social/media/image1.jpg",
                    "preview_url": "https://mastodon.social/media/preview1.jpg",
                    "name": "",  # Empty alt text
                    "id": "media123",
                    "meta": {
                        "original": {
                            "width": 1920,
                            "height": 1080,
                            "size": "1920x1080",
                            "aspect": 1.777777777777778,
                            "mime_type": "image/jpeg"
                        },
                        "small": {
                            "width": 400,
                            "height": 225,
                            "size": "400x225",
                            "aspect": 1.777777777777778
                        }
                    },
                    "blurhash": "UBL_:rOpGG-;~qRjWBay"
                }
            ]
        }
        
        images = self.adapter.extract_images_from_post(post)
        
        self.assertEqual(len(images), 1)
        image = images[0]
        
        # Test basic structure parsing
        self.assertEqual(image['url'], "https://mastodon.social/media/image1.jpg")
        self.assertEqual(image['mediaType'], "image/jpeg")
        self.assertEqual(image['image_post_id'], "media123")
        self.assertEqual(image['attachment_index'], 0)
        self.assertEqual(image['post_published'], "2023-01-01T12:00:00Z")
        
        # Test attachment_data contains full attachment info
        self.assertIn('attachment_data', image)
        self.assertEqual(image['attachment_data']['id'], "media123")
        self.assertEqual(image['attachment_data']['meta']['original']['width'], 1920)
    
    def test_identify_images_vs_other_media_types(self):
        """Test identification of images vs other media types (video, audio)"""
        post = {
            "id": "https://mastodon.social/@user/123456789",
            "type": "Note",
            "attachment": [
                {
                    "type": "Document",
                    "mediaType": "image/jpeg",
                    "url": "https://mastodon.social/media/image.jpg",
                    "name": "",
                    "id": "image123"
                },
                {
                    "type": "Document",
                    "mediaType": "video/mp4",
                    "url": "https://mastodon.social/media/video.mp4",
                    "name": "",
                    "id": "video123"
                },
                {
                    "type": "Document",
                    "mediaType": "audio/mp3",
                    "url": "https://mastodon.social/media/audio.mp3",
                    "name": "",
                    "id": "audio123"
                },
                {
                    "type": "Document",
                    "mediaType": "image/png",
                    "url": "https://mastodon.social/media/image2.png",
                    "name": "",
                    "id": "image456"
                },
                {
                    "type": "Document",
                    "mediaType": "application/pdf",
                    "url": "https://mastodon.social/media/document.pdf",
                    "name": "",
                    "id": "doc123"
                }
            ]
        }
        
        images = self.adapter.extract_images_from_post(post)
        
        # Should only extract the 2 image attachments
        self.assertEqual(len(images), 2)
        
        # Check that only images are extracted
        image_ids = [img['image_post_id'] for img in images]
        self.assertIn("image123", image_ids)
        self.assertIn("image456", image_ids)
        self.assertNotIn("video123", image_ids)
        self.assertNotIn("audio123", image_ids)
        self.assertNotIn("doc123", image_ids)
        
        # Check media types
        media_types = [img['mediaType'] for img in images]
        self.assertIn("image/jpeg", media_types)
        self.assertIn("image/png", media_types)
    
    def test_detect_images_with_existing_alt_text_should_be_skipped(self):
        """Test detection of images with existing alt text (should be skipped)"""
        post = {
            "id": "https://mastodon.social/@user/123456789",
            "type": "Note",
            "attachment": [
                {
                    "type": "Document",
                    "mediaType": "image/jpeg",
                    "url": "https://mastodon.social/media/image1.jpg",
                    "name": "A beautiful sunset over the ocean",  # Has alt text
                    "id": "image123"
                },
                {
                    "type": "Document",
                    "mediaType": "image/png",
                    "url": "https://mastodon.social/media/image2.png",
                    "name": "   ",  # Only whitespace - should be processed
                    "id": "image456"
                },
                {
                    "type": "Document",
                    "mediaType": "image/gif",
                    "url": "https://mastodon.social/media/image3.gif",
                    "name": "",  # Empty - should be processed
                    "id": "image789"
                }
            ]
        }
        
        images = self.adapter.extract_images_from_post(post)
        
        # Should only extract images without proper alt text (2 images)
        self.assertEqual(len(images), 2)
        
        # Check that image with alt text is skipped
        image_ids = [img['image_post_id'] for img in images]
        self.assertNotIn("image123", image_ids)  # Has alt text, should be skipped
        self.assertIn("image456", image_ids)     # Whitespace only, should be processed
        self.assertIn("image789", image_ids)     # Empty, should be processed
    
    def test_detect_images_without_alt_text_should_be_processed(self):
        """Test detection of images without alt text (should be processed)"""
        post = {
            "id": "https://mastodon.social/@user/123456789",
            "type": "Note",
            "attachment": [
                {
                    "type": "Document",
                    "mediaType": "image/jpeg",
                    "url": "https://mastodon.social/media/image1.jpg",
                    "name": "",  # Empty string
                    "id": "image123"
                },
                {
                    "type": "Document",
                    "mediaType": "image/png",
                    "url": "https://mastodon.social/media/image2.png",
                    "name": None,  # None value
                    "id": "image456"
                },
                {
                    "type": "Document",
                    "mediaType": "image/webp",
                    "url": "https://mastodon.social/media/image3.webp",
                    # Missing 'name' field entirely
                    "id": "image789"
                }
            ]
        }
        
        images = self.adapter.extract_images_from_post(post)
        
        # All 3 images should be processed (no alt text)
        self.assertEqual(len(images), 3)
        
        image_ids = [img['image_post_id'] for img in images]
        self.assertIn("image123", image_ids)
        self.assertIn("image456", image_ids)
        self.assertIn("image789", image_ids)
    
    def test_extract_image_urls_from_different_mastodon_media_formats(self):
        """Test extraction of image URLs from different Mastodon media formats"""
        # Test different URL formats that Mastodon might use
        post = {
            "id": "https://mastodon.social/@user/123456789",
            "type": "Note",
            "attachment": [
                {
                    "type": "Document",
                    "mediaType": "image/jpeg",
                    "url": "https://mastodon.social/media/image1.jpg",  # Direct URL
                    "name": "",
                    "id": "image123"
                },
                {
                    "type": "Document",
                    "mediaType": "image/png",
                    "href": "https://mastodon.social/media/image2.png",  # href instead of url
                    "name": "",
                    "id": "image456"
                },
                {
                    "type": "Document",
                    "mediaType": "image/gif",
                    "url": {
                        "href": "https://mastodon.social/media/image3.gif"  # URL as object
                    },
                    "name": "",
                    "id": "image789"
                }
            ]
        }
        
        images = self.adapter.extract_images_from_post(post)
        
        self.assertEqual(len(images), 3)
        
        # Check URL extraction for different formats
        urls = [img['url'] for img in images]
        self.assertIn("https://mastodon.social/media/image1.jpg", urls)
        self.assertIn("https://mastodon.social/media/image2.png", urls)
        self.assertIn("https://mastodon.social/media/image3.gif", urls)
    
    def test_extract_image_metadata_dimensions_file_type(self):
        """Test extraction of image metadata (dimensions, file type, etc.)"""
        post = {
            "id": "https://mastodon.social/@user/123456789",
            "type": "Note",
            "attachment": [
                {
                    "type": "Document",
                    "mediaType": "image/jpeg",
                    "url": "https://mastodon.social/media/image1.jpg",
                    "name": "",
                    "id": "image123",
                    "meta": {
                        "original": {
                            "width": 1920,
                            "height": 1080,
                            "size": "1920x1080",
                            "aspect": 1.777777777777778,
                            "mime_type": "image/jpeg"
                        },
                        "small": {
                            "width": 400,
                            "height": 225,
                            "size": "400x225",
                            "aspect": 1.777777777777778
                        }
                    },
                    "blurhash": "UBL_:rOpGG-;~qRjWBay",
                    "preview_url": "https://mastodon.social/media/preview1.jpg"
                }
            ]
        }
        
        images = self.adapter.extract_images_from_post(post)
        
        self.assertEqual(len(images), 1)
        image = images[0]
        
        # Check that metadata is preserved in attachment_data
        attachment_data = image['attachment_data']
        self.assertIn('meta', attachment_data)
        self.assertIn('blurhash', attachment_data)
        self.assertIn('preview_url', attachment_data)
        
        # Check specific metadata values
        meta = attachment_data['meta']
        self.assertEqual(meta['original']['width'], 1920)
        self.assertEqual(meta['original']['height'], 1080)
        self.assertEqual(meta['original']['mime_type'], "image/jpeg")
        self.assertEqual(attachment_data['blurhash'], "UBL_:rOpGG-;~qRjWBay")
        self.assertEqual(attachment_data['preview_url'], "https://mastodon.social/media/preview1.jpg")
    
    def test_handle_malformed_or_incomplete_media_attachment_data(self):
        """Test handling of malformed or incomplete media attachment data"""
        # Test various malformed/incomplete scenarios
        test_cases = [
            {
                "name": "missing_type",
                "attachment": {
                    "mediaType": "image/jpeg",
                    "url": "https://mastodon.social/media/image1.jpg",
                    "name": "",
                    "id": "image123"
                    # Missing 'type' field
                },
                "should_extract": False
            },
            {
                "name": "missing_mediaType",
                "attachment": {
                    "type": "Document",
                    "url": "https://mastodon.social/media/image2.jpg",
                    "name": "",
                    "id": "image456"
                    # Missing 'mediaType' field
                },
                "should_extract": False
            },
            {
                "name": "missing_url_and_href",
                "attachment": {
                    "type": "Document",
                    "mediaType": "image/jpeg",
                    "name": "",
                    "id": "image789"
                    # Missing both 'url' and 'href' fields
                },
                "should_extract": True  # Should still extract but with None URL
            },
            {
                "name": "missing_id",
                "attachment": {
                    "type": "Document",
                    "mediaType": "image/jpeg",
                    "url": "https://mastodon.social/media/image4.jpg",
                    "name": ""
                    # Missing 'id' field
                },
                "should_extract": True  # Should still extract but with None ID
            },
            {
                "name": "wrong_type",
                "attachment": {
                    "type": "Link",  # Wrong type
                    "mediaType": "image/jpeg",
                    "url": "https://mastodon.social/media/image5.jpg",
                    "name": "",
                    "id": "image101112"
                },
                "should_extract": False
            }
        ]
        
        for test_case in test_cases:
            with self.subTest(case=test_case["name"]):
                post = {
                    "id": "https://mastodon.social/@user/123456789",
                    "type": "Note",
                    "attachment": [test_case["attachment"]]
                }
                
                images = self.adapter.extract_images_from_post(post)
                
                if test_case["should_extract"]:
                    self.assertEqual(len(images), 1, f"Should extract image for case: {test_case['name']}")
                else:
                    self.assertEqual(len(images), 0, f"Should not extract image for case: {test_case['name']}")
    
    def test_process_different_image_formats_supported_by_mastodon(self):
        """Test processing of different image formats supported by Mastodon"""
        # Common image formats supported by Mastodon
        image_formats = [
            ("image/jpeg", "jpg"),
            ("image/png", "png"),
            ("image/gif", "gif"),
            ("image/webp", "webp"),
            ("image/avif", "avif"),
            ("image/heic", "heic"),
            ("image/bmp", "bmp"),
            ("image/tiff", "tiff")
        ]
        
        attachments = []
        for i, (media_type, ext) in enumerate(image_formats):
            attachments.append({
                "type": "Document",
                "mediaType": media_type,
                "url": f"https://mastodon.social/media/image{i}.{ext}",
                "name": "",
                "id": f"image{i}"
            })
        
        post = {
            "id": "https://mastodon.social/@user/123456789",
            "type": "Note",
            "attachment": attachments
        }
        
        images = self.adapter.extract_images_from_post(post)
        
        # All image formats should be extracted
        self.assertEqual(len(images), len(image_formats))
        
        # Check that all media types are preserved
        extracted_media_types = [img['mediaType'] for img in images]
        for media_type, _ in image_formats:
            self.assertIn(media_type, extracted_media_types)
    
    def test_edge_cases_empty_media_arrays_or_null_values(self):
        """Test edge cases like empty media arrays or null values"""
        test_cases = [
            {
                "name": "empty_attachment_array",
                "post": {
                    "id": "https://mastodon.social/@user/123456789",
                    "type": "Note",
                    "attachment": []
                },
                "expected_count": 0
            },
            {
                "name": "missing_attachment_field",
                "post": {
                    "id": "https://mastodon.social/@user/123456789",
                    "type": "Note"
                    # No 'attachment' field
                },
                "expected_count": 0
            },
            {
                "name": "null_attachment_field",
                "post": {
                    "id": "https://mastodon.social/@user/123456789",
                    "type": "Note",
                    "attachment": None
                },
                "expected_count": 0
            },
            {
                "name": "single_attachment_not_array",
                "post": {
                    "id": "https://mastodon.social/@user/123456789",
                    "type": "Note",
                    "attachment": {
                        "type": "Document",
                        "mediaType": "image/jpeg",
                        "url": "https://mastodon.social/media/image.jpg",
                        "name": "",
                        "id": "image123"
                    }
                },
                "expected_count": 1
            },
            {
                "name": "attachment_with_null_elements",
                "post": {
                    "id": "https://mastodon.social/@user/123456789",
                    "type": "Note",
                    "attachment": [
                        None,
                        {
                            "type": "Document",
                            "mediaType": "image/jpeg",
                            "url": "https://mastodon.social/media/image.jpg",
                            "name": "",
                            "id": "image123"
                        },
                        None
                    ]
                },
                "expected_count": 1
            }
        ]
        
        for test_case in test_cases:
            with self.subTest(case=test_case["name"]):
                images = self.adapter.extract_images_from_post(test_case["post"])
                self.assertEqual(len(images), test_case["expected_count"], 
                               f"Failed for case: {test_case['name']}")
    
    def test_comprehensive_mastodon_media_scenarios(self):
        """Create comprehensive test fixtures with various Mastodon media scenarios"""
        # Complex real-world scenario with mixed media types and conditions
        post = {
            "id": "https://mastodon.social/@photographer/987654321",
            "type": "Note",
            "content": "Mixed media post with photos and videos #photography",
            "published": "2023-12-01T15:30:00Z",
            "attachment": [
                {
                    "type": "Document",
                    "mediaType": "image/jpeg",
                    "url": "https://files.mastodon.social/media_attachments/files/111/234/567/890/original/photo1.jpg",
                    "preview_url": "https://files.mastodon.social/media_attachments/files/111/234/567/890/small/photo1.jpg",
                    "name": "A stunning landscape photo",  # Has alt text - should be skipped
                    "id": "111234567890",
                    "meta": {
                        "original": {
                            "width": 4032,
                            "height": 3024,
                            "size": "4032x3024",
                            "aspect": 1.333333,
                            "mime_type": "image/jpeg"
                        },
                        "small": {
                            "width": 533,
                            "height": 400,
                            "size": "533x400",
                            "aspect": 1.3325
                        }
                    },
                    "blurhash": "UeH2]kRjM{of~qayWBay%MofRjWB"
                },
                {
                    "type": "Document",
                    "mediaType": "image/png",
                    "url": "https://files.mastodon.social/media_attachments/files/111/234/567/891/original/screenshot.png",
                    "preview_url": "https://files.mastodon.social/media_attachments/files/111/234/567/891/small/screenshot.png",
                    "name": "",  # Empty alt text - should be processed
                    "id": "111234567891",
                    "meta": {
                        "original": {
                            "width": 1920,
                            "height": 1080,
                            "size": "1920x1080",
                            "aspect": 1.777778,
                            "mime_type": "image/png"
                        }
                    }
                },
                {
                    "type": "Document",
                    "mediaType": "video/mp4",
                    "url": "https://files.mastodon.social/media_attachments/files/111/234/567/892/original/video.mp4",
                    "preview_url": "https://files.mastodon.social/media_attachments/files/111/234/567/892/small/video.jpg",
                    "name": "",  # Video - should not be processed
                    "id": "111234567892",
                    "meta": {
                        "length": "0:00:30.00",
                        "duration": 30.0,
                        "fps": 30,
                        "size": "1280x720",
                        "width": 1280,
                        "height": 720,
                        "aspect": 1.777778,
                        "audio_encode": "aac",
                        "audio_bitrate": "44100 Hz",
                        "audio_channels": "stereo"
                    }
                },
                {
                    "type": "Document",
                    "mediaType": "image/gif",
                    "url": "https://files.mastodon.social/media_attachments/files/111/234/567/893/original/animated.gif",
                    "name": "   \n  \t  ",  # Whitespace only - should be processed
                    "id": "111234567893",
                    "meta": {
                        "original": {
                            "width": 500,
                            "height": 500,
                            "size": "500x500",
                            "aspect": 1.0,
                            "mime_type": "image/gif"
                        }
                    }
                }
            ],
            "mastodon": {
                "status_id": "987654321",
                "visibility": "public",
                "sensitive": False,
                "account": {
                    "id": "123456",
                    "username": "photographer",
                    "display_name": "Nature Photographer"
                }
            }
        }
        
        images = self.adapter.extract_images_from_post(post)
        
        # Should extract 2 images (PNG screenshot and GIF) - skip JPEG with alt text and MP4 video
        self.assertEqual(len(images), 2)
        
        # Check extracted images
        image_ids = [img['image_post_id'] for img in images]
        self.assertIn("111234567891", image_ids)  # PNG screenshot
        self.assertIn("111234567893", image_ids)  # GIF animation
        self.assertNotIn("111234567890", image_ids)  # JPEG with alt text
        self.assertNotIn("111234567892", image_ids)  # MP4 video
        
        # Check media types
        media_types = [img['mediaType'] for img in images]
        self.assertIn("image/png", media_types)
        self.assertIn("image/gif", media_types)
        
        # Check that metadata is preserved
        for image in images:
            self.assertIn('attachment_data', image)
            self.assertIn('meta', image['attachment_data'])
            self.assertEqual(image['post_published'], "2023-12-01T15:30:00Z")
    
    def test_mastodon_media_processing_performance(self):
        """Test performance with large numbers of attachments"""
        # Create a post with many attachments to test performance
        attachments = []
        for i in range(100):  # 100 attachments
            attachments.append({
                "type": "Document",
                "mediaType": "image/jpeg" if i % 2 == 0 else "video/mp4",
                "url": f"https://mastodon.social/media/file{i}.jpg",
                "name": "" if i % 3 == 0 else f"Description {i}",  # Some with alt text, some without
                "id": f"media{i}"
            })
        
        post = {
            "id": "https://mastodon.social/@user/123456789",
            "type": "Note",
            "attachment": attachments
        }
        
        # This should complete quickly even with many attachments
        import time
        start_time = time.time()
        images = self.adapter.extract_images_from_post(post)
        end_time = time.time()
        
        # Should complete in reasonable time (less than 1 second)
        self.assertLess(end_time - start_time, 1.0)
        
        # Should extract only images without alt text
        # 50 images (every other attachment), of which ~17 have no alt text (every 3rd has alt text)
        expected_count = len([i for i in range(0, 100, 2) if i % 3 == 0])
        self.assertEqual(len(images), expected_count)

if __name__ == '__main__':
    unittest.main()

class TestMastodonMediaProcessingIntegration(unittest.TestCase):
    """Integration tests for Mastodon media processing with other components"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = MagicMock()
        self.config.instance_url = "https://mastodon.social"
        self.config.access_token = "test_token"
        self.config.api_type = "mastodon"
        self.config.client_key = "test_client_key"
        self.config.client_secret = "test_client_secret"
        
        self.adapter = MastodonPlatform(self.config)
    
    def test_mastodon_media_processing_with_real_world_data_structure(self):
        """Test media processing with realistic Mastodon API response structure"""
        # This mimics the actual structure returned by Mastodon's statuses API
        mastodon_status = {
            "id": "109501234567890",
            "created_at": "2023-12-01T10:30:00.000Z",
            "in_reply_to_id": None,
            "in_reply_to_account_id": None,
            "sensitive": False,
            "spoiler_text": "",
            "visibility": "public",
            "language": "en",
            "uri": "https://mastodon.social/users/photographer/statuses/109501234567890",
            "url": "https://mastodon.social/@photographer/109501234567890",
            "replies_count": 5,
            "reblogs_count": 12,
            "favourites_count": 28,
            "edited_at": None,
            "content": "<p>Beautiful sunset from today's hike! 🌅 <a href=\"https://mastodon.social/tags/photography\" class=\"mention hashtag\" rel=\"tag\">#<span>photography</span></a> <a href=\"https://mastodon.social/tags/nature\" class=\"mention hashtag\" rel=\"tag\">#<span>nature</span></a></p>",
            "reblog": None,
            "account": {
                "id": "123456789",
                "username": "photographer",
                "acct": "photographer",
                "display_name": "Nature Photographer 📸",
                "locked": False,
                "bot": False,
                "discoverable": True,
                "group": False,
                "created_at": "2022-01-15T00:00:00.000Z",
                "note": "<p>Capturing the beauty of nature one photo at a time</p>",
                "url": "https://mastodon.social/@photographer",
                "avatar": "https://files.mastodon.social/accounts/avatars/123/456/789/original/avatar.jpg",
                "avatar_static": "https://files.mastodon.social/accounts/avatars/123/456/789/original/avatar.jpg",
                "header": "https://files.mastodon.social/accounts/headers/123/456/789/original/header.jpg",
                "header_static": "https://files.mastodon.social/accounts/headers/123/456/789/original/header.jpg",
                "followers_count": 1250,
                "following_count": 890,
                "statuses_count": 2340,
                "last_status_at": "2023-12-01",
                "emojis": [],
                "fields": []
            },
            "media_attachments": [
                {
                    "id": "109501234567891",
                    "type": "image",
                    "url": "https://files.mastodon.social/media_attachments/files/109/501/234/567/891/original/sunset.jpg",
                    "preview_url": "https://files.mastodon.social/media_attachments/files/109/501/234/567/891/small/sunset.jpg",
                    "remote_url": None,
                    "preview_remote_url": None,
                    "text_url": None,
                    "meta": {
                        "original": {
                            "width": 4032,
                            "height": 3024,
                            "size": "4032x3024",
                            "aspect": 1.333333
                        },
                        "small": {
                            "width": 533,
                            "height": 400,
                            "size": "533x400",
                            "aspect": 1.3325
                        }
                    },
                    "description": None,  # No alt text - should be processed
                    "blurhash": "UeH2]kRjM{of~qayWBay%MofRjWB"
                }
            ],
            "mentions": [],
            "tags": [
                {
                    "name": "photography",
                    "url": "https://mastodon.social/tags/photography"
                },
                {
                    "name": "nature",
                    "url": "https://mastodon.social/tags/nature"
                }
            ],
            "emojis": [],
            "card": None,
            "poll": None
        }
        
        # Convert to ActivityPub format (as would be done by _convert_mastodon_statuses_to_activitypub)
        activitypub_post = {
            "id": mastodon_status["uri"],
            "type": "Note",
            "content": mastodon_status["content"],
            "attributedTo": f"https://mastodon.social/@photographer",
            "published": mastodon_status["created_at"],
            "attachment": [
                {
                    "type": "Document",
                    "mediaType": "image/jpeg",
                    "url": mastodon_status["media_attachments"][0]["url"],
                    "preview_url": mastodon_status["media_attachments"][0]["preview_url"],
                    "name": mastodon_status["media_attachments"][0]["description"] or "",
                    "id": mastodon_status["media_attachments"][0]["id"],
                    "meta": mastodon_status["media_attachments"][0]["meta"],
                    "blurhash": mastodon_status["media_attachments"][0]["blurhash"]
                }
            ]
        }
        
        images = self.adapter.extract_images_from_post(activitypub_post)
        
        # Should extract the image since it has no alt text
        self.assertEqual(len(images), 1)
        
        image = images[0]
        self.assertEqual(image['url'], "https://files.mastodon.social/media_attachments/files/109/501/234/567/891/original/sunset.jpg")
        self.assertEqual(image['image_post_id'], "109501234567891")
        self.assertEqual(image['mediaType'], "image/jpeg")
        self.assertEqual(image['post_published'], "2023-12-01T10:30:00.000Z")
        
        # Check that metadata is preserved
        self.assertIn('meta', image)
        self.assertIn('preview_url', image)
        self.assertIn('blurhash', image)
        self.assertEqual(image['meta']['original']['width'], 4032)
        self.assertEqual(image['preview_url'], "https://files.mastodon.social/media_attachments/files/109/501/234/567/891/small/sunset.jpg")
    
    def test_mastodon_media_processing_unicode_and_special_characters(self):
        """Test media processing with Unicode and special characters in alt text and URLs"""
        post = {
            "id": "https://mastodon.social/@user/123456789",
            "type": "Note",
            "attachment": [
                {
                    "type": "Document",
                    "mediaType": "image/jpeg",
                    "url": "https://mastodon.social/media/café_photo_🌅.jpg",  # Unicode in URL
                    "name": "",  # Empty - should be processed
                    "id": "image123"
                },
                {
                    "type": "Document",
                    "mediaType": "image/png",
                    "url": "https://mastodon.social/media/image2.png",
                    "name": "Une belle photo de coucher de soleil 🌅🏔️",  # Unicode alt text - should be skipped
                    "id": "image456"
                },
                {
                    "type": "Document",
                    "mediaType": "image/gif",
                    "url": "https://mastodon.social/media/image3.gif",
                    "name": "   🌟✨   ",  # Only emoji and whitespace - should be processed
                    "id": "image789"
                }
            ]
        }
        
        images = self.adapter.extract_images_from_post(post)
        
        # Should extract 2 images (empty alt text and emoji-only alt text)
        self.assertEqual(len(images), 2)
        
        image_ids = [img['image_post_id'] for img in images]
        self.assertIn("image123", image_ids)  # Empty alt text
        self.assertIn("image789", image_ids)  # Emoji-only alt text (treated as empty after strip)
        self.assertNotIn("image456", image_ids)  # Has meaningful alt text
        
        # Check that Unicode URLs are preserved correctly
        urls = [img['url'] for img in images]
        self.assertIn("https://mastodon.social/media/café_photo_🌅.jpg", urls)
    
    def test_mastodon_media_processing_consistency_with_pixelfed(self):
        """Test that Mastodon media processing is consistent with Pixelfed processing"""
        # Create identical post structure for both platforms
        post_data = {
            "id": "https://example.social/@user/123456789",
            "type": "Note",
            "content": "Test post with mixed media",
            "published": "2023-01-01T12:00:00Z",
            "attachment": [
                {
                    "type": "Document",
                    "mediaType": "image/jpeg",
                    "url": "https://example.social/media/image1.jpg",
                    "name": "Image with alt text",  # Should be skipped
                    "id": "image123"
                },
                {
                    "type": "Document",
                    "mediaType": "image/png",
                    "url": "https://example.social/media/image2.png",
                    "name": "",  # Should be processed
                    "id": "image456"
                },
                {
                    "type": "Document",
                    "mediaType": "video/mp4",
                    "url": "https://example.social/media/video.mp4",
                    "name": "",  # Video - should not be processed
                    "id": "video789"
                }
            ]
        }
        
        # Test Mastodon processing
        mastodon_config = MagicMock()
        mastodon_config.instance_url = "https://mastodon.social"
        mastodon_config.access_token = "test_token"
        mastodon_config.api_type = "mastodon"
        mastodon_config.client_key = "test_key"
        mastodon_config.client_secret = "test_secret"
        mastodon_adapter = MastodonPlatform(mastodon_config)
        
        # Test Pixelfed processing
        pixelfed_config = MagicMock()
        pixelfed_config.instance_url = "https://pixelfed.social"
        pixelfed_config.access_token = "test_token"
        pixelfed_adapter = PixelfedPlatform(pixelfed_config)
        
        mastodon_images = mastodon_adapter.extract_images_from_post(post_data)
        pixelfed_images = pixelfed_adapter.extract_images_from_post(post_data)
        
        # Both should extract the same number of images
        self.assertEqual(len(mastodon_images), len(pixelfed_images))
        self.assertEqual(len(mastodon_images), 1)
        
        # Both should extract the same image
        mastodon_image = mastodon_images[0]
        pixelfed_image = pixelfed_images[0]
        
        # Key fields should be consistent
        self.assertEqual(mastodon_image['url'], pixelfed_image['url'])
        self.assertEqual(mastodon_image['mediaType'], pixelfed_image['mediaType'])
        self.assertEqual(mastodon_image['image_post_id'], pixelfed_image['image_post_id'])
        self.assertEqual(mastodon_image['attachment_index'], pixelfed_image['attachment_index'])
        self.assertEqual(mastodon_image['post_published'], pixelfed_image['post_published'])
    
    def test_mastodon_media_processing_error_resilience(self):
        """Test that media processing is resilient to various error conditions"""
        error_cases = [
            {
                "name": "corrupted_attachment_data",
                "post": {
                    "id": "https://mastodon.social/@user/123456789",
                    "type": "Note",
                    "attachment": [
                        {
                            "type": "Document",
                            "mediaType": "image/jpeg",
                            "url": "https://mastodon.social/media/image1.jpg",
                            "name": "",
                            "id": "image123",
                            "meta": "invalid_meta_data"  # Should be dict, not string
                        }
                    ]
                },
                "should_extract": True
            },
            {
                "name": "extremely_long_alt_text",
                "post": {
                    "id": "https://mastodon.social/@user/123456789",
                    "type": "Note",
                    "attachment": [
                        {
                            "type": "Document",
                            "mediaType": "image/jpeg",
                            "url": "https://mastodon.social/media/image2.jpg",
                            "name": "A" * 10000,  # Very long alt text - should be skipped
                            "id": "image456"
                        }
                    ]
                },
                "should_extract": False
            },
            {
                "name": "numeric_alt_text",
                "post": {
                    "id": "https://mastodon.social/@user/123456789",
                    "type": "Note",
                    "attachment": [
                        {
                            "type": "Document",
                            "mediaType": "image/jpeg",
                            "url": "https://mastodon.social/media/image3.jpg",
                            "name": 12345,  # Numeric alt text - should be converted to string
                            "id": "image789"
                        }
                    ]
                },
                "should_extract": False  # "12345" is meaningful alt text
            },
            {
                "name": "boolean_alt_text",
                "post": {
                    "id": "https://mastodon.social/@user/123456789",
                    "type": "Note",
                    "attachment": [
                        {
                            "type": "Document",
                            "mediaType": "image/jpeg",
                            "url": "https://mastodon.social/media/image4.jpg",
                            "name": False,  # Boolean alt text - should be converted to string
                            "id": "image101112"
                        }
                    ]
                },
                "should_extract": True  # "False" becomes empty after strip
            }
        ]
        
        for case in error_cases:
            with self.subTest(case=case["name"]):
                try:
                    images = self.adapter.extract_images_from_post(case["post"])
                    
                    if case["should_extract"]:
                        self.assertGreater(len(images), 0, f"Should extract image for case: {case['name']}")
                    else:
                        self.assertEqual(len(images), 0, f"Should not extract image for case: {case['name']}")
                        
                except Exception as e:
                    self.fail(f"Media processing should not raise exception for case {case['name']}: {e}")

if __name__ == '__main__':
    unittest.main()