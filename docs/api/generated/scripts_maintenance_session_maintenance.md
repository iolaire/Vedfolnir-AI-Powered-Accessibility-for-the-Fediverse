# scripts.maintenance.session_maintenance

Unified Session Maintenance CLI

Provides a unified interface for all session cleanup and maintenance utilities.
Combines automated cleanup, analytics, and database maintenance in one tool.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/scripts/maintenance/session_maintenance.py`

## Classes

### UnifiedSessionMaintenance

```python
class UnifiedSessionMaintenance
```

Unified session maintenance interface

**Methods:**

#### __init__

```python
def __init__(self, config: Config)
```

**Type:** Instance method

#### run_full_maintenance

```python
def run_full_maintenance(self, dry_run: bool) -> dict
```

Run complete maintenance cycle

**Type:** Instance method

#### _generate_maintenance_summary

```python
def _generate_maintenance_summary(self, results: dict) -> dict
```

Generate maintenance summary

**Type:** Instance method

## Functions

### main

```python
def main()
```

Main entry point

