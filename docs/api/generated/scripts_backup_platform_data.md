# scripts.backup_platform_data

Platform-aware backup script

Creates backups that preserve platform data integrity.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/scripts/backup_platform_data.py`

## Classes

### PlatformDataBackup

```python
class PlatformDataBackup
```

Platform-aware data backup utility

**Methods:**

#### __init__

```python
def __init__(self)
```

**Type:** Instance method

#### create_backup_directory

```python
def create_backup_directory(self)
```

Create backup directory structure

**Type:** Instance method

#### backup_database

```python
def backup_database(self)
```

Backup database with platform data

**Type:** Instance method

#### _create_database_info

```python
def _create_database_info(self, db_path)
```

Create database information file

**Type:** Instance method

#### backup_platform_data

```python
def backup_platform_data(self)
```

Backup platform-specific data

**Type:** Instance method

#### backup_image_files

```python
def backup_image_files(self)
```

Backup image files

**Type:** Instance method

#### backup_configuration

```python
def backup_configuration(self)
```

Backup configuration files

**Type:** Instance method

#### _backup_env_file

```python
def _backup_env_file(self, src_path, dst_path)
```

Backup .env file with sensitive data removed

**Type:** Instance method

#### backup_logs

```python
def backup_logs(self)
```

Backup log files

**Type:** Instance method

#### create_backup_manifest

```python
def create_backup_manifest(self)
```

Create backup manifest file

**Type:** Instance method

#### run_backup

```python
def run_backup(self)
```

Run complete backup process

**Type:** Instance method

## Functions

### main

```python
def main()
```

Main backup function

