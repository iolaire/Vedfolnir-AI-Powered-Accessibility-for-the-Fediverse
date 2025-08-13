# scripts.maintenance.check_expired_media

Script to check for and optionally clean up expired media attachments.

Mastodon and Pixelfed media attachments expire after a certain period (typically 24-48 hours).
This script helps identify images that may have expired media attachments.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/scripts/maintenance/check_expired_media.py`

## Functions

### check_expired_media

```python
def check_expired_media(days_threshold, dry_run)
```

Check for images with potentially expired media attachments.

Args:
    days_threshold: Number of days after which media is considered potentially expired
    dry_run: If True, only report findings without making changes

### main

```python
def main()
```

Main function

