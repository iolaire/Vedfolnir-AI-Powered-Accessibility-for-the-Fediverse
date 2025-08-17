# Web Application Startup Guidelines

## Command Patterns

When documenting or instructing users on how to start the web application, always use the appropriate command pattern based on the context:

### For Testing and Development (Non-blocking)

Use this pattern when the user needs to continue interacting with the terminal or when testing the application:

```bash
python web_app.py & sleep 10
```

**When to use:**
- Testing scenarios where the chat/terminal needs to remain interactive
- Development workflows where you need to run additional commands
- Automated testing scripts
- Documentation examples where users will perform additional steps

### For Production (Blocking)

Use this pattern for production deployments or when the application should run in the foreground:

```bash
python web_app.py
```

**When to use:**
- Production deployment instructions
- When the application should run as the primary process
- Docker containers or systemd services
- When no additional terminal interaction is needed

### Documentation Standards

#### In Steering Documents
Always provide both patterns with clear context:

```bash
# For testing/development (non-blocking)
python web_app.py & sleep 10

# For production (blocking)
python web_app.py
```

#### In User-Facing Documentation
Provide both options with explanations:

```bash
# For testing/development (non-blocking)
python web_app.py & sleep 10

# For production (blocking)
python web_app.py
```

#### In Test Documentation
Default to non-blocking pattern:

```bash
python web_app.py & sleep 10
```

## Implementation Notes

### The `& sleep 10` Pattern

- `&` runs the process in the background
- `sleep 10` gives the application time to start up
- This allows the terminal to remain interactive
- Prevents blocking in chat/AI assistant interactions

### Process Management

When using the non-blocking pattern, document how to stop the process:

```bash
# Find the process
ps aux | grep "python.*web_app.py" | grep -v grep

# Stop the process
kill <process_id>

# Or use pkill
pkill -f "python web_app.py"
```

### Service Management

For production deployments, prefer service management:

```bash
# systemd service
sudo systemctl start vedfolnir
sudo systemctl enable vedfolnir

# Docker
docker run -d vedfolnir

# Docker Compose
docker-compose up -d
```

## File Updates Required

When updating documentation, ensure these files use the correct patterns:

### Technical Documentation
- `.kiro/steering/tech.md` ✅ Updated
- `docs/user_guide.md` ✅ Updated
- `docs/platform_setup.md` ✅ Updated
- `docs/troubleshooting.md` - Check for updates needed
- `docs/deployment.md` - Check for updates needed

### Test Documentation
- `tests/frontend/README.md` ✅ Updated
- Any test scripts or documentation

### README Files
- Main `README.md` - Check for updates needed
- Module-specific README files

## Consistency Rules

1. **Always provide context** - Explain when to use which pattern
2. **Default to non-blocking in tests** - Use `& sleep 10` for testing scenarios
3. **Use blocking for production** - Use plain `python web_app.py` for production
4. **Document process management** - Always explain how to stop background processes
5. **Update all references** - Ensure consistency across all documentation

## Validation

To ensure all documentation follows these guidelines:

```bash
# Search for web_app.py references
grep -r "python web_app.py" . --exclude-dir=.git --exclude-dir=__pycache__

# Check for missing & sleep 10 in test contexts
grep -r "python web_app.py" tests/ docs/

# Verify steering document compliance
grep -r "python web_app.py" .kiro/steering/
```

## Examples

### Good Examples

```bash
# Testing scenario
python web_app.py & sleep 10

# Production scenario with context
python web_app.py  # Runs in foreground for production

# Complete example with both options
# For testing/development (non-blocking)
python web_app.py & sleep 10

# For production (blocking)
python web_app.py
```

### Avoid

```bash
# Missing context
python web_app.py

# No non-blocking option for tests
python web_app.py  # This blocks the terminal

# Inconsistent patterns across documentation
```

This guideline ensures consistent, user-friendly documentation that works well for both interactive testing and production deployment scenarios.