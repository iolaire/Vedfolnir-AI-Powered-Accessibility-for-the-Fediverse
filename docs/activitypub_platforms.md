# ActivityPub Platform Support

The Vedfolnir now supports multiple ActivityPub platforms beyond just Pixelfed. This document explains how to configure and use the bot with different platforms.

## Supported Platforms

The following ActivityPub platforms are currently supported:

- **Pixelfed**: Image-focused platform similar to Instagram
- **Mastodon**: General-purpose microblogging platform
- **Pleroma**: Lightweight ActivityPub server

## Configuration

### Platform Selection

You can specify the platform type in your `.env` file:

```
# Explicitly set the platform type
ACTIVITYPUB_PLATFORM_TYPE=pixelfed
```

Valid values for `ACTIVITYPUB_PLATFORM_TYPE` are:
- `pixelfed`
- `mastodon`
- `pleroma`

If not specified, the bot will attempt to auto-detect the platform type based on the instance URL.

### Legacy Configuration

For backward compatibility, the `PIXELFED_API` environment variable is still supported:

```
# Legacy configuration (equivalent to ACTIVITYPUB_PLATFORM_TYPE=pixelfed)
PIXELFED_API=true
```

## Platform Detection

The bot includes a utility script to detect the platform type of an instance:

```bash
python detect_platform.py https://example.com
```

This will output the detected platform type and provide a configuration hint for your `.env` file.

## Platform-Specific Behavior

Each platform has slightly different APIs and behaviors:

### Pixelfed

- Uses the Pixelfed API for retrieving posts and updating media descriptions
- Optimized for image-focused content
- Supports direct media description updates

### Mastodon

- Uses the Mastodon API for retrieving posts and updating media descriptions
- Handles both text and media content
- Supports media description updates via the media endpoint

### Pleroma

- Uses the Pleroma API (compatible with Mastodon API) for retrieving posts and updating media descriptions
- Lightweight implementation with similar capabilities to Mastodon

## Implementation Details

The platform support is implemented using the Adapter pattern:

1. `ActivityPubPlatform`: Abstract base class defining the interface for all platform adapters
2. `PixelfedPlatform`, `MastodonPlatform`, `PleromaPlatform`: Concrete implementations for each platform
3. `get_platform_adapter()`: Factory function to get the appropriate adapter based on configuration or auto-detection

## Adding New Platforms

To add support for a new ActivityPub platform:

1. Create a new class that extends `ActivityPubPlatform`
2. Implement all required methods
3. Add platform detection logic
4. Update the `get_platform_adapter()` function to return your new adapter

Example:

```python
class NewPlatform(ActivityPubPlatform):
    @classmethod
    def detect_platform(cls, instance_url: str) -> bool:
        # Implement detection logic
        return 'newplatform' in instance_url
        
    # Implement all required methods...
```

Then update the factory function:

```python
def get_platform_adapter(config):
    # ...existing code...
    
    # Add your new platform
    if platform_type == 'newplatform':
        return NewPlatform(config)
    
    # ...existing code...
```