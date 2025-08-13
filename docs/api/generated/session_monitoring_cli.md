# session_monitoring_cli

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/session_monitoring_cli.py`

## Functions

### session_monitoring

```python
def session_monitoring()
```

Session performance monitoring commands.

**Decorators:**
- `@click.group()`

### status

```python
def status()
```

Show current session performance status.

**Decorators:**
- `@session_monitoring.command()`
- `@with_appcontext`

### summary

```python
def summary()
```

Show detailed performance summary.

**Decorators:**
- `@session_monitoring.command()`
- `@with_appcontext`

### metrics

```python
def metrics(format)
```

Export current metrics.

**Decorators:**
- `@session_monitoring.command()`
- `@with_appcontext`
- `@click.option('--format', type=click.Choice(['json', 'text']), default='text', help='Output format (json or text)')`

### alerts

```python
def alerts(threshold)
```

Check for performance alerts.

**Decorators:**
- `@session_monitoring.command()`
- `@with_appcontext`
- `@click.option('--threshold', type=float, default=1.0, help='Alert threshold for slow operations (seconds)')`

### enable_periodic_logging

```python
def enable_periodic_logging(interval)
```

Enable periodic performance logging.

**Decorators:**
- `@session_monitoring.command()`
- `@with_appcontext`
- `@click.option('--interval', type=int, default=300, help='Logging interval in seconds')`

### register_session_monitoring_commands

```python
def register_session_monitoring_commands(app)
```

Register session monitoring CLI commands with the Flask app.

