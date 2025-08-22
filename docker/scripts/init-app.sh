#!/bin/bash
# Initialize Vedfolnir application with MySQL database
# This script replaces any SQLite-based initialization

set -e

echo "🔧 Initializing Vedfolnir application with MySQL..."

# Check if database needs initialization
echo "📋 Checking database state..."

# Count existing tables
table_count=$(mysql -h"${DB_HOST}" -P"${DB_PORT}" -u"${DB_USER}" -p"${DB_PASSWORD}" \
    -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='${DB_NAME}';" 2>/dev/null || echo "0")

if [ "$table_count" -eq "0" ]; then
    echo "📋 Database is empty, initializing schema..."
    
    # Initialize database schema
    python3 -c "
from database import init_db
try:
    init_db()
    print('✅ Database schema initialized successfully')
except Exception as e:
    print(f'❌ Database initialization failed: {e}')
    exit(1)
"
else
    echo "ℹ️ Database already contains $table_count tables"
fi

# Run any pending migrations
echo "🔄 Running database migrations..."
python3 -c "
from database import run_migrations
try:
    run_migrations()
    print('✅ Database migrations completed')
except Exception as e:
    print(f'⚠️ Migration warning: {e}')
"

# Create admin user if it doesn't exist
echo "👤 Checking admin user..."
python3 -c "
from database import get_db_connection
import pymysql

try:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users WHERE username = %s', ('admin',))
    admin_count = cursor.fetchone()[0]
    conn.close()
    
    if admin_count == 0:
        print('Creating admin user...')
        import subprocess
        result = subprocess.run(['python3', 'scripts/setup/init_admin_user.py'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print('✅ Admin user created successfully')
        else:
            print(f'⚠️ Admin user creation warning: {result.stderr}')
    else:
        print('ℹ️ Admin user already exists')
        
except Exception as e:
    print(f'⚠️ Admin user check failed: {e}')
"

# Validate application configuration
echo "🔍 Validating application configuration..."
python3 -c "
from config import Config
from database import get_db_connection

try:
    # Test configuration
    config = Config()
    print(f'✅ Configuration loaded: {config.database.database_url[:50]}...')
    
    # Test database connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT VERSION()')
    mysql_version = cursor.fetchone()[0]
    conn.close()
    print(f'✅ MySQL connection successful: {mysql_version}')
    
except Exception as e:
    print(f'❌ Configuration validation failed: {e}')
    exit(1)
"

# Clean up any old SQLite files (safety measure)
echo "🧹 Cleaning up old SQLite files..."
find /app -name "*.db" -type f -path "*/storage/*" -exec rm -f {} \; 2>/dev/null || true
find /app -name "*.db-wal" -type f -exec rm -f {} \; 2>/dev/null || true
find /app -name "*.db-shm" -type f -exec rm -f {} \; 2>/dev/null || true

echo "✅ Application initialization completed"
echo "🌐 Starting web application..."

# Start the web application
exec python3 web_app.py
