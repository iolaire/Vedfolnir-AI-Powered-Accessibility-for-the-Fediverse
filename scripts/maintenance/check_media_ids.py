#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from database import DatabaseManager
from config import Config
from sqlalchemy import text

def check_ids():
    """Check if id is being stored"""
    config = Config()
    db = DatabaseManager(config)
    session = db.get_session()
    
    try:
        # Get 10 images
        query = text("SELECT id, image_url, id FROM images LIMIT 10")
        result = session.execute(query)
        rows = result.fetchall()
        
        print("Images in database:")
        for row in rows:
            print(f"ID: {row[0]}, ID: {row[2]}, URL: {row[1]}")
            
    finally:
        session.close()

if __name__ == "__main__":
    check_ids()
