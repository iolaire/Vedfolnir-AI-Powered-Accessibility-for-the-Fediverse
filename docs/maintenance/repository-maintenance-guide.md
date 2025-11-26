# Repository Maintenance Guide

## Overview
This guide helps maintain a clean repository by preventing external libraries and large files from being tracked in git.

## Current Status ✅
- **Repository Size**: 124M (well-maintained)
- **External Dependencies**: None tracked
- **Large Files**: None found
- **Gitignore Coverage**: Complete

## Regular Maintenance

### Weekly Checks
```bash
# Check repository size and dependencies
python scripts/utilities/check_repo_size.py

# Check for accidentally staged large files
git diff --cached --stat
```

### Before Committing
```bash
# Always check what you're about to commit
git status
git diff --cached --name-only

# Look for suspicious patterns
git diff --cached --name-only | grep -E "(node_modules|__pycache__|\.pyc|vendor|lib/)"
```

### Monthly Cleanup
```bash
# Run comprehensive cleanup (interactive)
./scripts/utilities/clean_external_deps.sh

# Clean up untracked files
git clean -fd --dry-run  # Preview
git clean -fd            # Execute
```

## What to Avoid Tracking

### External Libraries
- `node_modules/` - Node.js dependencies
- `__pycache__/`, `*.pyc` - Python cache files
- `vendor/`, `lib/`, `libs/` - Vendor libraries
- `third-party/`, `external/` - Third-party code
- `.cache/`, `cache/` - Cache directories

### AI/ML Files
- `*.bin`, `*.safetensors` - Model weights
- `models/`, `checkpoints/` - Model directories
- `.transformers_cache/` - Hugging Face cache
- `.torch/` - PyTorch cache

### Large Files
- `*.tar.gz`, `*.zip`, `*.rar` - Archives
- `*.iso`, `*.dmg`, `*.img` - Disk images
- Any file > 10MB should be carefully reviewed

### Generated Content
- Build outputs (`build/`, `dist/`)
- Logs (`*.log`, `logs/`)
- Temporary files (`*.tmp`, `temp/`)
- OS files (`.DS_Store`, `Thumbs.db`)

## Emergency Cleanup

### Remove File from Git History
```bash
# Remove a file that was accidentally committed
git rm --cached path/to/file

# Remove from entire history (use carefully!)
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch path/to/file' \
  --prune-empty --tag-name-filter cat -- --all
```

### Clean Up Large Files
```bash
# Find large files in git history
git rev-list --objects --all | \
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
  awk '/^blob/ {print substr($0,6)}' | \
  sort --numeric-sort --key=2 | \
  tail -10

# Use BFG Repo-Cleaner for complex cleanup
# https://rtyley.github.io/bfg-repo-cleaner/
```

## Best Practices

### 1. Use Package Managers Properly
```bash
# Python - use virtual environments
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Node.js - dependencies in package.json
npm install  # Creates node_modules/ (ignored)
```

### 2. Configure Git Properly
```bash
# Set up global gitignore
git config --global core.excludesfile ~/.gitignore_global

# Use Git LFS for legitimate large files
git lfs track "*.psd"
git lfs track "*.zip"
```

### 3. Regular Monitoring
```bash
# Add to your development workflow
alias repo-check="python scripts/utilities/check_repo_size.py"
alias repo-clean="./scripts/utilities/clean_external_deps.sh"

# Set up pre-commit hooks
# .git/hooks/pre-commit
#!/bin/bash
python scripts/utilities/check_repo_size.py --quiet
```

## Troubleshooting

### Repository Too Large
1. Run `python scripts/utilities/check_repo_size.py`
2. Identify large directories/files
3. Use `./scripts/utilities/clean_external_deps.sh`
4. Consider Git LFS for legitimate large files

### Accidentally Committed Dependencies
1. Use `git rm --cached` to untrack
2. Update `.gitignore`
3. Commit the removal
4. For history cleanup, use BFG Repo-Cleaner

### Performance Issues
- Large repositories can slow down git operations
- Consider splitting into multiple repositories
- Use shallow clones for CI/CD: `git clone --depth 1`

## Tools and Scripts

### Available Scripts
- `scripts/utilities/check_repo_size.py` - Repository analysis
- `scripts/utilities/clean_external_deps.sh` - Interactive cleanup
- `.gitignore` - Comprehensive ignore patterns

### External Tools
- [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/) - History cleanup
- [Git LFS](https://git-lfs.github.io/) - Large file storage
- [git-sizer](https://github.com/github/git-sizer) - Repository analysis

## Success Metrics

### Good Repository Health
- Size < 500MB for most projects
- No external dependencies tracked
- No files > 10MB without good reason
- Clean `git status` output
- Fast git operations

### Warning Signs
- Repository size growing rapidly
- `node_modules/` or similar in git status
- Slow git operations
- Large diffs for small changes
- Binary files in commits

## Conclusion

Maintaining a clean repository is crucial for:
- **Performance** - Faster clones and operations
- **Collaboration** - Easier for team members
- **Storage** - Reduced hosting costs
- **Security** - No accidental credential exposure

Regular use of the provided tools and following these guidelines will keep your repository healthy and efficient.