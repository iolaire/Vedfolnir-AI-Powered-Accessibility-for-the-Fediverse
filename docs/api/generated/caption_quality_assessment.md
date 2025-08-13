# caption_quality_assessment

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/caption_quality_assessment.py`

## Classes

### SimpleCaptionQualityAssessor

```python
class SimpleCaptionQualityAssessor
```

Simple caption quality assessor that doesn't rely on image classification

**Methods:**

#### __init__

```python
def __init__(self, config)
```

Initialize the quality assessor

**Type:** Instance method

#### assess_caption_quality

```python
def assess_caption_quality(self, caption: str, prompt_used: str) -> Dict[str, Any]
```

Assess the quality of a caption using simple heuristics

Args:
    caption: The caption text to assess
    prompt_used: Optional prompt used to generate the caption
    
Returns:
    Dictionary containing quality metrics and overall score

**Type:** Instance method

#### _assess_length

```python
def _assess_length(self, caption: str) -> int
```

Assess caption length

**Type:** Instance method

#### _assess_content

```python
def _assess_content(self, caption: str) -> int
```

Assess caption content quality

**Type:** Instance method

#### _assess_clarity

```python
def _assess_clarity(self, caption: str) -> int
```

Assess caption clarity

**Type:** Instance method

#### _has_quality_issues

```python
def _has_quality_issues(self, caption: str) -> bool
```

Check for specific quality issues that require review

**Type:** Instance method

#### _generate_feedback

```python
def _generate_feedback(self, caption: str, length_score: int, content_score: int, clarity_score: int) -> str
```

Generate feedback based on assessment scores

**Type:** Instance method

### CaptionQualityManager

```python
class CaptionQualityManager
```

Manages caption quality assessment and provides utilities for working with caption quality metrics.

This class serves as a central point for caption quality assessment, providing methods to:
- Assess caption quality using simple heuristics
- Format quality feedback for display in the UI
- Generate quality badges and visual indicators
- Filter and sort captions based on quality metrics

**Methods:**

#### __init__

```python
def __init__(self)
```

Initialize the caption quality manager

**Type:** Instance method

#### assess_caption_quality

```python
def assess_caption_quality(self, caption: str, image_category: str, prompt_used: str) -> Dict[str, Any]
```

Assess the quality of a caption

Args:
    caption: The caption text to assess
    image_category: Optional category of the image (ignored in simplified version)
    prompt_used: Optional prompt used to generate the caption
    
Returns:
    Dictionary containing quality metrics and overall score

**Type:** Instance method

#### get_quality_badge_class

```python
def get_quality_badge_class(self, score: int) -> str
```

Get the appropriate CSS class for a quality score badge

Args:
    score: The quality score (0-100)
    
Returns:
    CSS class name for the badge

**Type:** Instance method

#### get_quality_level_description

```python
def get_quality_level_description(self, quality_level: str) -> str
```

Get a user-friendly description of a quality level

Args:
    quality_level: The quality level string (poor, fair, good, excellent)
    
Returns:
    User-friendly description

**Type:** Instance method

#### format_feedback_for_display

```python
def format_feedback_for_display(self, feedback: str) -> str
```

Format feedback for display in the UI

Args:
    feedback: The raw feedback string
    
Returns:
    HTML-formatted feedback

**Type:** Instance method

#### get_quality_summary

```python
def get_quality_summary(self, metrics: Dict[str, Any]) -> str
```

Get a concise summary of quality metrics

Args:
    metrics: The quality metrics dictionary
    
Returns:
    Concise summary string

**Type:** Instance method

#### should_flag_for_review

```python
def should_flag_for_review(self, caption: str, metrics: Dict[str, Any]) -> bool
```

Determine if a caption should be flagged for special review

Args:
    caption: The caption text
    metrics: Optional quality metrics dictionary
    
Returns:
    True if the caption should be flagged for review

**Type:** Instance method

