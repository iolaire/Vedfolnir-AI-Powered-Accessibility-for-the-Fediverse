#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Script to process more posts and skip already processed ones

# Run the bot with increased post limit, pagination support, and fixed SQLAlchemy session handling
echo "Running Alt Text Bot with pagination support to process more posts..."
echo "This will fetch up to 200 posts and skip those already processed."
echo "Fixed SQLAlchemy session handling to prevent DetachedInstanceError."
python main.py --users iolaire --log-level INFO

# To reprocess all images, including those already processed, uncomment the line below:
# echo "Running Alt Text Bot with pagination support to reprocess ALL posts..."
# python main.py --users iolaire --log-level INFO --reprocess-all