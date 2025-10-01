#!/bin/bash
# Nginx management script for Docker Compose

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

case "${1:-help}" in
    start)
        echo "Starting Nginx service..."
        docker-compose up -d nginx
        ;;
    stop)
        echo "Stopping Nginx service..."
        docker-compose stop nginx
        ;;
    restart)
        echo "Restarting Nginx service..."
        docker-compose restart nginx
        ;;
    reload)
        echo "Reloading Nginx configuration..."
        docker-compose exec nginx nginx -s reload
        ;;
    test)
        echo "Testing Nginx configuration..."
        docker-compose exec nginx nginx -t
        ;;
    logs)
        echo "Showing Nginx logs..."
        docker-compose logs -f nginx
        ;;
    status)
        echo "Nginx service status:"
        docker-compose ps nginx
        echo ""
        echo "Nginx health check:"
        docker-compose exec nginx /scripts/nginx-health-check.sh || echo "Health check failed"
        ;;
    stats)
        echo "Nginx statistics:"
        curl -s http://localhost:8080/nginx_status || echo "Status endpoint not available"
        ;;
    ssl-info)
        echo "SSL certificate information:"
        openssl x509 -in ssl/certs/vedfolnir.crt -text -noout | grep -E "(Subject:|DNS:|IP Address:|Not Before|Not After)" || echo "Certificate not found"
        ;;
    help|*)
        echo "Nginx management script"
        echo ""
        echo "Usage: $0 {start|stop|restart|reload|test|logs|status|stats|ssl-info|help}"
        echo ""
        echo "Commands:"
        echo "  start     - Start Nginx service"
        echo "  stop      - Stop Nginx service"
        echo "  restart   - Restart Nginx service"
        echo "  reload    - Reload Nginx configuration"
        echo "  test      - Test Nginx configuration"
        echo "  logs      - Show Nginx logs"
        echo "  status    - Show Nginx service status"
        echo "  stats     - Show Nginx statistics"
        echo "  ssl-info  - Show SSL certificate information"
        echo "  help      - Show this help message"
        ;;
esac
