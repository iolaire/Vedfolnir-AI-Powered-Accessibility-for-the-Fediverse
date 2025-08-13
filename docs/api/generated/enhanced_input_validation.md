# enhanced_input_validation

Enhanced Input Validation Middleware

Provides comprehensive input validation and sanitization.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/enhanced_input_validation.py`

## Classes

### EnhancedInputValidator

```python
class EnhancedInputValidator
```

Enhanced input validation and sanitization

**Class Variables:**
- `ALLOWED_TAGS`
- `ALLOWED_ATTRIBUTES`

**Methods:**

#### sanitize_html

```python
def sanitize_html(text)
```

Sanitize HTML content

**Decorators:**
- `@staticmethod`

**Type:** Static method

#### sanitize_sql

```python
def sanitize_sql(text)
```

Sanitize text to prevent SQL injection

**Decorators:**
- `@staticmethod`

**Type:** Static method

#### sanitize_xss

```python
def sanitize_xss(text)
```

Sanitize text to prevent XSS

**Decorators:**
- `@staticmethod`

**Type:** Static method

#### validate_length

```python
def validate_length(text, max_length)
```

Validate text length

**Decorators:**
- `@staticmethod`

**Type:** Static method

#### validate_filename

```python
def validate_filename(filename)
```

Validate and sanitize filename

**Decorators:**
- `@staticmethod`

**Type:** Static method

#### validate_email

```python
def validate_email(email)
```

Validate email format

**Decorators:**
- `@staticmethod`

**Type:** Static method

#### validate_url

```python
def validate_url(url)
```

Validate URL format and scheme

**Decorators:**
- `@staticmethod`

**Type:** Static method

## Functions

### enhanced_input_validation

```python
def enhanced_input_validation(f)
```

Decorator for enhanced input validation

### _validate_json_recursive

```python
def _validate_json_recursive(data, validator, depth)
```

Recursively validate JSON data

