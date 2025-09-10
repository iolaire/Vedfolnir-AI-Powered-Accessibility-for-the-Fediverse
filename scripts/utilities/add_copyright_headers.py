# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Copyright Header Utility Script

This script adds copyright and license headers to all source code files in the project.
It supports Python, JavaScript, HTML, CSS, Shell, and SQL files with appropriate comment syntax.
"""

import os
import sys
import shutil
import fnmatch
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import argparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Header templates for different file types
HEADER_TEMPLATES = {
    'python': [
        "# Copyright (C) 2025 iolaire mcfadden.",
        "# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.",
        "# THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.",
        ""
    ],
    'javascript': [
        "// Copyright (C) 2025 iolaire mcfadden.",
        "// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.",
        "// THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.",
        ""
    ],
    'html': [
        "<!-- Copyright (C) 2025 iolaire mcfadden. -->",
        "<!-- This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version. -->",
        "<!-- THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE. -->",
        ""
    ],
    'css': [
        "/* Copyright (C) 2025 iolaire mcfadden. */",
        "/* This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version. */",
        "/* THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE. */",
        ""
    ],
    'shell': [
        "# Copyright (C) 2025 iolaire mcfadden.",
        "# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.",
        "# THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.",
        ""
    ],
    'sql': [
        "-- Copyright (C) 2025 iolaire mcfadden.",
        "-- This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.",
        "-- THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.",
        ""
    ]
}

# File extension to type mapping
FILE_TYPE_MAPPING = {
    '.py': 'python',
    '.js': 'javascript',
    '.html': 'html',
    '.css': 'css',
    '.sh': 'shell',
    '.sql': 'sql'
}

# Include patterns for source files
INCLUDE_PATTERNS = ['*.py', '*.js', '*.html', '*.css', '*.sh', '*.sql']

# Exclude patterns for files/directories to skip
EXCLUDE_PATTERNS = [
    '*/node_modules/*',
    '*/.git/*',
    '*/__pycache__/*',
    '*/venv/*',
    '*/env/*',
    '*/build/*',
    '*/dist/*',
    '*.min.js',
    '*.min.css',
    '*/migrations/*',
    '*/vendor/*',
    '*/third_party/*'
]

@dataclass
class FileProcessingResult:
    """Result of processing a single file"""
    file_path: str
    file_type: str
    had_header: bool
    header_added: bool
    error: Optional[str] = None
    backup_created: bool = False

@dataclass
class ProcessingSummary:
    """Summary of processing results"""
    total_files: int
    files_processed: int
    files_skipped: int
    files_with_errors: int
    files_by_type: Dict[str, int]
    errors: List[str]

class CopyrightHeaderProcessor:
    """Main class for processing copyright headers"""
    
    def __init__(self, root_dir: str = '.', create_backups: bool = True, dry_run: bool = False):
        self.root_dir = Path(root_dir)
        self.create_backups = create_backups
        self.dry_run = dry_run
        self.results: List[FileProcessingResult] = []
    
    def detect_file_type(self, file_path: Path) -> Optional[str]:
        """Detect file type based on extension"""
        return FILE_TYPE_MAPPING.get(file_path.suffix.lower())
    
    def has_copyright_header(self, file_path: Path) -> bool:
        """Check if file already has copyright header"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Read first 10 lines to check for copyright
                first_lines = []
                for i, line in enumerate(f):
                    if i >= 10:
                        break
                    first_lines.append(line.lower())
                
                content = ''.join(first_lines)
                return 'copyright' in content and 'iolaire mcfadden' in content
        except Exception as e:
            logger.warning(f"Error reading file {file_path}: {e}")
            return False
    
    def create_backup(self, file_path: Path) -> bool:
        """Create backup of file before modification"""
        if not self.create_backups:
            return True
        
        try:
            backup_path = file_path.with_suffix(file_path.suffix + '.backup')
            shutil.copy2(file_path, backup_path)
            logger.debug(f"Created backup: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create backup for {file_path}: {e}")
            return False
    
    def add_header_to_file(self, file_path: Path, file_type: str) -> FileProcessingResult:
        """Add copyright header to a single file"""
        result = FileProcessingResult(
            file_path=str(file_path),
            file_type=file_type,
            had_header=False,
            header_added=False
        )
        
        try:
            # Check if file already has header
            if self.has_copyright_header(file_path):
                result.had_header = True
                logger.info(f"Skipping {file_path} - already has copyright header")
                return result
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Create backup if not dry run
            if not self.dry_run:
                result.backup_created = self.create_backup(file_path)
                if not result.backup_created:
                    result.error = "Failed to create backup"
                    return result
            
            # Get header template
            header_lines = HEADER_TEMPLATES[file_type]
            
            # Handle special cases
            new_content = self._handle_special_cases(content, header_lines, file_type)
            
            # Write modified content if not dry run
            if not self.dry_run:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
            
            result.header_added = True
            logger.info(f"{'[DRY RUN] ' if self.dry_run else ''}Added copyright header to {file_path}")
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"Error processing {file_path}: {e}")
        
        return result
    
    def _handle_special_cases(self, content: str, header_lines: List[str], file_type: str) -> str:
        """Handle special cases like shebangs, doctypes, etc."""
        lines = content.split('\n')
        header_text = '\n'.join(header_lines)
        
        if file_type == 'python' and lines and lines[0].startswith('#!'):
            # Preserve shebang line
            shebang = lines[0]
            rest_content = '\n'.join(lines[1:])
            return f"{shebang}\n{header_text}{rest_content}"
        
        elif file_type == 'html' and content.strip().startswith('<!DOCTYPE'):
            # Handle HTML doctype
            doctype_end = content.find('>')
            if doctype_end != -1:
                doctype = content[:doctype_end + 1]
                rest_content = content[doctype_end + 1:]
                return f"{doctype}\n{header_text}{rest_content}"
        
        elif file_type == 'shell' and lines and lines[0].startswith('#!'):
            # Preserve shebang line for shell scripts
            shebang = lines[0]
            rest_content = '\n'.join(lines[1:])
            return f"{shebang}\n{header_text}{rest_content}"
        
        # Default case - add header at the beginning
        return header_text + content
    
    def scan_project_files(self) -> List[Path]:
        """Scan project for source code files"""
        source_files = []
        
        for root, dirs, files in os.walk(self.root_dir):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if not any(
                fnmatch.fnmatch(os.path.join(root, d), pattern) 
                for pattern in EXCLUDE_PATTERNS
            )]
            
            for file in files:
                file_path = Path(root) / file
                
                # Check if file matches include patterns
                if any(fnmatch.fnmatch(file, pattern) for pattern in INCLUDE_PATTERNS):
                    # Check if file should be excluded
                    if not any(fnmatch.fnmatch(str(file_path), pattern) for pattern in EXCLUDE_PATTERNS):
                        source_files.append(file_path)
        
        return source_files
    
    def process_all_files(self) -> ProcessingSummary:
        """Process all source files in the project"""
        logger.info(f"{'[DRY RUN] ' if self.dry_run else ''}Starting copyright header processing...")
        
        # Scan for files
        source_files = self.scan_project_files()
        logger.info(f"Found {len(source_files)} source files to process")
        
        # Process each file
        files_by_type = {}
        errors = []
        
        for file_path in source_files:
            file_type = self.detect_file_type(file_path)
            if not file_type:
                logger.warning(f"Unknown file type for {file_path}")
                continue
            
            files_by_type[file_type] = files_by_type.get(file_type, 0) + 1
            
            result = self.add_header_to_file(file_path, file_type)
            self.results.append(result)
            
            if result.error:
                errors.append(f"{file_path}: {result.error}")
        
        # Generate summary
        summary = ProcessingSummary(
            total_files=len(source_files),
            files_processed=len([r for r in self.results if r.header_added]),
            files_skipped=len([r for r in self.results if r.had_header]),
            files_with_errors=len([r for r in self.results if r.error]),
            files_by_type=files_by_type,
            errors=errors
        )
        
        return summary
    
    def print_summary(self, summary: ProcessingSummary):
        """Print processing summary"""
        print("\n" + "="*60)
        print("COPYRIGHT HEADER PROCESSING SUMMARY")
        print("="*60)
        print(f"Total files found: {summary.total_files}")
        print(f"Files processed: {summary.files_processed}")
        print(f"Files skipped (already had headers): {summary.files_skipped}")
        print(f"Files with errors: {summary.files_with_errors}")
        
        print("\nFiles by type:")
        for file_type, count in summary.files_by_type.items():
            print(f"  {file_type}: {count}")
        
        if summary.errors:
            print("\nErrors:")
            for error in summary.errors:
                print(f"  {error}")
        
        print("="*60)

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Add copyright headers to source code files')
    parser.add_argument('--root-dir', default='.', help='Root directory to process (default: current directory)')
    parser.add_argument('--no-backup', action='store_true', help='Do not create backup files')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create processor
    processor = CopyrightHeaderProcessor(
        root_dir=args.root_dir,
        create_backups=not args.no_backup,
        dry_run=args.dry_run
    )
    
    # Process files
    summary = processor.process_all_files()
    
    # Print summary
    processor.print_summary(summary)
    
    # Exit with error code if there were errors
    if summary.files_with_errors > 0:
        sys.exit(1)

if __name__ == '__main__':
    main()