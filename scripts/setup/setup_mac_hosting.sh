#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Vedfolnir Mac Hosting Setup Script
# Complete setup for hosting Vedfolnir on macOS with Gunicorn

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_VERSION="3.12.5"
VENV_NAME="gunicorn-host"
SERVICE_NAME="com.vedfolnir.gunicorn"

echo -e "${BLUE}=== Vedfolnir Mac Hosting Setup ===${NC}"
echo "Project directory: $PROJECT_DIR"
echo

# Function to print status
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    print_error "This script is designed for macOS only"
    exit 1
fi

print_status "Running on macOS"

# Step 1: Install Homebrew if not present
echo -e "\n${BLUE}=== Step 1: Homebrew Setup ===${NC}"
if ! command -v brew &> /dev/null; then
    print_info "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to PATH for M1/M2 Macs
    if [[ $(uname -m) == "arm64" ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
else
    print_status "Homebrew already installed"
fi

# Update Homebrew
brew update

# Step 2: Install required system dependencies
echo -e "\n${BLUE}=== Step 2: System Dependencies ===${NC}"

# Install Python build dependencies
print_info "Installing Python build dependencies..."
brew install openssl readline sqlite3 xz zlib tcl-tk

# Install pyenv for Python version management
if ! command -v pyenv &> /dev/null; then
    print_info "Installing pyenv..."
    brew install pyenv pyenv-virtualenv
    
    # Add pyenv to shell configuration
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
    echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
    echo 'eval "$(pyenv init -)"' >> ~/.zshrc
    echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.zshrc
    
    # Initialize pyenv for current session
    export PYENV_ROOT="$HOME/.pyenv"
    export PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init -)"
    eval "$(pyenv virtualenv-init -)"
else
    print_status "pyenv already installed"
fi

# Install MySQL
if ! brew services list | grep mysql | grep -q started; then
    print_info "Installing and starting MySQL..."
    brew install mysql
    brew services start mysql
    
    print_warning "MySQL installed. You may need to run mysql_secure_installation"
else
    print_status "MySQL already running"
fi

# Install Redis
if ! brew services list | grep redis | grep -q started; then
    print_info "Installing and starting Redis..."
    brew install redis
    brew services start redis
else
    print_status "Redis already running"
fi

# Install Nginx
if ! brew services list | grep nginx | grep -q started; then
    print_info "Installing Nginx..."
    brew install nginx
    
    # Create servers directory
    mkdir -p /opt/homebrew/etc/nginx/servers
    
    print_info "Nginx installed but not started (will configure later)"
else
    print_status "Nginx already installed"
fi

# Step 3: Python Environment Setup
echo -e "\n${BLUE}=== Step 3: Python Environment ===${NC}"

# Install Python version if not present
if ! pyenv versions | grep -q "$PYTHON_VERSION"; then
    print_info "Installing Python $PYTHON_VERSION..."
    pyenv install "$PYTHON_VERSION"
else
    print_status "Python $PYTHON_VERSION already installed"
fi

# Create virtual environment if not present
if ! pyenv versions | grep -q "$VENV_NAME"; then
    print_info "Creating virtual environment '$VENV_NAME'..."
    pyenv virtualenv "$PYTHON_VERSION" "$VENV_NAME"
else
    print_status "Virtual environment '$VENV_NAME' already exists"
fi

# Activate virtual environment
print_info "Activating virtual environment..."
pyenv activate "$VENV_NAME"

# Step 4: Install Python Dependencies
echo -e "\n${BLUE}=== Step 4: Python Dependencies ===${NC}"

cd "$PROJECT_DIR"

# Upgrade pip
print_info "Upgrading pip..."
pip install --upgrade pip

# Install requirements
if [[ -f "requirements.txt" ]]; then
    print_info "Installing Python requirements..."
    pip install -r requirements.txt
else
    print_error "requirements.txt not found in $PROJECT_DIR"
    exit 1
fi

# Install additional production dependencies
print_info "Installing production dependencies..."
pip install gunicorn eventlet

# Step 5: Database Setup
echo -e "\n${BLUE}=== Step 5: Database Setup ===${NC}"

# Check if .env file exists
if [[ ! -f ".env" ]]; then
    print_info "Generating environment configuration..."
    python scripts/setup/generate_env_secrets.py
else
    print_status ".env file already exists"
fi

# Initialize database
print_info "Setting up database..."
python scripts/setup/mysql_init_and_migrate.py

# Create admin user if needed
print_info "Setting up admin user..."
python scripts/setup/setup_admin_user.py

# Step 6: Create Directories
echo -e "\n${BLUE}=== Step 6: Directory Setup ===${NC}"

# Create required directories
mkdir -p logs
mkdir -p storage/images
mkdir -p storage/temp
mkdir -p storage/backups

print_status "Required directories created"

# Step 7: Configure Gunicorn Service
echo -e "\n${BLUE}=== Step 7: Gunicorn Service Configuration ===${NC}"

# Update start_gunicorn.sh with correct paths
print_info "Updating Gunicorn startup script..."
cat > start_gunicorn.sh << EOF
#!/bin/bash

# Exit on any error
set -e

# Navigate to the project directory
cd "$PROJECT_DIR"

# Set up environment variables for Mac
export PATH="/opt/homebrew/bin:\$PATH"

# Initialize pyenv
if command -v pyenv 1>/dev/null 2>&1; then
  eval "\$(pyenv init --path)"
  eval "\$(pyenv init -)"
fi

# Activate the virtual environment
pyenv activate $VENV_NAME

# Create logs directory if it doesn't exist
mkdir -p logs

# Install/update requirements if requirements.txt exists
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi

# Start Gunicorn with RQ worker integration
exec gunicorn --bind 127.0.0.1:8000 \\
    --workers 4 \\
    --worker-class eventlet \\
    --timeout 120 \\
    --keep-alive 2 \\
    --max-requests 1000 \\
    --max-requests-jitter 50 \\
    --preload \\
    --access-logfile logs/access.log \\
    --error-logfile logs/error.log \\
    --log-level info \\
    web_app:app
EOF

chmod +x start_gunicorn.sh

# Update plist file with correct paths
print_info "Creating launchd service configuration..."
cat > com.vedfolnir.gunicorn.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Label</key>
	<string>com.vedfolnir.gunicorn</string>
	<key>ProgramArguments</key>
	<array>
		<string>$PROJECT_DIR/start_gunicorn.sh</string>
	</array>
	<key>KeepAlive</key>
	<true/>
	<key>RunAtLoad</key>
	<true/>
	<key>WorkingDirectory</key>
	<string>$PROJECT_DIR</string>
	<key>StandardOutPath</key>
	<string>$PROJECT_DIR/logs/vedfolnir.log</string>
	<key>StandardErrorPath</key>
	<string>$PROJECT_DIR/logs/vedfolnir.err</string>
	<key>EnvironmentVariables</key>
	<dict>
		<key>PATH</key>
		<string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
	</dict>
</dict>
</plist>
EOF

print_status "Gunicorn service configuration created"

# Step 8: Install and Start Services
echo -e "\n${BLUE}=== Step 8: Service Installation ===${NC}"

# Install launchd service
print_info "Installing Gunicorn service..."
cp com.vedfolnir.gunicorn.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.vedfolnir.gunicorn.plist

# Start the service
print_info "Starting Gunicorn service..."
launchctl start com.vedfolnir.gunicorn

# Wait for startup
sleep 5

# Test the service
if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000 | grep -q "200\|302"; then
    print_status "Gunicorn service is running successfully"
else
    print_warning "Gunicorn service may not be responding yet"
    print_info "Check logs: tail -f logs/vedfolnir.log"
fi

# Step 9: Nginx Configuration (Optional)
echo -e "\n${BLUE}=== Step 9: Nginx Configuration (Optional) ===${NC}"

read -p "Do you want to configure Nginx as a reverse proxy? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Creating Nginx configuration..."
    
    # Create basic Nginx config
    cat > /opt/homebrew/etc/nginx/servers/vedfolnir.conf << EOF
server {
    listen 80;
    server_name localhost;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

    # Start Nginx
    print_info "Starting Nginx..."
    sudo brew services start nginx
    
    print_status "Nginx configured and started"
    print_info "Application available at: http://localhost"
else
    print_info "Skipping Nginx configuration"
    print_info "Application available at: http://127.0.0.1:8000"
fi

# Step 10: Final Setup and Testing
echo -e "\n${BLUE}=== Step 10: Final Setup ===${NC}"

# Create management scripts
print_info "Creating management scripts..."

# Service management script
cat > scripts/manage_services.sh << 'EOF'
#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Vedfolnir Service Management Script

case "$1" in
    start)
        echo "Starting Vedfolnir services..."
        launchctl start com.vedfolnir.gunicorn
        brew services start mysql
        brew services start redis
        if brew services list | grep nginx | grep -q started; then
            echo "Nginx already running"
        fi
        ;;
    stop)
        echo "Stopping Vedfolnir services..."
        launchctl stop com.vedfolnir.gunicorn
        ;;
    restart)
        echo "Restarting Vedfolnir services..."
        launchctl stop com.vedfolnir.gunicorn
        sleep 3
        launchctl start com.vedfolnir.gunicorn
        ;;
    status)
        echo "=== Service Status ==="
        echo -n "Gunicorn: "
        if launchctl list | grep -q com.vedfolnir.gunicorn; then
            echo "Running"
        else
            echo "Stopped"
        fi
        
        echo -n "MySQL: "
        if brew services list | grep mysql | grep -q started; then
            echo "Running"
        else
            echo "Stopped"
        fi
        
        echo -n "Redis: "
        if brew services list | grep redis | grep -q started; then
            echo "Running"
        else
            echo "Stopped"
        fi
        
        echo -n "Nginx: "
        if brew services list | grep nginx | grep -q started; then
            echo "Running"
        else
            echo "Stopped"
        fi
        ;;
    logs)
        echo "=== Recent Logs ==="
        tail -n 20 logs/vedfolnir.log
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
EOF

chmod +x scripts/manage_services.sh

print_status "Management scripts created"

# Final status check
echo -e "\n${GREEN}=== Setup Complete! ===${NC}"
echo
echo "🎉 Vedfolnir has been successfully set up on your Mac!"
echo
echo "📋 Summary:"
echo "  • Python $PYTHON_VERSION with virtual environment '$VENV_NAME'"
echo "  • MySQL database configured and running"
echo "  • Redis session storage running"
echo "  • Gunicorn application server running on port 8000"
if brew services list | grep nginx | grep -q started; then
    echo "  • Nginx reverse proxy running on port 80"
fi
echo
echo "🔗 Access your application:"
if brew services list | grep nginx | grep -q started; then
    echo "  • Web interface: http://localhost"
fi
echo "  • Direct access: http://127.0.0.1:8000"
echo
echo "🛠️  Management commands:"
echo "  • Start services:   ./scripts/manage_services.sh start"
echo "  • Stop services:    ./scripts/manage_services.sh stop"
echo "  • Restart services: ./scripts/manage_services.sh restart"
echo "  • Check status:     ./scripts/manage_services.sh status"
echo "  • View logs:        ./scripts/manage_services.sh logs"
echo
echo "📁 Important files:"
echo "  • Configuration: .env"
echo "  • Logs: logs/"
echo "  • Service config: ~/Library/LaunchAgents/com.vedfolnir.gunicorn.plist"
echo
echo "🔧 Next steps:"
echo "  1. Configure your platform connections in the web interface"
echo "  2. Test caption generation functionality"
echo "  3. Set up SSL certificates if needed (for production)"
echo
print_status "Setup completed successfully!"