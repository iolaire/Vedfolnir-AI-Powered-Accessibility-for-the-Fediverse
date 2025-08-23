# MySQL Database Architecture

## Database Migration from SQLite

**IMPORTANT**: Vedfolnir has migrated from SQLite to MySQL/MariaDB for improved performance, scalability, and enterprise features. SQLite is no longer supported.

### Migration Benefits
- **Performance**: Significantly improved query performance and concurrent access
- **Scalability**: Support for multiple application instances and high-volume processing
- **Enterprise Features**: Advanced indexing, connection pooling, and optimization
- **Security**: Enhanced security features and audit capabilities
- **Reliability**: Better data integrity and backup/recovery options

### Migration Tools
For existing SQLite users, comprehensive migration tools are available:

```bash
# Run migration with backup (recommended)
python scripts/mysql_migration/migrate_to_mysql.py --backup

# Verify migration results
python scripts/mysql_migration/verify_migration.py
```

## MySQL Configuration

### Database Setup
```sql
CREATE DATABASE vedfolnir CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'vedfolnir_user'@'localhost' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON vedfolnir.* TO 'vedfolnir_user'@'localhost';
FLUSH PRIVILEGES;
```

### Connection Configuration
```bash
# Basic MySQL Configuration
DATABASE_URL=mysql+pymysql://vedfolnir_user:password@localhost/vedfolnir?charset=utf8mb4
DB_TYPE=mysql
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
```

## Database Schema

### Core Tables
- **users**: User accounts with roles and authentication
- **platform_connections**: Encrypted platform credentials and settings
- **posts**: ActivityPub posts from various platforms
- **images**: Image metadata and caption information
- **processing_runs**: Batch processing history and statistics
- **user_sessions**: Session management and audit trail

### Performance Features
- **Optimized Indexes**: MySQL-specific performance indexes
- **Connection Pooling**: SQLAlchemy connection pool with overflow
- **Query Optimization**: Optimized queries for MySQL engine
- **Batch Operations**: Efficient bulk operations

## Security and Compliance
- **Encryption at Rest**: Platform credentials encrypted with Fernet
- **GDPR Support**: Data export, anonymization, and deletion
- **Audit Trails**: Complete user action logging
- **Security Monitoring**: Real-time security event tracking
