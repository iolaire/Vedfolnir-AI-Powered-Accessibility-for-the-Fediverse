# batch_update_service

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/batch_update_service.py`

## Classes

### BatchUpdateService

```python
class BatchUpdateService
```

Service for batch updating approved captions to ActivityPub

**Methods:**

#### __init__

```python
def __init__(self, config: Config)
```

**Type:** Instance method

#### batch_update_captions

```python
async def batch_update_captions(self, limit: int) -> dict
```

Update approved captions in batches to reduce API calls

**Type:** Instance method

#### _process_post_group_with_semaphore

```python
async def _process_post_group_with_semaphore(self, semaphore, ap_client, post_id, images)
```

Process a post group with semaphore for concurrency control

**Type:** Instance method

#### _process_post_group

```python
async def _process_post_group(self, ap_client: ActivityPubClient, post_id: str, images: List[Image]) -> dict
```

Process a group of images belonging to the same post

**Type:** Instance method

#### _verify_updates

```python
async def _verify_updates(self, ap_client: ActivityPubClient, post_id: str, updated_images: List[Image]) -> dict
```

Verify that updates were applied correctly

**Type:** Instance method

#### _group_images_by_post

```python
def _group_images_by_post(self, images: List[Image]) -> List[Tuple[str, List[Image]]]
```

Group images by their parent post to reduce API calls

**Type:** Instance method

## Functions

### main

```python
async def main()
```

CLI interface for batch update service

