# Batch Update Functionality

The Vedfolnir includes a batch update service that efficiently updates approved captions to ActivityPub platforms. This service provides several advantages over the traditional single-image update approach:

1. **Reduced API Calls**: Groups images by post to minimize API calls
2. **Verification**: Verifies that updates were applied correctly
3. **Rollback**: Automatically rolls back failed updates to maintain consistency
4. **Concurrency**: Processes multiple batches concurrently for better performance

## Configuration

The batch update functionality can be configured through environment variables:

```
# Batch Update Configuration
BATCH_UPDATE_ENABLED=true           # Enable/disable batch updates
BATCH_UPDATE_SIZE=5                 # Number of posts to process in each batch
BATCH_UPDATE_MAX_CONCURRENT=2       # Maximum number of concurrent batches
BATCH_UPDATE_VERIFICATION_DELAY=2   # Delay in seconds before verification
BATCH_UPDATE_ROLLBACK_ON_FAILURE=true  # Enable/disable rollback on failure
```

## Command-Line Interface

The batch update service can be run from the command line using the `batch_update_cli.py` script:

```bash
# Process up to 50 approved images
python batch_update_cli.py --limit 50

# Process with custom batch size and concurrency
python batch_update_cli.py --limit 100 --batch-size 10 --concurrent 3

# Disable rollback on failure
python batch_update_cli.py --no-rollback

# Simulate updates without making changes
python batch_update_cli.py --dry-run

# Enable verbose logging
python batch_update_cli.py --verbose
```

## Programmatic Usage

The batch update service can also be used programmatically:

```python
from config import Config
from batch_update_service import BatchUpdateService

# Load configuration
config = Config()

# Create batch update service
service = BatchUpdateService(config)

# Run batch update
stats = await service.batch_update_captions(limit=50)

# Process results
print(f"Processed: {stats['processed']}")
print(f"Successful: {stats['successful']}")
print(f"Failed: {stats['failed']}")
print(f"Verified: {stats['verified']}")
print(f"Rollbacks: {stats['rollbacks']}")
```

## How It Works

1. **Grouping**: Images are grouped by their parent post to reduce API calls
2. **Batching**: Posts are processed in batches for better performance
3. **Concurrency**: Multiple batches are processed concurrently with a semaphore for control
4. **Verification**: After updates, the service verifies that changes were applied correctly
5. **Rollback**: If verification fails, the service attempts to roll back changes

## Error Handling

The batch update service includes comprehensive error handling:

- **API Errors**: Retries API calls with exponential backoff
- **Verification Failures**: Attempts to roll back changes to maintain consistency
- **Detailed Logging**: Provides detailed logs for troubleshooting
- **Error Statistics**: Returns detailed statistics about errors

## Integration with Web Interface

The batch update service is integrated with the web interface through the `PostingService` class. When batch updates are enabled, the `post_approved_captions` method uses the batch update service instead of the traditional single-image approach.