# Ollama Context Configuration

## Overview

The `OLLAMA_MODEL_CONTEXT` setting controls the context window size (num_ctx parameter) sent to the Ollama API when generating image captions. This parameter affects how much context the model can consider when generating responses.

## Configuration

### Environment Variable

Add the following to your `.env` file:

```bash
OLLAMA_MODEL_CONTEXT=4096
```

### Default Value

If not specified, the default context size is `4096`.

### Recommended Values

- **4096** (default): Good balance of performance and capability for most image captioning tasks
- **8192**: Larger context for more complex images or longer prompts
- **2048**: Smaller context for faster processing with simpler images

## Usage

The context size is automatically included in all Ollama API requests as part of the `options` parameter:

```json
{
  "model": "llava:7b",
  "prompt": "Describe this image...",
  "images": ["base64_image_data"],
  "stream": false,
  "options": {
    "num_ctx": 4096
  }
}
```

## Performance Considerations

- **Larger context sizes** provide more capability but use more memory and may be slower
- **Smaller context sizes** are faster but may limit the model's ability to handle complex prompts
- The optimal size depends on your specific use case and hardware capabilities

## Testing

You can test your configuration using the provided test script:

```bash
python scripts/debug/test_ollama_context_config.py
```

This will verify that:
- The configuration is loaded correctly
- The environment variable is read properly
- The context size is included in API payloads

## Troubleshooting

### Configuration Not Loading

If the context size isn't being applied:

1. Verify the environment variable is set: `echo $OLLAMA_MODEL_CONTEXT`
2. Restart the application after changing the `.env` file
3. Check the logs for context size information during initialization

### Performance Issues

If you experience performance issues:

- Try reducing the context size (e.g., from 4096 to 2048)
- Monitor Ollama server resources during caption generation
- Consider your hardware capabilities when setting the context size

## Related Configuration

This setting works alongside other Ollama configuration options:

- `OLLAMA_URL`: Ollama server URL
- `OLLAMA_MODEL`: Model name (e.g., llava:7b)
- `OLLAMA_TIMEOUT`: Request timeout in seconds