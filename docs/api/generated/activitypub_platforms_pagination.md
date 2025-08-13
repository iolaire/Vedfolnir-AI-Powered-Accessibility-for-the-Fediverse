# activitypub_platforms_pagination

Enhanced version of the PixelfedPlatform class with pagination support.
This file contains only the modified PixelfedPlatform class with pagination support.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/activitypub_platforms_pagination.py`

## Classes

### PixelfedPlatformWithPagination

```python
class PixelfedPlatformWithPagination
```

Enhanced adapter for Pixelfed platform with pagination support

**Methods:**

#### __init__

```python
def __init__(self, config)
```

**Type:** Instance method

#### get_user_posts

```python
async def get_user_posts(self, client, user_id: str, limit: int) -> List[Dict[str, Any]]
```

Retrieve user's posts from Pixelfed using API with pagination support

Args:
    client: The ActivityPubClient instance
    user_id: The user ID to fetch posts for
    limit: Maximum number of posts to fetch
    
Returns:
    List of posts in ActivityPub format

**Type:** Instance method

