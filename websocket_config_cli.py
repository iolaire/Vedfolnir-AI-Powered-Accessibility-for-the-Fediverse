#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Configuration CLI Tool

Command-line interface for WebSocket configuration management, validation,
migration, and health checking.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from websocket_config_validator import WebSocketConfigValidator
from websocket_config_migration import WebSocketConfigMigration
from websocket_config_documentation import WebSocketConfigDocumentation
from websocket_config_health_checker import WebSocketConfigHealthChecker


def setup_logging(level: str = "INFO") -> None:
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def validate_command(args) -> int:
    """Handle validate command"""
    validator = WebSocketConfigValidator()
    
    # Load environment variables from file if specified
    env_vars = None
    if args.env_file:
        if not os.path.exists(args.env_file):
            print(f"❌ Environment file not found: {args.env_file}")
            return 1
        
        env_vars = {}
        with open(args.env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip().strip('"\'')
    
    # Perform validation
    report = validator.validate_configuration(env_vars)
    
    # Display results
    print("🔍 WebSocket Configuration Validation Report")
    print("=" * 50)
    print(f"Timestamp: {report.timestamp}")
    print(f"Health Score: {report.health_score:.1f}%")
    print(f"Status: {'✅ Valid' if report.is_valid else '❌ Invalid'}")
    print()
    
    # Summary
    print("📊 Summary:")
    print(f"  Total Fields: {report.total_fields}")
    print(f"  Validated Fields: {report.validated_fields}")
    print(f"  Errors: {len(report.errors)}")
    print(f"  Warnings: {len(report.warnings)}")
    print(f"  Missing Required: {len(report.missing_required)}")
    print(f"  Deprecated Used: {len(report.deprecated_used)}")
    print()
    
    # Errors
    if report.errors:
        print("❌ Errors:")
        for error in report.errors:
            print(f"  • {error.field_name}: {error.message}")
            if error.suggested_value:
                print(f"    Suggested: {error.suggested_value}")
        print()
    
    # Warnings
    if report.warnings:
        print("⚠️  Warnings:")
        for warning in report.warnings:
            print(f"  • {warning.field_name}: {warning.message}")
        print()
    
    # Missing required fields
    if report.missing_required:
        print("🚫 Missing Required Fields:")
        for field in report.missing_required:
            print(f"  • {field}")
        print()
    
    # Deprecated fields
    if report.deprecated_used:
        print("⚠️  Deprecated Fields in Use:")
        for field in report.deprecated_used:
            print(f"  • {field}")
        print()
    
    # Configuration summary
    if args.verbose and report.configuration_summary:
        print("📋 Configuration Summary:")
        for category, info in report.configuration_summary.get("categories", {}).items():
            print(f"  {category}: {info['configured_fields']}/{info['total_fields']} fields ({info['configuration_percentage']:.1f}%)")
        print()
    
    # Output to file if requested
    if args.output:
        output_data = {
            "timestamp": report.timestamp.isoformat(),
            "health_score": report.health_score,
            "is_valid": report.is_valid,
            "summary": {
                "total_fields": report.total_fields,
                "validated_fields": report.validated_fields,
                "errors": len(report.errors),
                "warnings": len(report.warnings),
                "missing_required": len(report.missing_required),
                "deprecated_used": len(report.deprecated_used)
            },
            "errors": [
                {
                    "field": error.field_name,
                    "rule": error.rule_name,
                    "message": error.message,
                    "current_value": error.current_value,
                    "suggested_value": error.suggested_value
                }
                for error in report.errors
            ],
            "warnings": [
                {
                    "field": warning.field_name,
                    "rule": warning.rule_name,
                    "message": warning.message,
                    "current_value": warning.current_value
                }
                for warning in report.warnings
            ],
            "missing_required": report.missing_required,
            "deprecated_used": report.deprecated_used,
            "configuration_summary": report.configuration_summary
        }
        
        with open(args.output, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"📄 Validation report saved to: {args.output}")
    
    return 0 if report.is_valid else 1


def migrate_command(args) -> int:
    """Handle migrate command"""
    migration = WebSocketConfigMigration()
    
    # Check if migration plan exists
    if args.plan not in migration.get_available_migrations():
        print(f"❌ Migration plan '{args.plan}' not found")
        print("Available migrations:")
        for plan_name in migration.get_available_migrations():
            plan = migration.get_migration_plan(plan_name)
            print(f"  • {plan_name}: {plan.description}")
        return 1
    
    # Check if environment file exists
    if not os.path.exists(args.env_file):
        print(f"❌ Environment file not found: {args.env_file}")
        return 1
    
    # Analyze configuration first
    if args.analyze:
        print("🔍 Analyzing configuration for migration...")
        analysis = migration.analyze_configuration_for_migration(args.env_file)
        
        print("📊 Analysis Results:")
        print(f"  Health Score: {analysis['validation_report']['health_score']:.1f}%")
        print(f"  Errors: {analysis['validation_report']['errors']}")
        print(f"  Warnings: {analysis['validation_report']['warnings']}")
        print()
        
        if analysis['recommended_migrations']:
            print("💡 Recommended Migrations:")
            for rec_migration in analysis['recommended_migrations']:
                print(f"  • {rec_migration}")
        else:
            print("✅ No migrations recommended")
        
        if analysis['compatibility_issues']:
            print("⚠️  Compatibility Issues:")
            for issue in analysis['compatibility_issues']:
                print(f"  • {issue}")
        
        print()
    
    # Execute migration
    print(f"🚀 Executing migration: {args.plan}")
    
    result = migration.execute_migration(
        args.plan,
        args.env_file,
        backup_dir=args.backup_dir,
        dry_run=args.dry_run
    )
    
    # Display results
    if result.success:
        print("✅ Migration completed successfully!")
        if args.dry_run:
            print("   (Dry run - no changes made)")
    else:
        print("❌ Migration failed!")
    
    print(f"Steps completed: {result.steps_completed}")
    print(f"Steps failed: {result.steps_failed}")
    
    if result.backup_path:
        print(f"Backup created: {result.backup_path}")
    
    if result.errors:
        print("\n❌ Errors:")
        for error in result.errors:
            print(f"  • {error}")
    
    if result.warnings:
        print("\n⚠️  Warnings:")
        for warning in result.warnings:
            print(f"  • {warning}")
    
    if result.migrated_fields:
        print(f"\n📝 Migrated {len(result.migrated_fields)} fields:")
        for field, value in result.migrated_fields.items():
            print(f"  • {field} = {value}")
    
    return 0 if result.success else 1


def health_command(args) -> int:
    """Handle health command"""
    health_checker = WebSocketConfigHealthChecker()
    
    if args.monitor:
        print("🔄 Starting health monitoring...")
        print(f"Check interval: {args.interval} seconds")
        print("Press Ctrl+C to stop")
        
        def health_callback(result):
            print(f"[{result.timestamp.strftime('%H:%M:%S')}] Health: {result.overall_status.value.upper()}")
            if result.has_critical_issues:
                print("  ⚠️  Critical issues detected!")
            elif result.has_warnings:
                print("  ⚠️  Warnings detected")
        
        health_checker.add_health_callback(health_callback)
        health_checker.check_interval = args.interval
        
        try:
            health_checker.start_monitoring()
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping health monitoring...")
            health_checker.stop_monitoring()
            return 0
    
    else:
        # Single health check
        print("🏥 Performing health check...")
        result = health_checker.perform_health_check()
        
        # Display results
        print("=" * 50)
        print(f"Timestamp: {result.timestamp}")
        print(f"Overall Status: {result.overall_status.value.upper()}")
        print(f"Total Metrics: {len(result.metrics)}")
        print()
        
        # Configuration health
        if result.configuration_health:
            print("📋 Configuration Health:")
            print(f"  Health Score: {result.configuration_health.health_score:.1f}%")
            print(f"  Errors: {len(result.configuration_health.errors)}")
            print(f"  Warnings: {len(result.configuration_health.warnings)}")
            print()
        
        # Metrics
        if result.metrics:
            print("📊 Health Metrics:")
            for metric in result.metrics:
                status_icon = {
                    "healthy": "✅",
                    "warning": "⚠️",
                    "critical": "❌",
                    "unknown": "❓"
                }.get(metric.status.value, "❓")
                
                print(f"  {status_icon} {metric.name}: {metric.message}")
            print()
        
        # Performance metrics
        if result.performance_metrics:
            print("⚡ Performance Metrics:")
            for key, value in result.performance_metrics.items():
                if isinstance(value, float):
                    print(f"  • {key}: {value:.3f}s")
                else:
                    print(f"  • {key}: {value}")
            print()
        
        # Recommendations
        if result.recommendations:
            print("💡 Recommendations:")
            for rec in result.recommendations:
                print(f"  • {rec}")
            print()
        
        # Output to file if requested
        if args.output:
            output_data = {
                "timestamp": result.timestamp.isoformat(),
                "overall_status": result.overall_status.value,
                "metrics": [
                    {
                        "name": metric.name,
                        "value": metric.value,
                        "status": metric.status.value,
                        "message": metric.message,
                        "timestamp": metric.timestamp.isoformat()
                    }
                    for metric in result.metrics
                ],
                "performance_metrics": result.performance_metrics,
                "recommendations": result.recommendations,
                "configuration_health": {
                    "health_score": result.configuration_health.health_score,
                    "errors": len(result.configuration_health.errors),
                    "warnings": len(result.configuration_health.warnings),
                    "is_valid": result.configuration_health.is_valid
                } if result.configuration_health else None
            }
            
            with open(args.output, 'w') as f:
                json.dump(output_data, f, indent=2)
            
            print(f"📄 Health report saved to: {args.output}")
        
        return 0 if result.is_healthy else 1


def docs_command(args) -> int:
    """Handle docs command"""
    docs = WebSocketConfigDocumentation()
    
    if args.type == "reference":
        print("📚 Generating configuration reference...")
        content = docs.generate_configuration_reference(args.format)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(content)
            print(f"📄 Reference saved to: {args.output}")
        else:
            print(content)
    
    elif args.type == "template":
        print("📝 Generating configuration template...")
        content = docs.validator.generate_configuration_template(include_optional=True)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(content)
            print(f"📄 Template saved to: {args.output}")
        else:
            print(content)
    
    elif args.type == "deployment":
        if not args.deployment_type:
            print("❌ Deployment type required for deployment guide")
            return 1
        
        print(f"🚀 Generating {args.deployment_type} deployment guide...")
        try:
            content = docs.generate_deployment_guide(args.deployment_type)
            
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(content)
                print(f"📄 Deployment guide saved to: {args.output}")
            else:
                print(content)
        except ValueError as e:
            print(f"❌ {e}")
            return 1
    
    elif args.type == "all":
        print("📚 Generating all documentation...")
        output_dir = args.output or "docs"
        generated_files = docs.generate_all_documentation(output_dir)
        
        print(f"📄 Generated {len(generated_files)} documentation files:")
        for doc_type, file_path in generated_files.items():
            print(f"  • {doc_type}: {file_path}")
    
    return 0


def main() -> int:
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="WebSocket Configuration Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate current environment
  %(prog)s validate
  
  # Validate specific environment file
  %(prog)s validate --env-file .env.production
  
  # Migrate configuration
  %(prog)s migrate legacy_to_v1 --env-file .env
  
  # Perform health check
  %(prog)s health
  
  # Start health monitoring
  %(prog)s health --monitor --interval 30
  
  # Generate documentation
  %(prog)s docs reference --output websocket_config.md
  %(prog)s docs template --output .env.template
  %(prog)s docs deployment --deployment-type docker
        """
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate WebSocket configuration")
    validate_parser.add_argument("--env-file", help="Environment file to validate")
    validate_parser.add_argument("--output", help="Output validation report to file (JSON)")
    validate_parser.add_argument("--verbose", action="store_true", help="Show detailed information")
    
    # Migrate command
    migrate_parser = subparsers.add_parser("migrate", help="Migrate WebSocket configuration")
    migrate_parser.add_argument("plan", help="Migration plan name")
    migrate_parser.add_argument("--env-file", default=".env", help="Environment file to migrate")
    migrate_parser.add_argument("--backup-dir", help="Backup directory")
    migrate_parser.add_argument("--dry-run", action="store_true", help="Simulate migration without changes")
    migrate_parser.add_argument("--analyze", action="store_true", help="Analyze configuration before migration")
    
    # Health command
    health_parser = subparsers.add_parser("health", help="Check WebSocket configuration health")
    health_parser.add_argument("--monitor", action="store_true", help="Start continuous monitoring")
    health_parser.add_argument("--interval", type=int, default=60, help="Health check interval in seconds")
    health_parser.add_argument("--output", help="Output health report to file (JSON)")
    
    # Docs command
    docs_parser = subparsers.add_parser("docs", help="Generate WebSocket configuration documentation")
    docs_parser.add_argument(
        "type",
        choices=["reference", "template", "deployment", "all"],
        help="Documentation type to generate"
    )
    docs_parser.add_argument(
        "--format",
        choices=["markdown", "html", "json"],
        default="markdown",
        help="Output format for reference documentation"
    )
    docs_parser.add_argument(
        "--deployment-type",
        choices=["docker", "kubernetes", "systemd", "nginx"],
        help="Deployment type for deployment guide"
    )
    docs_parser.add_argument("--output", help="Output file or directory")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Execute command
    try:
        if args.command == "validate":
            return validate_command(args)
        elif args.command == "migrate":
            return migrate_command(args)
        elif args.command == "health":
            return health_command(args)
        elif args.command == "docs":
            return docs_command(args)
        else:
            print(f"❌ Unknown command: {args.command}")
            return 1
    
    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if args.log_level == "DEBUG":
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())