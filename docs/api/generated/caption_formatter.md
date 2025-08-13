# caption_formatter

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/caption_formatter.py`

## Classes

### CaptionFormatter

```python
class CaptionFormatter
```

Enhances caption formatting and performs grammar checking.

This class provides functionality to:
- Improve sentence structure
- Fix common grammatical errors
- Ensure proper capitalization and punctuation
- Format captions for optimal accessibility

**Methods:**

#### __init__

```python
def __init__(self, caption_config)
```

Initialize the caption formatter

**Type:** Instance method

#### format_caption

```python
def format_caption(self, caption: str) -> str
```

Format and improve a caption

Args:
    caption: The original caption text
    
Returns:
    Improved caption with better formatting and grammar

**Type:** Instance method

#### _fix_capitalization

```python
def _fix_capitalization(self, text: str) -> str
```

Fix capitalization issues in the text

**Type:** Instance method

#### _fix_punctuation

```python
def _fix_punctuation(self, text: str) -> str
```

Fix punctuation issues in the text

**Type:** Instance method

#### _fix_common_errors

```python
def _fix_common_errors(self, text: str) -> str
```

Fix common grammatical and spelling errors

**Type:** Instance method

#### _improve_sentence_structure

```python
def _improve_sentence_structure(self, text: str) -> str
```

Improve the structure of sentences in the text

**Type:** Instance method

#### _check_grammar

```python
def _check_grammar(self, text: str) -> str
```

Check and correct grammar using LanguageTool

**Type:** Instance method

#### _final_cleanup

```python
def _final_cleanup(self, text: str) -> str
```

Perform final cleanup on the text

**Type:** Instance method

