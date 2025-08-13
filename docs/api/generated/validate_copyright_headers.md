# validate_copyright_headers

Copyright Header Validation Script

This script validates that all source code files in the project have proper copyright headers.
It provides compliance checking and reporting functionality.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/validate_copyright_headers.py`

## Constants

- `FILE_TYPE_MAPPING`
- `INCLUDE_PATTERNS`
- `EXCLUDE_PATTERNS`

## Classes

### ValidationResult

```python
class ValidationResult
```

Result of validating a single file

**Decorators:**
- `@dataclass`

### ValidationSummary

```python
class ValidationSummary
```

Summary of validation results

**Decorators:**
- `@dataclass`

### CopyrightHeaderValidator

```python
class CopyrightHeaderValidator
```

Main class for validating copyright headers

**Methods:**

#### __init__

```python
def __init__(self, root_dir: str)
```

**Type:** Instance method

#### detect_file_type

```python
def detect_file_type(self, file_path: Path) -> Optional[str]
```

Detect file type based on extension

**Type:** Instance method

#### validate_copyright_header

```python
def validate_copyright_header(self, file_path: Path) -> ValidationResult
```

Validate copyright header in a single file

**Type:** Instance method

#### scan_project_files

```python
def scan_project_files(self) -> List[Path]
```

Scan project for source code files

**Type:** Instance method

#### validate_all_files

```python
def validate_all_files(self) -> ValidationSummary
```

Validate all source files in the project

**Type:** Instance method

#### print_summary

```python
def print_summary(self, summary: ValidationSummary, verbose: bool)
```

Print validation summary

**Type:** Instance method

#### print_detailed_report

```python
def print_detailed_report(self, summary: ValidationSummary)
```

Print detailed validation report

**Type:** Instance method

## Functions

### main

```python
def main()
```

Main function

