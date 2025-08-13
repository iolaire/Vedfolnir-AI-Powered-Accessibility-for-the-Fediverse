# input_validation

Input validation utilities for security

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/input_validation.py`

## Classes

### InputValidator

```python
class InputValidator
```

Secure input validation and sanitization

**Methods:**

#### sanitize_string

```python
def sanitize_string(value: str, max_length: int) -> str
```

Sanitize string input

**Decorators:**
- `@staticmethod`

**Type:** Static method

#### validate_integer

```python
def validate_integer(value: Any, min_val: int, max_val: int) -> Optional[int]
```

Validate integer input

**Decorators:**
- `@staticmethod`

**Type:** Static method

#### validate_boolean

```python
def validate_boolean(value: Any) -> bool
```

Validate boolean input

**Decorators:**
- `@staticmethod`

**Type:** Static method

#### validate_form_data

```python
def validate_form_data(form_data: Dict[str, Any], schema: Dict[str, Dict]) -> Dict[str, Any]
```

Validate form data against schema

**Decorators:**
- `@staticmethod`

**Type:** Static method

## Functions

### validate_request_data

```python
def validate_request_data(schema: Dict[str, Dict])
```

Decorator for request data validation

