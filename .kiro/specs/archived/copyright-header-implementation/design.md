# Design Document

## Overview

This design outlines the implementation of copyright and license headers across all source code files in the Vedfolnir project. The solution will systematically add standardized headers to existing files while establishing processes to ensure new files automatically include appropriate headers.

## Architecture

### Header Content Structure

The copyright header consists of three main components:
1. **Copyright Notice**: "Copyright (C) 2025 iolaire mcfadden."
2. **License Statement**: GNU Affero General Public License v3.0 reference
3. **Warranty Disclaimer**: Standard "AS IS" warranty disclaimer

### File Type Mapping

Different file types require different comment syntaxes:

| File Type | Extension | Comment Syntax | Example |
|-----------|-----------|----------------|---------|
| Python | .py | # | `# Copyright (C) 2025...` |
| JavaScript | .js | // | `// Copyright (C) 2025...` |
| HTML | .html | <!-- --> | `<!-- Copyright (C) 2025... -->` |
| CSS | .css | /* */ | `/* Copyright (C) 2025... */` |
| Shell | .sh | # | `# Copyright (C) 2025...` |
| SQL | .sql | -- | `-- Copyright (C) 2025...` |

## Components and Interfaces

### 1. Header Template System

**Purpose**: Provide standardized header templates for each file type

**Implementation**:
```python
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
    ]
}
```

### 2. File Processing Engine

**Purpose**: Systematically process existing files to add headers

**Key Functions**:
- `scan_project_files()`: Discover all source code files
- `detect_file_type()`: Determine appropriate header format
- `has_copyright_header()`: Check if file already has header
- `add_header_to_file()`: Insert header at top of file
- `preserve_shebangs()`: Handle special cases like #!/usr/bin/env python

**Implementation Strategy**:
```python
def process_file(file_path):
    """Process a single file to add copyright header"""
    file_type = detect_file_type(file_path)
    if file_type not in HEADER_TEMPLATES:
        return False
    
    if has_copyright_header(file_path):
        return True  # Already has header
    
    return add_header_to_file(file_path, file_type)

def add_header_to_file(file_path, file_type):
    """Add copyright header to file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    header_lines = HEADER_TEMPLATES[file_type]
    
    # Handle special cases (shebangs, doctype declarations, etc.)
    if file_type == 'python' and content.startswith('#!'):
        # Preserve shebang line
        lines = content.split('\n')
        shebang = lines[0]
        rest_content = '\n'.join(lines[1:])
        new_content = shebang + '\n' + '\n'.join(header_lines) + rest_content
    elif file_type == 'html' and content.strip().startswith('<!DOCTYPE'):
        # Handle HTML doctype
        lines = content.split('\n')
        doctype_line = lines[0]
        rest_content = '\n'.join(lines[1:])
        new_content = doctype_line + '\n' + '\n'.join(header_lines) + rest_content
    else:
        new_content = '\n'.join(header_lines) + content
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    return True
```

### 3. File Discovery System

**Purpose**: Identify all source code files that need headers

**Implementation**:
```python
import os
import fnmatch

INCLUDE_PATTERNS = ['*.py', '*.js', '*.html', '*.css', '*.sh', '*.sql']
EXCLUDE_PATTERNS = [
    '*/node_modules/*',
    '*/.git/*',
    '*/__pycache__/*',
    '*/venv/*',
    '*/env/*',
    '*.min.js',
    '*.min.css'
]

def scan_project_files(root_dir='.'):
    """Scan project for source code files"""
    source_files = []
    
    for root, dirs, files in os.walk(root_dir):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(os.path.join(root, d), pattern) for pattern in EXCLUDE_PATTERNS)]
        
        for file in files:
            file_path = os.path.join(root, file)
            
            # Check if file matches include patterns
            if any(fnmatch.fnmatch(file, pattern) for pattern in INCLUDE_PATTERNS):
                # Check if file should be excluded
                if not any(fnmatch.fnmatch(file_path, pattern) for pattern in EXCLUDE_PATTERNS):
                    source_files.append(file_path)
    
    return source_files
```

### 4. Header Detection System

**Purpose**: Determine if a file already has a copyright header

**Implementation**:
```python
def has_copyright_header(file_path):
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
    except Exception:
        return False
```

## Data Models

### File Processing Record

```python
@dataclass
class FileProcessingResult:
    file_path: str
    file_type: str
    had_header: bool
    header_added: bool
    error: Optional[str] = None
    backup_created: bool = False
```

### Processing Summary

```python
@dataclass
class ProcessingSummary:
    total_files: int
    files_processed: int
    files_skipped: int
    files_with_errors: int
    files_by_type: Dict[str, int]
    errors: List[str]
```

## Error Handling

### 1. File Access Errors
- **Issue**: Permission denied, file locked, etc.
- **Solution**: Log error, continue with other files, provide summary of failed files

### 2. Encoding Issues
- **Issue**: Files with non-UTF-8 encoding
- **Solution**: Try multiple encodings (utf-8, latin-1, cp1252), log encoding used

### 3. Binary Files
- **Issue**: Accidentally processing binary files
- **Solution**: Detect binary files and skip them

### 4. Large Files
- **Issue**: Memory issues with very large files
- **Solution**: Process files in chunks, set reasonable size limits

### 5. Backup and Recovery
- **Issue**: Need to recover if header addition breaks files
- **Solution**: Create backups before modification, provide rollback functionality

```python
def create_backup(file_path):
    """Create backup of file before modification"""
    backup_path = file_path + '.backup'
    shutil.copy2(file_path, backup_path)
    return backup_path

def rollback_file(file_path):
    """Restore file from backup"""
    backup_path = file_path + '.backup'
    if os.path.exists(backup_path):
        shutil.copy2(backup_path, file_path)
        os.remove(backup_path)
        return True
    return False
```

## Testing Strategy

### 1. Unit Tests
- Test header template generation for each file type
- Test file type detection
- Test header detection logic
- Test special case handling (shebangs, doctypes)

### 2. Integration Tests
- Test processing of sample files
- Test backup and rollback functionality
- Test error handling with problematic files

### 3. End-to-End Tests
- Test processing entire project directory
- Verify files still function after header addition
- Test that build processes continue to work

### 4. Regression Tests
- Verify Python files still execute
- Verify JavaScript files still load in browsers
- Verify HTML files still render correctly
- Verify CSS files still apply styles

## Implementation Phases

### Phase 1: Core Infrastructure
1. Create header templates for each file type
2. Implement file discovery system
3. Implement header detection logic
4. Create basic file processing engine

### Phase 2: Special Case Handling
1. Handle shebang lines in Python/shell scripts
2. Handle DOCTYPE declarations in HTML
3. Handle existing comments and docstrings
4. Implement backup and rollback functionality

### Phase 3: Batch Processing
1. Implement batch processing of existing files
2. Add progress reporting and logging
3. Create summary reporting
4. Add error recovery mechanisms

### Phase 4: Integration and Testing
1. Test with actual project files
2. Verify functionality is preserved
3. Update build processes if needed
4. Create documentation and guidelines

## Quality Assurance

### Pre-Processing Validation
- Verify all target files are accessible
- Check available disk space for backups
- Validate header templates are properly formatted

### Post-Processing Validation
- Verify headers were added correctly
- Check that file functionality is preserved
- Validate syntax of modified files
- Confirm build processes still work

### Rollback Procedures
- Maintain backups of all modified files
- Provide easy rollback mechanism
- Log all changes for audit trail
- Test rollback functionality before deployment