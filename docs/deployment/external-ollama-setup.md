# External Ollama API Setup for Docker Deployment

## Overview

Vedfolnir's Docker Compose deployment is configured to use an external Ollama API service running on the host system. This approach provides better resource management, GPU access, and allows the AI service to be shared across multiple applications.

## Prerequisites

### Host System Requirements

- **Operating System**: macOS, Linux, or Windows with Docker Desktop
- **Memory**: Minimum 8GB RAM (16GB+ recommended for LLaVA models)
- **GPU**: Optional but recommended for better performance
- **Network**: Ollama service must be accessible on localhost:11434

### Ollama Installation

1. **Install Ollama on Host System**:
   ```bash
   # macOS (using Homebrew)
   brew install ollama
   
   # Linux
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # Windows
   # Download from https://ollama.ai/download
   ```

2. **Start Ollama Service**:
   ```bash
   # Start Ollama service
   ollama serve
   
   # Verify service is running
   curl http://localhost:11434/api/version
   ```

3. **Install Required Models**:
   ```bash
   # Install LLaVA model (required for image captioning)
   ollama pull llava:7b
   
   # Verify model installation
   ollama list
   ```

## Docker Configuration

### Network Configuration

The Docker Compose configuration uses `host.docker.internal:11434` to access the external Ollama service:

```yaml
environment:
  OLLAMA_URL: http://host.docker.internal:11434
  DOCKER_DEPLOYMENT: "true"
```

### Host Networking Requirements

- **Port 11434**: Must be accessible from Docker containers
- **Firewall**: Ensure localhost:11434 is not blocked
- **Docker Desktop**: Must support `host.docker.internal` networking

## Configuration Files

### Environment Variables

Update your `.env` file:

```bash
# Ollama Configuration (External Service)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llava:7b
OLLAMA_TIMEOUT=60.0
OLLAMA_MODEL_CONTEXT=4096

# Docker Deployment Flag
DOCKER_DEPLOYMENT=true
```

### Application Configuration

The application automatically detects Docker deployment and uses the correct Ollama URL:

- **Local Development**: `http://localhost:11434`
- **Docker Deployment**: `http://host.docker.internal:11434`

## Health Checks

### Container Health Checks

The application container includes health checks for external Ollama connectivity:

```bash
# Manual health check from container
docker-compose exec vedfolnir /app/scripts/health/docker_ollama_health.sh --verbose

# Python-based health check
docker-compose exec vedfolnir python /app/scripts/health/check_ollama_external.py --verbose
```

### Host System Health Checks

Verify Ollama is running on the host:

```bash
# Check Ollama service status
curl http://localhost:11434/api/version

# Check available models
curl http://localhost:11434/api/tags

# Test model availability
ollama list | grep llava
```

## Troubleshooting

### Common Issues

1. **Connection Refused**:
   ```bash
   # Verify Ollama is running
   ps aux | grep ollama
   
   # Start Ollama if not running
   ollama serve
   ```

2. **Model Not Found**:
   ```bash
   # Install required model
   ollama pull llava:7b
   
   # Verify installation
   ollama list
   ```

3. **Docker Networking Issues**:
   ```bash
   # Test from container
   docker-compose exec vedfolnir curl -f http://host.docker.internal:11434/api/version
   
   # Check Docker Desktop settings
   # Ensure "Use Docker Compose V2" is enabled
   ```

4. **Firewall Blocking**:
   ```bash
   # macOS: Allow connections to localhost:11434
   # Linux: Check iptables rules
   # Windows: Check Windows Firewall settings
   ```

### Debug Commands

```bash
# Test connectivity from host
curl -v http://localhost:11434/api/version

# Test connectivity from container
docker-compose exec vedfolnir curl -v http://host.docker.internal:11434/api/version

# Check container logs
docker-compose logs vedfolnir | grep -i ollama

# Run health check with verbose output
docker-compose exec vedfolnir python /app/scripts/health/check_ollama_external.py --verbose --json
```

## Performance Optimization

### Host System Optimization

1. **GPU Acceleration** (if available):
   ```bash
   # Verify GPU support
   ollama run llava:7b --gpu
   ```

2. **Memory Management**:
   ```bash
   # Set Ollama memory limit
   export OLLAMA_MAX_LOADED_MODELS=1
   export OLLAMA_NUM_PARALLEL=1
   ```

3. **Model Preloading**:
   ```bash
   # Preload model to reduce first-request latency
   ollama run llava:7b "test" --keep-alive 24h
   ```

### Container Optimization

1. **Request Timeout**:
   ```bash
   # Increase timeout for large images
   OLLAMA_TIMEOUT=120.0
   ```

2. **Connection Pooling**:
   ```bash
   # Configure retry settings
   RETRY_MAX_ATTEMPTS=3
   RETRY_BASE_DELAY=1.0
   ```

## Security Considerations

### Network Security

- Ollama service runs on localhost only (not exposed externally)
- Docker containers access via internal networking
- No external ports exposed for Ollama

### Access Control

- Ollama API has no built-in authentication
- Access is restricted to localhost and Docker containers
- Consider using a reverse proxy for additional security

### Data Privacy

- Image data is sent to local Ollama service only
- No external API calls or data transmission
- All processing happens on the host system

## Monitoring and Maintenance

### Service Monitoring

```bash
# Monitor Ollama service
systemctl status ollama  # Linux with systemd

# Monitor resource usage
htop | grep ollama

# Monitor API requests
tail -f /var/log/ollama.log  # If logging is enabled
```

### Model Updates

```bash
# Update models
ollama pull llava:7b

# Clean up old models
ollama rm old_model_name

# List all models and sizes
ollama list
```

### Backup and Recovery

```bash
# Backup Ollama models directory
tar -czf ollama_models_backup.tar.gz ~/.ollama/models/

# Restore models
tar -xzf ollama_models_backup.tar.gz -C ~/
```

## Integration Testing

### Automated Tests

Run the integration test suite:

```bash
# Test external Ollama connectivity
python tests/integration/test_ollama_external_connectivity.py

# Test from Docker container
docker-compose exec vedfolnir python tests/integration/test_ollama_external_connectivity.py
```

### Manual Testing

```bash
# Test caption generation
docker-compose exec vedfolnir python -c "
from config import Config
from ollama_caption_generator import OllamaCaptionGenerator
config = Config()
generator = OllamaCaptionGenerator(config)
print('Ollama connectivity test passed')
"
```

## Support and Resources

### Documentation Links

- [Ollama Official Documentation](https://ollama.ai/docs)
- [Docker Desktop Networking](https://docs.docker.com/desktop/networking/)
- [LLaVA Model Information](https://ollama.ai/library/llava)

### Community Resources

- [Ollama GitHub Repository](https://github.com/ollama/ollama)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

### Troubleshooting Support

If you encounter issues:

1. Check the troubleshooting section above
2. Run health checks with verbose output
3. Review container logs for error messages
4. Verify host system Ollama installation
5. Test connectivity manually using curl commands