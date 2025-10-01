#!/bin/bash
# Nginx health check script for Docker

# Test Nginx configuration
nginx -t >/dev/null 2>&1 || exit 1

# Test HTTP response
curl -f -s http://localhost:8080/health >/dev/null 2>&1 || exit 1

# Test if Nginx is serving requests
curl -f -s -I http://localhost >/dev/null 2>&1 || exit 1

echo "Nginx is healthy"
exit 0
