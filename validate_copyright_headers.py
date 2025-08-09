# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Copyright Header Validation Script

This script validates that all source code files in the project have proper copyright headers.
It provides compliance checking and reporting functionality.
"""

import os
import sys
import fnmatch
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional
import argparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
class ValidationResult:
    """Result of validating a single file"""
    file_path: str
    file_type: str
    has_header: bool
    has_correct_copyright: bool
    has_correct_license: bool
    error: Optional[str] = None

@dataclass
class ValidationSummary:
    """Summary of validation results"""
    total_files: int
    files_with_headers: int
    files_missing_headers: int
    files_with_incorrect_headers: int
    files_by_type: Dict[str, int]
    missing_files: List[str]
    incorrect_files: List[str]
    errors: List[str]

class CopyrightHeaderValidator:
    """Main class for validating copyright headers"""
    
    def __init__(self, root_dir: str = '.'):
        self.root_dir = Path(root_dir)
        self.results: List[ValidationResult] = []
    
    def detect_file_type(self, file_path: Path) -> Optional[str]:
        """Detect file type based on extension"""
        return FILE_TYPE_MAPPING.get(file_path.suffix.lower())
    
    def validate_copyright_header(self, file_path: Path) -> ValidationResult:
        """Validate copyright header in a single file"""
        file_type = self.detect_file_type(file_path)
        result = ValidationResult(
            file_path=str(file_path),
            file_type=file_type or 'unknown',
            has_header=False,
            has_correct_copyright=False,
            has_correct_license=False
        )
        
        if not file_type:
            result.error = "Unknown file type"
            return result
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Read first 15 lines to check for copyright header
                first_lines = []
                for i, line in enumerate(f):
                    if i >= 15:
                        break
                    first_lines.append(line.lower())
                
                content = ''.join(first_lines)
                
                # Check for copyright notice
                if 'copyright' in content:
                    result.has_header = True
                    
                    # Check for correct copyright holder
                    if 'iolaire mcfadden' in content:
                        result.has_correct_copyright = True
                    
                    # Check for AGPL license reference
                    if 'gnu affero general public license' in content:
                        result.has_correct_license = True
                
        except Exception as e:
            result.error = str(e)
            logger.warning(f"Error reading file {file_path}: {e}")
        
        return result
    
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
    
    def validate_all_files(self) -> ValidationSummary:
        """Validate all source files in the project"""
        logger.info("Starting copyright header validation...")
        
        # Scan for files
        source_files = self.scan_project_files()
        logger.info(f"Found {len(source_files)} source files to validate")
        
        # Validate each file
        files_by_type = {}
        missing_files = []
        incorrect_files = []
        errors = []
        
        for file_path in source_files:
            file_type = self.detect_file_type(file_path)
            if not file_type:
                logger.warning(f"Unknown file type for {file_path}")
                continue
            
            files_by_type[file_type] = files_by_type.get(file_type, 0) + 1
            
            result = self.validate_copyright_header(file_path)
            self.results.append(result)
            
            if result.error:
                errors.append(f"{file_path}: {result.error}")
            elif not result.has_header:
                missing_files.append(str(file_path))
            elif not (result.has_correct_copyright and result.has_correct_license):
                incorrect_files.append(str(file_path))
        
        # Generate summary
        summary = ValidationSummary(
            total_files=len(source_files),
            files_with_headers=len([r for r in self.results if r.has_header]),
            files_missing_headers=len([r for r in self.results if not r.has_header and not r.error]),
            files_with_incorrect_headers=len([r for r in self.results if r.has_header and not (r.has_correct_copyright and r.has_correct_license)]),
            files_by_type=files_by_type,
            missing_files=missing_files,
            incorrect_files=incorrect_files,
            errors=errors
        )
        
        return summary
    
    def print_summary(self, summary: ValidationSummary, verbose: bool = False):
        """Print validation summary"""
        print("\n" + "="*60)
        print("COPYRIGHT HEADER VALIDATION SUMMARY")
        print("="*60)
        print(f"Total files scanned: {summary.total_files}")
        print(f"Files with headers: {summary.files_with_headers}")
        print(f"Files missing headers: {summary.files_missing_headers}")
        print(f"Files with incorrect headers: {summary.files_with_incorrect_headers}")
        
        print("\nFiles by type:")
        for file_type, count in summary.files_by_type.items():
            print(f"  {file_type}: {count}")
        
        # Compliance status
        if summary.files_missing_headers == 0 and summary.files_with_incorrect_headers == 0:
            print("\n✅ COMPLIANCE STATUS: PASSED")
            print("All source files have proper copyright headers!")
        else:
            print("\n❌ COMPLIANCE STATUS: FAILED")
            print("Some files are missing or have incorrect copyright headers.")
        
        if verbose or summary.files_missing_headers > 0:
            if summary.missing_files:
                print("\nFiles missing copyright headers:")
                for file_path in summary.missing_files:
                    print(f"  ❌ {file_path}")
        
        if verbose or summary.files_with_incorrect_headers > 0:
            if summary.incorrect_files:
                print("\nFiles with incorrect copyright headers:")
                for file_path in summary.incorrect_files:
                    print(f"  ⚠️  {file_path}")
        
        if summary.errors:
            print("\nErrors encountered:")
            for error in summary.errors:
                print(f"  ❌ {error}")
        
        print("="*60)
    
    def print_detailed_report(self, summary: ValidationSummary):
        """Print detailed validation report"""
        print("\n" + "="*60)
        print("DETAILED VALIDATION REPORT")
        print("="*60)
        
        for result in self.results:
            status = "✅" if (result.has_header and result.has_correct_copyright and result.has_correct_license) else "❌"
            print(f"{status} {result.file_path} ({result.file_type})")
            
            if result.error:
                print(f"    Error: {result.error}")
            elif not result.has_header:
                print("    Missing copyright header")
            elif not result.has_correct_copyright:
                print("    Incorrect copyright holder")
            elif not result.has_correct_license:
                print("    Missing or incorrect license reference")
        
        print("="*60)

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Validate copyright headers in source code files')
    parser.add_argument('--root-dir', default='.', help='Root directory to validate (default: current directory)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output')
    parser.add_argument('--detailed', '-d', action='store_true', help='Show detailed report for all files')
    parser.add_argument('--quiet', '-q', action='store_true', help='Only show summary')
    
    args = parser.parse_args()
    
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    elif args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create validator
    validator = CopyrightHeaderValidator(root_dir=args.root_dir)
    
    # Validate files
    summary = validator.validate_all_files()
    
    # Print results
    if not args.quiet:
        validator.print_summary(summary, verbose=args.verbose)
    
    if args.detailed:
        validator.print_detailed_report(summary)
    
    # Exit with error code if validation failed
    if summary.files_missing_headers > 0 or summary.files_with_incorrect_headers > 0:
        sys.exit(1)
    else:
        if not args.quiet:
            print("\n🎉 All files have proper copyright headers!")
        sys.exit(0)

if __name__ == '__main__':
    main()