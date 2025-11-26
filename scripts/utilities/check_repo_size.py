# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Repository Size and External Dependencies Checker

This script helps monitor your repository size and identifies potential
external libraries or large files that might be accidentally tracked.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Dict

def get_repo_size() -> str:
    """Get the total size of the repository."""
    try:
        result = subprocess.run(['du', '-sh', '.'], capture_output=True, text=True)
        return result.stdout.strip().split('\t')[0]
    except Exception as e:
        return f"Error: {e}"

def find_large_files(size_mb: int = 10) -> List[Tuple[str, str]]:
    """Find files larger than specified size in MB."""
    try:
        result = subprocess.run([
            'find', '.', '-type', 'f', '-size', f'+{size_mb}M',
            '-not', '-path', './.git/*'
        ], capture_output=True, text=True)
        
        large_files = []
        for line in result.stdout.strip().split('\n'):
            if line:
                # Get file size
                size_result = subprocess.run(['du', '-h', line], capture_output=True, text=True)
                size = size_result.stdout.strip().split('\t')[0] if size_result.stdout else "Unknown"
                large_files.append((line, size))
        
        return large_files
    except Exception as e:
        print(f"Error finding large files: {e}")
        return []

def check_tracked_dependencies() -> List[str]:
    """Check for potentially tracked external dependencies."""
    patterns = [
        'node_modules',
        '__pycache__',
        '.pyc',
        '.egg-info',
        'vendor/',
        'lib/',
        'libs/',
        'third-party/',
        'third_party/',
        'external/',
        'dependencies/',
        '.cache/',
        'models/',
        'checkpoints/',
        '.bin',
        '.safetensors'
    ]
    
    try:
        result = subprocess.run(['git', 'ls-files'], capture_output=True, text=True)
        tracked_files = result.stdout.strip().split('\n')
        
        suspicious_files = []
        for file in tracked_files:
            for pattern in patterns:
                if pattern in file:
                    suspicious_files.append(file)
                    break
        
        return suspicious_files
    except Exception as e:
        print(f"Error checking tracked files: {e}")
        return []

def get_directory_sizes() -> List[Tuple[str, str]]:
    """Get sizes of top-level directories."""
    try:
        result = subprocess.run(['du', '-sh', '*'], capture_output=True, text=True, shell=True)
        
        dir_sizes = []
        for line in result.stdout.strip().split('\n'):
            if line and '\t' in line:
                size, path = line.split('\t', 1)
                dir_sizes.append((path, size))
        
        # Sort by size (rough approximation)
        dir_sizes.sort(key=lambda x: x[1], reverse=True)
        return dir_sizes
    except Exception as e:
        print(f"Error getting directory sizes: {e}")
        return []

def check_gitignore_coverage() -> Dict[str, bool]:
    """Check if common external dependency patterns are in .gitignore."""
    gitignore_path = Path('.gitignore')
    
    if not gitignore_path.exists():
        return {}
    
    gitignore_content = gitignore_path.read_text()
    
    patterns_to_check = {
        'node_modules/': 'node_modules/' in gitignore_content,
        '__pycache__/': '__pycache__/' in gitignore_content,
        '*.pyc': '*.pyc' in gitignore_content,
        'vendor/': 'vendor/' in gitignore_content,
        'lib/': 'lib/' in gitignore_content,
        '.cache/': '.cache/' in gitignore_content,
        'models/': 'models/' in gitignore_content,
        '*.bin': '*.bin' in gitignore_content,
        '*.safetensors': '*.safetensors' in gitignore_content,
        'storage/': 'storage/' in gitignore_content,
    }
    
    return patterns_to_check

def main():
    """Main function to run all checks."""
    print("🔍 Repository Size and Dependencies Check")
    print("=" * 50)
    
    # Repository size
    repo_size = get_repo_size()
    print(f"📊 Total repository size: {repo_size}")
    print()
    
    # Directory sizes
    print("📁 Directory sizes:")
    dir_sizes = get_directory_sizes()
    for path, size in dir_sizes[:10]:  # Show top 10
        print(f"  {size:>8} {path}")
    print()
    
    # Large files
    print("🔍 Large files (>10MB):")
    large_files = find_large_files(10)
    if large_files:
        for file_path, size in large_files:
            print(f"  {size:>8} {file_path}")
    else:
        print("  ✅ No large files found")
    print()
    
    # Tracked dependencies
    print("⚠️  Potentially tracked external dependencies:")
    suspicious_files = check_tracked_dependencies()
    if suspicious_files:
        for file in suspicious_files[:20]:  # Show first 20
            print(f"  📦 {file}")
        if len(suspicious_files) > 20:
            print(f"  ... and {len(suspicious_files) - 20} more")
    else:
        print("  ✅ No suspicious files found")
    print()
    
    # .gitignore coverage
    print("📋 .gitignore coverage for common patterns:")
    gitignore_coverage = check_gitignore_coverage()
    for pattern, covered in gitignore_coverage.items():
        status = "✅" if covered else "❌"
        print(f"  {status} {pattern}")
    print()
    
    # Recommendations
    print("💡 Recommendations:")
    if large_files:
        print("  • Consider using Git LFS for large files")
        print("  • Move large files to external storage if possible")
    
    if suspicious_files:
        print("  • Review tracked dependency files")
        print("  • Update .gitignore to exclude external libraries")
        print("  • Use 'git rm --cached <file>' to untrack files")
    
    missing_patterns = [p for p, covered in gitignore_coverage.items() if not covered]
    if missing_patterns:
        print(f"  • Add missing patterns to .gitignore: {', '.join(missing_patterns)}")
    
    if not large_files and not suspicious_files and not missing_patterns:
        print("  ✅ Repository looks clean and well-maintained!")

if __name__ == "__main__":
    main()