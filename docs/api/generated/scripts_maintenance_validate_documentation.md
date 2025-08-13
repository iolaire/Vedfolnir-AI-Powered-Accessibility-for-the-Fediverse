# scripts.maintenance.validate_documentation

Documentation validation script for Vedfolnir.

This script validates:
- Configuration examples in documentation
- Code snippets for syntax errors
- Environment variable references
- Link validity (basic checks)

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/scripts/maintenance/validate_documentation.py`

## Classes

### DocumentationValidator

```python
class DocumentationValidator
```

**Methods:**

#### __init__

```python
def __init__(self)
```

**Type:** Instance method

#### _load_config_variables

```python
def _load_config_variables(self) -> Set[str]
```

Load all configuration variables from config.py

**Type:** Instance method

#### validate_file

```python
def validate_file(self, filepath: str) -> None
```

Validate a single documentation file

**Type:** Instance method

#### _validate_code_blocks

```python
def _validate_code_blocks(self, filepath: str, content: str) -> None
```

Validate code blocks for syntax errors

**Type:** Instance method

#### _validate_env_vars

```python
def _validate_env_vars(self, filepath: str, content: str) -> None
```

Validate environment variable references

**Type:** Instance method

#### _validate_config_examples

```python
def _validate_config_examples(self, filepath: str, content: str) -> None
```

Validate configuration examples

**Type:** Instance method

#### _validate_links

```python
def _validate_links(self, filepath: str, content: str) -> None
```

Basic link validation

**Type:** Instance method

#### validate_all

```python
def validate_all(self) -> bool
```

Validate all documentation files

**Type:** Instance method

#### _validate_example_config

```python
def _validate_example_config(self, filepath: str) -> None
```

Validate example configuration files

**Type:** Instance method

#### print_results

```python
def print_results(self) -> None
```

Print validation results

**Type:** Instance method

## Functions

### main

```python
def main()
```

Main function

