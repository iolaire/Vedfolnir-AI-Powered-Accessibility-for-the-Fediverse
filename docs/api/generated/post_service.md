# post_service

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/post_service.py`

## Classes

### PostingService

```python
class PostingService
```

Service for posting approved captions to ActivityPub

**Methods:**

#### __init__

```python
def __init__(self, config: Config)
```

**Type:** Instance method

#### post_approved_captions

```python
async def post_approved_captions(self, limit: int) -> dict
```

Post approved captions to ActivityPub server

**Type:** Instance method

#### _post_single_image

```python
async def _post_single_image(self, ap_client: ActivityPubClient, image: Image) -> bool
```

Post a single image's caption

**Type:** Instance method

## Functions

### main

```python
async def main()
```

CLI interface for posting service

