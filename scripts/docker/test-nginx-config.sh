#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Test Nginx configuration using Python unittest

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "Testing Nginx configuration..."

# Run the specific test or all configuration tests
case "${1:-all}" in
    syntax)
        echo "Running configuration syntax test..."
        python3 -m unittest tests.integration.test_nginx_config_simple.TestNginxConfiguration.test_nginx_configuration_syntax -v
        ;;
    config)
        echo "Running all configuration tests..."
        python3 -m unittest tests.integration.test_nginx_config_simple.TestNginxConfiguration -v
        ;;
    connectivity)
        echo "Running connectivity tests..."
        python3 -m unittest tests.integration.test_nginx_config_simple.TestNginxConnectivity -v
        ;;
    performance)
        echo "Running performance tests..."
        python3 -m unittest tests.integration.test_nginx_config_simple.TestNginxPerformanceSimple -v
        ;;
    all|*)
        echo "Running all Nginx tests..."
        python3 -m unittest tests.integration.test_nginx_config_simple -v
        ;;
esac

echo ""
echo "✅ Nginx configuration tests completed!"