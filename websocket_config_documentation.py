# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Configuration Documentation Generator

This module generates comprehensive documentation for WebSocket configuration
options, including examples, troubleshooting guides, and deployment scenarios.
"""

import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from websocket_config_schema import WebSocketConfigSchema
from websocket_config_validator import WebSocketConfigValidator
from websocket_config_migration import WebSocketConfigMigration


class WebSocketConfigDocumentation:
    """
    WebSocket configuration documentation generator
    
    Generates comprehensive documentation including configuration reference,
    examples, troubleshooting guides, and deployment scenarios.
    """
    
    def __init__(self):
        """Initialize documentation generator"""
        self.schema = WebSocketConfigSchema()
        self.validator = WebSocketConfigValidator()
        self.migration = WebSocketConfigMigration()
    
    def generate_configuration_reference(self, output_format: str = "markdown") -> str:
        """
        Generate comprehensive configuration reference documentation
        
        Args:
            output_format: Output format ('markdown', 'html', 'json')
            
        Returns:
            Configuration reference documentation
        """
        if output_format == "markdown":
            return self._generate_markdown_reference()
        elif output_format == "html":
            return self._generate_html_reference()
        elif output_format == "json":
            return self._generate_json_reference()
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
    
    def _generate_markdown_reference(self) -> str:
        """Generate Markdown configuration reference"""
        lines = [
            "# WebSocket Configuration Reference",
            "",
            f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "This document provides a comprehensive reference for all WebSocket configuration options.",
            "",
            "## Table of Contents",
            ""
        ]
        
        # Generate table of contents
        categories = self.schema.get_categories()
        for category in sorted(categories):
            lines.append(f"- [{category.title()} Configuration](#{category.lower()}-configuration)")
        
        lines.extend([
            "- [Configuration Examples](#configuration-examples)",
            "- [Troubleshooting](#troubleshooting)",
            "- [Migration Guide](#migration-guide)",
            ""
        ])
        
        # Generate configuration sections by category
        for category in sorted(categories):
            lines.extend(self._generate_category_section_markdown(category))
        
        # Add examples section
        lines.extend(self._generate_examples_section_markdown())
        
        # Add troubleshooting section
        lines.extend(self._generate_troubleshooting_section_markdown())
        
        # Add migration guide section
        lines.extend(self._generate_migration_section_markdown())
        
        return "\n".join(lines)
    
    def _generate_category_section_markdown(self, category: str) -> List[str]:
        """Generate Markdown section for a configuration category"""
        lines = [
            f"## {category.title()} Configuration",
            ""
        ]
        
        category_fields = self.schema.get_fields_by_category(category)
        
        for field_name, field_schema in sorted(category_fields.items()):
            lines.extend([
                f"### {field_name}",
                "",
                f"**Description:** {field_schema.description}",
                "",
                f"**Type:** `{field_schema.data_type.value}`",
                f"**Default:** `{field_schema.default_value}`",
                f"**Required:** {'Yes' if field_schema.required else 'No'}",
                ""
            ])
            
            if field_schema.examples:
                lines.extend([
                    "**Examples:**",
                    ""
                ])
                for example in field_schema.examples:
                    lines.append(f"```bash")
                    lines.append(f"{field_name}={example}")
                    lines.append("```")
                    lines.append("")
            
            # Add validation rules
            validation_rules = self.schema.get_validation_rules(field_name)
            if validation_rules:
                lines.extend([
                    "**Validation Rules:**",
                    ""
                ])
                for rule in validation_rules:
                    lines.append(f"- **{rule.name}:** {rule.message} ({rule.level.value})")
                lines.append("")
            
            if field_schema.deprecated:
                lines.extend([
                    "⚠️ **DEPRECATED:** This field is deprecated.",
                    ""
                ])
                if field_schema.migration_note:
                    lines.extend([
                        f"**Migration Note:** {field_schema.migration_note}",
                        ""
                    ])
            
            lines.append("---")
            lines.append("")
        
        return lines
    
    def _generate_examples_section_markdown(self) -> List[str]:
        """Generate configuration examples section"""
        lines = [
            "## Configuration Examples",
            "",
            "This section provides complete configuration examples for different deployment scenarios.",
            ""
        ]
        
        examples = {
            "Development Environment": self._get_development_config_example(),
            "Production Environment": self._get_production_config_example(),
            "Multi-Instance Deployment": self._get_multi_instance_config_example(),
            "High Security Environment": self._get_high_security_config_example()
        }
        
        for example_name, config in examples.items():
            lines.extend([
                f"### {example_name}",
                "",
                "```bash"
            ])
            
            for key, value in sorted(config.items()):
                lines.append(f"{key}={value}")
            
            lines.extend([
                "```",
                ""
            ])
        
        return lines
    
    def _generate_troubleshooting_section_markdown(self) -> List[str]:
        """Generate troubleshooting section"""
        lines = [
            "## Troubleshooting",
            "",
            "This section covers common configuration issues and their solutions.",
            ""
        ]
        
        troubleshooting_items = [
            {
                "issue": "CORS Connection Failures",
                "symptoms": [
                    "WebSocket connections fail with CORS errors",
                    "Browser console shows 'Access-Control-Allow-Origin' errors"
                ],
                "solutions": [
                    "Check SOCKETIO_CORS_ORIGINS includes your client domain",
                    "Ensure FLASK_HOST and FLASK_PORT match your server configuration",
                    "Verify SOCKETIO_CORS_CREDENTIALS is set correctly"
                ]
            },
            {
                "issue": "Connection Timeouts",
                "symptoms": [
                    "WebSocket connections timeout frequently",
                    "Clients disconnect unexpectedly"
                ],
                "solutions": [
                    "Increase SOCKETIO_PING_TIMEOUT value",
                    "Adjust SOCKETIO_PING_INTERVAL for your network conditions",
                    "Check network infrastructure for connection stability"
                ]
            },
            {
                "issue": "Authentication Failures",
                "symptoms": [
                    "WebSocket connections rejected with auth errors",
                    "Users cannot connect despite valid sessions"
                ],
                "solutions": [
                    "Verify SOCKETIO_REQUIRE_AUTH is configured correctly",
                    "Check SOCKETIO_SESSION_VALIDATION setting",
                    "Ensure session backend is properly configured"
                ]
            },
            {
                "issue": "Performance Issues",
                "symptoms": [
                    "Slow WebSocket connection establishment",
                    "High server resource usage"
                ],
                "solutions": [
                    "Optimize SOCKETIO_MAX_CONNECTIONS for your server capacity",
                    "Adjust SOCKETIO_CONNECTION_POOL_SIZE",
                    "Consider using Redis for session storage in multi-instance deployments"
                ]
            }
        ]
        
        for item in troubleshooting_items:
            lines.extend([
                f"### {item['issue']}",
                "",
                "**Symptoms:**",
                ""
            ])
            
            for symptom in item['symptoms']:
                lines.append(f"- {symptom}")
            
            lines.extend([
                "",
                "**Solutions:**",
                ""
            ])
            
            for solution in item['solutions']:
                lines.append(f"- {solution}")
            
            lines.extend([
                "",
                "---",
                ""
            ])
        
        return lines
    
    def _generate_migration_section_markdown(self) -> List[str]:
        """Generate migration guide section"""
        lines = [
            "## Migration Guide",
            "",
            "This section covers migration between different configuration versions and deployment scenarios.",
            ""
        ]
        
        migration_plans = self.migration.get_available_migrations()
        
        for plan_name in migration_plans:
            plan = self.migration.get_migration_plan(plan_name)
            if plan:
                lines.extend([
                    f"### {plan.description}",
                    "",
                    f"**Migration:** {plan.version_from} → {plan.version_to}",
                    "",
                    "**Steps:**",
                    ""
                ])
                
                for i, step in enumerate(plan.steps, 1):
                    lines.append(f"{i}. **{step.name}:** {step.description}")
                
                lines.extend([
                    "",
                    f"**Backup Required:** {'Yes' if plan.backup_required else 'No'}",
                    f"**Rollback Supported:** {'Yes' if plan.rollback_supported else 'No'}",
                    "",
                    "**Usage:**",
                    "",
                    "```python",
                    "from websocket_config_migration import WebSocketConfigMigration",
                    "",
                    "migration = WebSocketConfigMigration()",
                    f"result = migration.execute_migration('{plan_name}', '.env')",
                    "```",
                    "",
                    "---",
                    ""
                ])
        
        return lines
    
    def _get_development_config_example(self) -> Dict[str, str]:
        """Get development environment configuration example"""
        return {
            "FLASK_ENV": "development",
            "FLASK_HOST": "127.0.0.1",
            "FLASK_PORT": "5000",
            "SOCKETIO_CORS_ORIGINS": "http://localhost:3000,http://127.0.0.1:5000",
            "SOCKETIO_TRANSPORTS": "websocket,polling",
            "SOCKETIO_DEBUG": "true",
            "SOCKETIO_LOG_LEVEL": "DEBUG",
            "SOCKETIO_LOG_CONNECTIONS": "true",
            "SOCKETIO_REQUIRE_AUTH": "false",
            "SOCKETIO_CSRF_PROTECTION": "false"
        }
    
    def _get_production_config_example(self) -> Dict[str, str]:
        """Get production environment configuration example"""
        return {
            "FLASK_ENV": "production",
            "FLASK_HOST": "0.0.0.0",
            "FLASK_PORT": "443",
            "SOCKETIO_CORS_ORIGINS": "https://yourdomain.com,https://www.yourdomain.com",
            "SOCKETIO_CORS_CREDENTIALS": "true",
            "SOCKETIO_TRANSPORTS": "websocket,polling",
            "SOCKETIO_PING_TIMEOUT": "120",
            "SOCKETIO_PING_INTERVAL": "30",
            "SOCKETIO_MAX_CONNECTIONS": "5000",
            "SOCKETIO_REQUIRE_AUTH": "true",
            "SOCKETIO_SESSION_VALIDATION": "true",
            "SOCKETIO_RATE_LIMITING": "true",
            "SOCKETIO_CSRF_PROTECTION": "true",
            "SOCKETIO_LOG_LEVEL": "WARNING",
            "SOCKETIO_DEBUG": "false"
        }
    
    def _get_multi_instance_config_example(self) -> Dict[str, str]:
        """Get multi-instance deployment configuration example"""
        return {
            "FLASK_ENV": "production",
            "REDIS_URL": "redis://redis-server:6379/0",
            "SESSION_STORAGE": "redis",
            "SOCKETIO_ASYNC_MODE": "eventlet",
            "SOCKETIO_TRANSPORTS": "polling,websocket",
            "SOCKETIO_MAX_CONNECTIONS": "10000",
            "SOCKETIO_CONNECTION_POOL_SIZE": "20",
            "SOCKETIO_PING_TIMEOUT": "60",
            "SOCKETIO_PING_INTERVAL": "25",
            "HEALTH_CHECK_ENABLED": "true",
            "WEBSOCKET_HEALTH_CHECK_ENABLED": "true"
        }
    
    def _get_high_security_config_example(self) -> Dict[str, str]:
        """Get high security environment configuration example"""
        return {
            "SOCKETIO_CORS_ORIGINS": "https://secure.yourdomain.com",
            "SOCKETIO_CORS_CREDENTIALS": "true",
            "SOCKETIO_REQUIRE_AUTH": "true",
            "SOCKETIO_SESSION_VALIDATION": "true",
            "SOCKETIO_RATE_LIMITING": "true",
            "SOCKETIO_CSRF_PROTECTION": "true",
            "SOCKETIO_MAX_CONNECTIONS": "1000",
            "SOCKETIO_PING_TIMEOUT": "30",
            "SOCKETIO_PING_INTERVAL": "10",
            "SOCKETIO_LOG_LEVEL": "INFO",
            "SOCKETIO_LOG_CONNECTIONS": "true"
        }
    
    def generate_deployment_guide(self, deployment_type: str) -> str:
        """
        Generate deployment-specific configuration guide
        
        Args:
            deployment_type: Type of deployment ('docker', 'kubernetes', 'systemd', 'nginx')
            
        Returns:
            Deployment guide documentation
        """
        if deployment_type == "docker":
            return self._generate_docker_guide()
        elif deployment_type == "kubernetes":
            return self._generate_kubernetes_guide()
        elif deployment_type == "systemd":
            return self._generate_systemd_guide()
        elif deployment_type == "nginx":
            return self._generate_nginx_guide()
        else:
            raise ValueError(f"Unsupported deployment type: {deployment_type}")
    
    def _generate_docker_guide(self) -> str:
        """Generate Docker deployment guide"""
        return """# WebSocket Configuration for Docker Deployment

## Environment Variables

Create a `.env` file with your WebSocket configuration:

```bash
# Basic Configuration
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
SOCKETIO_CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# Redis Configuration (for multi-container setup)
REDIS_URL=redis://redis:6379/0
SESSION_STORAGE=redis

# Security Configuration
SOCKETIO_REQUIRE_AUTH=true
SOCKETIO_CSRF_PROTECTION=true
```

## docker-compose Example

```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "5000:5000"
    env_file:
      - .env
    depends_on:
      - redis
    
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
```

## Health Checks

Add health check configuration:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:5000/health || exit 1
```
"""
    
    def _generate_kubernetes_guide(self) -> str:
        """Generate Kubernetes deployment guide"""
        return """# WebSocket Configuration for Kubernetes Deployment

## ConfigMap

Create a ConfigMap for WebSocket configuration:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: websocket-config
data:
  FLASK_HOST: "0.0.0.0"
  FLASK_PORT: "5000"
  SOCKETIO_TRANSPORTS: "polling,websocket"
  SOCKETIO_MAX_CONNECTIONS: "10000"
  SOCKETIO_REQUIRE_AUTH: "true"
  HEALTH_CHECK_ENABLED: "true"
```

## Secret

Create a Secret for sensitive configuration:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: websocket-secrets
type: Opaque
data:
  REDIS_URL: <base64-encoded-redis-url>
  FLASK_SECRET_KEY: <base64-encoded-secret-key>
```

## Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: websocket-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: websocket-app
  template:
    metadata:
      labels:
        app: websocket-app
    spec:
      containers:
      - name: websocket-app
        image: your-app:latest
        ports:
        - containerPort: 5000
        envFrom:
        - configMapRef:
            name: websocket-config
        - secretRef:
            name: websocket-secrets
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 10
```

## Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: websocket-service
spec:
  selector:
    app: websocket-app
  ports:
  - port: 80
    targetPort: 5000
  type: LoadBalancer
  sessionAffinity: ClientIP
```
"""
    
    def save_documentation(self, content: str, filename: str, output_dir: str = "docs") -> str:
        """
        Save documentation to file
        
        Args:
            content: Documentation content
            filename: Output filename
            output_dir: Output directory
            
        Returns:
            Path to saved file
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        file_path = output_path / filename
        with open(file_path, 'w') as f:
            f.write(content)
        
        return str(file_path)
    
    def generate_all_documentation(self, output_dir: str = "docs") -> Dict[str, str]:
        """
        Generate all documentation files
        
        Args:
            output_dir: Output directory for documentation
            
        Returns:
            Dictionary mapping document names to file paths
        """
        generated_files = {}
        
        # Configuration reference
        config_ref = self.generate_configuration_reference("markdown")
        generated_files["configuration_reference"] = self.save_documentation(
            config_ref, "websocket_configuration_reference.md", output_dir
        )
        
        # Configuration template
        config_template = self.validator.generate_configuration_template(include_optional=True)
        generated_files["configuration_template"] = self.save_documentation(
            config_template, "websocket_configuration_template.env", output_dir
        )
        
        # Deployment guides
        deployment_types = ["docker", "kubernetes", "systemd", "nginx"]
        for deployment_type in deployment_types:
            try:
                guide = self.generate_deployment_guide(deployment_type)
                filename = f"websocket_deployment_{deployment_type}.md"
                generated_files[f"deployment_{deployment_type}"] = self.save_documentation(
                    guide, filename, output_dir
                )
            except ValueError:
                # Skip unsupported deployment types
                pass
        
        return generated_files