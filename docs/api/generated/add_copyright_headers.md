# add_copyright_headers

Copyright Header Utility Script

This script adds copyright and license headers to all source code files in the project.
It supports Python, JavaScript, HTML, CSS, Shell, and SQL files with appropriate comment syntax.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/add_copyright_headers.py`

## Constants

- `HEADER_TEMPLATES`
- `FILE_TYPE_MAPPING`
- `INCLUDE_PATTERNS`
- `EXCLUDE_PATTERNS`

## Classes

### FileProcessingResult

```python
class FileProcessingResult
```

Result of processing a single file

**Decorators:**
- `@dataclass`

### ProcessingSummary

```python
class ProcessingSummary
```

Summary of processing results

**Decorators:**
- `@dataclass`

### CopyrightHeaderProcessor

```python
class CopyrightHeaderProcessor
```

Main class for processing copyright headers

**Methods:**

#### __init__

```python
def __init__(self, root_dir: str, create_backups: bool, dry_run: bool)
```

**Type:** Instance method

#### detect_file_type

```python
def detect_file_type(self, file_path: Path) -> Optional[str]
```

Detect file type based on extension

**Type:** Instance method

#### has_copyright_header

```python
def has_copyright_header(self, file_path: Path) -> bool
```

Check if file already has copyright header

**Type:** Instance method

#### create_backup

```python
def create_backup(self, file_path: Path) -> bool
```

Create backup of file before modification

**Type:** Instance method

#### add_header_to_file

```python
def add_header_to_file(self, file_path: Path, file_type: str) -> FileProcessingResult
```

Add copyright header to a single file

**Type:** Instance method

#### _handle_special_cases

```python
def _handle_special_cases(self, content: str, header_lines: List[str], file_type: str) -> str
```

Handle special cases like shebangs, doctypes, etc.

**Type:** Instance method

#### scan_project_files

```python
def scan_project_files(self) -> List[Path]
```

Scan project for source code files

**Type:** Instance method

#### process_all_files

```python
def process_all_files(self) -> ProcessingSummary
```

Process all source files in the project

**Type:** Instance method

#### print_summary

```python
def print_summary(self, summary: ProcessingSummary)
```

Print processing summary

**Type:** Instance method

## Functions

### main

```python
def main()
```

Main function

