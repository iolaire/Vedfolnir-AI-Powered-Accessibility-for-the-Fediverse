#!/bin/bash
# Initialize Vedfolnir application for development with MySQL database

set -e

echo "🔧 Initializing Vedfolnir development environment with MySQL..."

# Development-specific initialization
echo "📋 Setting up development database..."

# Initialize development database
python3 -c "
from database import init_db
try:
    init_db()
    print('✅ Development database initialized')
except Exception as e:
    print(f'⚠️ Database initialization: {e}')
"

# Create test database if it doesn't exist
echo "🧪 Setting up test database..."
mysql -h"${DB_HOST}" -u"${DB_USER}" -p"${DB_PASSWORD}" -e "
CREATE DATABASE IF NOT EXISTS vedfolnir_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
" 2>/dev/null || echo "⚠️ Test database setup failed"

# Create admin user for development
echo "👤 Creating development admin user..."
python3 scripts/setup/init_admin_user.py || echo "⚠️ Admin user already exists or creation failed"

# Install development dependencies if requirements-dev.txt exists
if [ -f "requirements-dev.txt" ]; then
    echo "📦 Installing development dependencies..."
    pip install -r requirements-dev.txt || echo "⚠️ Development dependencies installation failed"
fi

# Run tests to validate setup
echo "🧪 Running basic validation tests..."
python3 -c "
import sys
sys.path.append('/app')

try:
    # Test imports
    from database import get_db_connection
    from config import Config
    from web_app import app
    
    # Test database connection
    conn = get_db_connection()
    conn.close()
    print('✅ Database connection test passed')
    
    # Test Flask app
    with app.app_context():
        print('✅ Flask application test passed')
        
except Exception as e:
    print(f'⚠️ Validation test failed: {e}')
"

echo "✅ Development environment initialization completed"
echo "🌐 Starting development web application with debugging..."

# Start with debugger if FLASK_DEBUG is true
if [ "$FLASK_DEBUG" = "true" ]; then
    echo "🐛 Starting with debugger on port 5678..."
    exec python3 -m debugpy --listen 0.0.0.0:5678 --wait-for-client web_app.py
else
    exec python3 web_app.py
fi
