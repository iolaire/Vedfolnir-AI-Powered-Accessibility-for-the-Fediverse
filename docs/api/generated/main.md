# main

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/main.py`

## Classes

### Vedfolnir

```python
class Vedfolnir
```

Main bot class that orchestrates the alt text generation process

**Methods:**

#### __init__

```python
def __init__(self, config: Config, reprocess_all: bool)
```

**Type:** Instance method

#### run_multi_user

```python
async def run_multi_user(self, user_ids: List[str], skip_ollama)
```

Process multiple users in a single run

**Type:** Instance method

#### run

```python
async def run(self, user_id: str)
```

Main execution method for a single user (for backward compatibility)

**Type:** Instance method

#### _process_user

```python
async def _process_user(self, user_id: str, ap_client: ActivityPubClient, image_processor: ImageProcessor, caption_generator, batch_id: str)
```

Process a single user's posts

Args:
    user_id: The ID of the user to process
    ap_client: ActivityPub client instance
    image_processor: Image processor instance
    caption_generator: Caption generator instance (can be None if --no-ollama is set)
    batch_id: Optional batch ID to group runs that are part of the same batch

**Type:** Instance method

#### _create_processing_run

```python
def _create_processing_run(self, user_id: str, batch_id: str) -> ProcessingRun
```

Create a new processing run record

Args:
    user_id: The ID of the user being processed
    batch_id: Optional batch ID to group runs that are part of the same batch

**Type:** Instance method

#### _complete_processing_run

```python
def _complete_processing_run(self, error: str)
```

Complete the processing run record

**Type:** Instance method

#### _process_post

```python
async def _process_post(self, post: Dict[str, Any], ap_client: ActivityPubClient, image_processor: ImageProcessor, caption_generator)
```

Process a single post for alt text generation

**Type:** Instance method

#### _process_image

```python
async def _process_image(self, image_info: Dict[str, Any], db_post, image_processor: ImageProcessor, caption_generator: OllamaCaptionGenerator)
```

Process a single image to generate alt text

**Type:** Instance method

#### _log_retry_statistics

```python
def _log_retry_statistics(self)
```

Log retry statistics after processing run

**Type:** Instance method

#### _print_statistics

```python
def _print_statistics(self)
```

Print execution statistics

**Type:** Instance method

## Functions

### main

```python
async def main()
```

Main entry point

