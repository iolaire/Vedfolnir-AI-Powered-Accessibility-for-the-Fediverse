# docs.api.generate_api_docs

API Documentation Generator

This script extracts function and class signatures from Python source files
and generates comprehensive API documentation with usage examples.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/docs/api/generate_api_docs.py`

## Classes

### FunctionSignature

```python
class FunctionSignature
```

Represents a function signature with metadata

**Decorators:**
- `@dataclass`

### ClassSignature

```python
class ClassSignature
```

Represents a class signature with metadata

**Decorators:**
- `@dataclass`

### ModuleSignature

```python
class ModuleSignature
```

Represents a module signature with metadata

**Decorators:**
- `@dataclass`

### APIDocumentationGenerator

```python
class APIDocumentationGenerator
```

Generates comprehensive API documentation from Python source files

**Methods:**

#### __init__

```python
def __init__(self, project_root: str)
```

**Type:** Instance method

#### extract_module_signature

```python
def extract_module_signature(self, file_path: Path) -> ModuleSignature
```

Extract signature information from a Python module

**Type:** Instance method

#### _extract_function_signature

```python
def _extract_function_signature(self, node: ast.FunctionDef) -> FunctionSignature
```

Extract function signature from AST node

**Type:** Instance method

#### _extract_class_signature

```python
def _extract_class_signature(self, node: ast.ClassDef) -> ClassSignature
```

Extract class signature from AST node

**Type:** Instance method

#### scan_project

```python
def scan_project(self, exclude_patterns: List[str]) -> None
```

Scan the entire project for Python files and extract signatures

**Type:** Instance method

#### generate_markdown_documentation

```python
def generate_markdown_documentation(self, output_dir: Path) -> None
```

Generate markdown documentation for all modules

**Type:** Instance method

#### _generate_index_file

```python
def _generate_index_file(self, output_dir: Path) -> None
```

Generate index file with all modules

**Type:** Instance method

#### _generate_module_documentation

```python
def _generate_module_documentation(self, module_sig: ModuleSignature, output_dir: Path) -> None
```

Generate documentation for a single module

**Type:** Instance method

#### _write_class_documentation

```python
def _write_class_documentation(self, f, class_sig: ClassSignature) -> None
```

Write documentation for a class

**Type:** Instance method

#### _write_function_documentation

```python
def _write_function_documentation(self, f, func_sig: FunctionSignature, is_method: bool) -> None
```

Write documentation for a function

**Type:** Instance method

## Functions

### main

```python
def main()
```

Main function to generate API documentation

