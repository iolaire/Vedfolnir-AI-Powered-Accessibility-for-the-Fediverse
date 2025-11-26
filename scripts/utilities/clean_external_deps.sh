#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Repository Cleanup Script
# Removes external dependencies and large files from git tracking

set -e

echo "🧹 Repository Cleanup Script"
echo "=========================="

# Function to safely remove files from git tracking
remove_from_git() {
    local pattern="$1"
    local description="$2"
    
    echo "🔍 Checking for $description..."
    
    # Find files matching pattern that are tracked by git
    files=$(git ls-files | grep -E "$pattern" || true)
    
    if [ -n "$files" ]; then
        echo "📦 Found $description files:"
        echo "$files" | head -10
        if [ $(echo "$files" | wc -l) -gt 10 ]; then
            echo "... and $(( $(echo "$files" | wc -l) - 10 )) more"
        fi
        
        read -p "❓ Remove these files from git tracking? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "$files" | xargs git rm --cached
            echo "✅ Removed $description from git tracking"
        else
            echo "⏭️  Skipped $description"
        fi
    else
        echo "✅ No $description found in git tracking"
    fi
    echo
}

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Error: Not in a git repository"
    exit 1
fi

echo "📊 Current repository size: $(du -sh . | cut -f1)"
echo

# Remove common external dependencies
remove_from_git "node_modules/" "Node.js dependencies"
remove_from_git "__pycache__|\.pyc$" "Python cache files"
remove_from_git "\.egg-info/" "Python package info"
remove_from_git "vendor/|lib/|libs/" "Vendor/library directories"
remove_from_git "third[-_]party/|external/" "Third-party dependencies"
remove_from_git "\.cache/|cache/" "Cache directories"
remove_from_git "models/.*\.(bin|safetensors|onnx|pb|h5|hdf5|pkl|pickle|joblib|model|weights)$" "AI/ML model files"
remove_from_git "checkpoints/" "Model checkpoints"
remove_from_git "\.(tar\.gz|zip|rar|7z|bz2|xz|gz|tgz|tar|iso|dmg|img)$" "Archive files"

# Check for large files
echo "🔍 Checking for large files (>10MB)..."
large_files=$(git ls-files | xargs ls -la 2>/dev/null | awk '$5 > 10485760 {print $9, $5}' || true)

if [ -n "$large_files" ]; then
    echo "📦 Found large files:"
    echo "$large_files"
    read -p "❓ Remove these large files from git tracking? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "$large_files" | awk '{print $1}' | xargs git rm --cached
        echo "✅ Removed large files from git tracking"
    else
        echo "⏭️  Skipped large files"
    fi
else
    echo "✅ No large files found"
fi
echo

# Show final status
echo "📊 Final repository size: $(du -sh . | cut -f1)"
echo

# Check if there are changes to commit
if git diff --cached --quiet; then
    echo "✅ No changes made to git tracking"
else
    echo "📝 Changes made to git tracking:"
    git diff --cached --name-status
    echo
    read -p "❓ Commit these changes? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git commit -m "Remove external dependencies and large files from git tracking

- Cleaned up accidentally tracked external libraries
- Removed large files from version control
- Updated repository to follow .gitignore patterns"
        echo "✅ Changes committed"
    else
        echo "⏭️  Changes staged but not committed"
        echo "💡 Run 'git commit' to commit the changes later"
    fi
fi

echo
echo "🎉 Cleanup complete!"
echo "💡 Don't forget to:"
echo "   • Review and update your .gitignore file"
echo "   • Run 'python scripts/utilities/check_repo_size.py' to verify"
echo "   • Consider using Git LFS for legitimate large files"