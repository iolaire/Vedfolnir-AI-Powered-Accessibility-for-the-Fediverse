# caption_review_integration

Caption Review Integration

This module provides integration between caption generation and the review interface,
including batch grouping, bulk operations, and enhanced review workflows.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/caption_review_integration.py`

## Classes

### CaptionReviewIntegration

```python
class CaptionReviewIntegration
```

Integration service for caption generation and review workflows

**Methods:**

#### __init__

```python
def __init__(self, db_manager: DatabaseManager)
```

**Type:** Instance method

#### create_review_batch_from_task

```python
def create_review_batch_from_task(self, task_id: str, user_id: int) -> Optional[Dict[str, Any]]
```

Create a review batch from completed caption generation task

Args:
    task_id: The completed task ID
    user_id: The user ID for authorization
    
Returns:
    Dict with batch information or None if task not found

**Type:** Instance method

#### get_review_batches

```python
def get_review_batches(self, user_id: int, platform_connection_id: Optional[int], days_back: int, limit: int) -> List[Dict[str, Any]]
```

Get recent review batches for a user

Args:
    user_id: The user ID
    platform_connection_id: Optional platform filter
    days_back: Number of days to look back
    limit: Maximum number of batches to return
    
Returns:
    List of batch information dictionaries

**Type:** Instance method

#### get_batch_images

```python
def get_batch_images(self, batch_id: str, user_id: int, status_filter: Optional[ProcessingStatus], sort_by: str, sort_order: str, page: int, per_page: int) -> Dict[str, Any]
```

Get images from a specific batch with filtering and pagination

Args:
    batch_id: The batch ID (task ID)
    user_id: The user ID for authorization
    status_filter: Optional status filter
    sort_by: Field to sort by
    sort_order: Sort order ('asc' or 'desc')
    page: Page number (1-based)
    per_page: Items per page
    
Returns:
    Dict with images and pagination info

**Type:** Instance method

#### bulk_approve_batch

```python
def bulk_approve_batch(self, batch_id: str, user_id: int, image_ids: Optional[List[int]], reviewer_notes: Optional[str]) -> Dict[str, Any]
```

Bulk approve images in a batch

Args:
    batch_id: The batch ID (task ID)
    user_id: The user ID for authorization
    image_ids: Optional list of specific image IDs (approves all if None)
    reviewer_notes: Optional notes for all approved images
    
Returns:
    Dict with operation results

**Type:** Instance method

#### bulk_reject_batch

```python
def bulk_reject_batch(self, batch_id: str, user_id: int, image_ids: Optional[List[int]], reviewer_notes: Optional[str]) -> Dict[str, Any]
```

Bulk reject images in a batch

Args:
    batch_id: The batch ID (task ID)
    user_id: The user ID for authorization
    image_ids: Optional list of specific image IDs (rejects all if None)
    reviewer_notes: Optional notes for all rejected images
    
Returns:
    Dict with operation results

**Type:** Instance method

#### update_batch_image_caption

```python
def update_batch_image_caption(self, image_id: int, user_id: int, new_caption: str, batch_id: Optional[str]) -> Dict[str, Any]
```

Update caption for a single image in a batch

Args:
    image_id: The image ID
    user_id: The user ID for authorization
    new_caption: The new caption text
    batch_id: Optional batch ID for additional validation
    
Returns:
    Dict with operation results

**Type:** Instance method

#### get_batch_statistics

```python
def get_batch_statistics(self, batch_id: str, user_id: int) -> Optional[Dict[str, Any]]
```

Get statistics for a review batch

Args:
    batch_id: The batch ID (task ID)
    user_id: The user ID for authorization
    
Returns:
    Dict with batch statistics or None if not found

**Type:** Instance method

#### _image_to_dict

```python
def _image_to_dict(self, image: Image) -> Dict[str, Any]
```

Convert Image object to dictionary for JSON serialization

**Type:** Instance method

