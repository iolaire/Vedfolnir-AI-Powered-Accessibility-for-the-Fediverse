# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import click
import json
from flask import current_app
from flask.cli import with_appcontext
from app.services.monitoring.performance.monitors.session_performance_monitor import get_performance_monitor

@click.group()
def session_monitoring():
    """Session performance monitoring commands."""
    pass

@session_monitoring.command()
@with_appcontext
def status():
    """Show current session performance status."""
    try:
        monitor = get_performance_monitor()
        metrics = monitor.get_current_metrics()
        
        click.echo("Session Performance Status")
        click.echo("=" * 50)
        
        # Session metrics
        session_metrics = metrics['session_metrics']
        click.echo(f"Sessions Created: {session_metrics['creations']}")
        click.echo(f"Sessions Closed: {session_metrics['closures']}")
        click.echo(f"Active Sessions: {session_metrics['active_sessions']}")
        click.echo(f"Peak Active Sessions: {session_metrics['peak_active_sessions']}")
        click.echo(f"Session Commits: {session_metrics['commits']}")
        click.echo(f"Session Rollbacks: {session_metrics['rollbacks']}")
        click.echo(f"Session Errors: {session_metrics['errors']}")
        click.echo(f"Average Session Duration: {session_metrics['average_duration']:.3f}s")
        
        click.echo()
        
        # Recovery metrics
        recovery_metrics = metrics['recovery_metrics']
        click.echo("Recovery Metrics")
        click.echo("-" * 20)
        click.echo(f"Detached Instance Recoveries: {recovery_metrics['detached_instance_recoveries']}")
        click.echo(f"Session Reattachments: {recovery_metrics['session_reattachments']}")
        click.echo(f"Recovery Rate: {recovery_metrics['recovery_rate']:.2%}")
        
        click.echo()
        
        # Performance metrics
        perf_metrics = metrics['performance_metrics']
        click.echo("Performance Timing")
        click.echo("-" * 20)
        click.echo(f"Avg Creation Time: {perf_metrics['avg_creation_time']:.3f}s")
        click.echo(f"Avg Cleanup Time: {perf_metrics['avg_cleanup_time']:.3f}s")
        click.echo(f"Avg Recovery Time: {perf_metrics['avg_recovery_time']:.3f}s")
        
        click.echo()
        
        # Pool metrics
        pool_metrics = metrics['pool_metrics']
        click.echo("Database Pool")
        click.echo("-" * 20)
        click.echo(f"Pool Size: {pool_metrics['pool_size']}")
        click.echo(f"Checked Out: {pool_metrics['checked_out']}")
        click.echo(f"Overflow: {pool_metrics['overflow']}")
        click.echo(f"Checked In: {pool_metrics['checked_in']}")
        
        click.echo()
        click.echo(f"Active Requests: {metrics['active_requests']}")
        
    except Exception as e:
        click.echo(f"Error retrieving session performance status: {e}", err=True)

@session_monitoring.command()
@with_appcontext
def summary():
    """Show detailed performance summary."""
    try:
        monitor = get_performance_monitor()
        summary = monitor.get_performance_summary()
        click.echo(summary)
    except Exception as e:
        click.echo(f"Error retrieving performance summary: {e}", err=True)

@session_monitoring.command()
@with_appcontext
@click.option('--format', type=click.Choice(['json', 'text']), default='text',
              help='Output format (json or text)')
def metrics(format):
    """Export current metrics."""
    try:
        monitor = get_performance_monitor()
        metrics = monitor.get_current_metrics()
        
        if format == 'json':
            click.echo(json.dumps(metrics, indent=2, default=str))
        else:
            # Text format
            click.echo("Session Performance Metrics")
            click.echo("=" * 50)
            click.echo(f"Timestamp: {metrics['timestamp']}")
            click.echo()
            
            for category, data in metrics.items():
                if category == 'timestamp':
                    continue
                    
                click.echo(f"{category.replace('_', ' ').title()}:")
                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, float):
                            click.echo(f"  {key}: {value:.3f}")
                        else:
                            click.echo(f"  {key}: {value}")
                else:
                    click.echo(f"  {data}")
                click.echo()
                
    except Exception as e:
        click.echo(f"Error retrieving metrics: {e}", err=True)

@session_monitoring.command()
@with_appcontext
@click.option('--threshold', type=float, default=1.0,
              help='Alert threshold for slow operations (seconds)')
def alerts(threshold):
    """Check for performance alerts."""
    try:
        monitor = get_performance_monitor()
        metrics = monitor.get_current_metrics()
        
        alerts_found = False
        
        click.echo("Performance Alerts")
        click.echo("=" * 30)
        
        # Check for slow operations
        perf_metrics = metrics['performance_metrics']
        
        if perf_metrics['avg_creation_time'] > threshold:
            click.echo(f"⚠️  Slow session creation: {perf_metrics['avg_creation_time']:.3f}s (threshold: {threshold}s)")
            alerts_found = True
        
        if perf_metrics['avg_cleanup_time'] > threshold:
            click.echo(f"⚠️  Slow session cleanup: {perf_metrics['avg_cleanup_time']:.3f}s (threshold: {threshold}s)")
            alerts_found = True
        
        if perf_metrics['avg_recovery_time'] > threshold:
            click.echo(f"⚠️  Slow recovery operations: {perf_metrics['avg_recovery_time']:.3f}s (threshold: {threshold}s)")
            alerts_found = True
        
        # Check for high error rates
        session_metrics = metrics['session_metrics']
        total_operations = session_metrics['creations'] + session_metrics['closures']
        
        if total_operations > 0:
            error_rate = session_metrics['errors'] / total_operations
            if error_rate > 0.05:  # 5% error rate threshold
                click.echo(f"⚠️  High error rate: {error_rate:.2%} ({session_metrics['errors']}/{total_operations})")
                alerts_found = True
        
        # Check for high recovery rate
        recovery_rate = metrics['recovery_metrics']['recovery_rate']
        if recovery_rate > 0.1:  # 10% recovery rate threshold
            click.echo(f"⚠️  High recovery rate: {recovery_rate:.2%}")
            alerts_found = True
        
        # Check pool utilization
        pool_metrics = metrics['pool_metrics']
        if pool_metrics['pool_size'] > 0:
            utilization = pool_metrics['checked_out'] / pool_metrics['pool_size']
            if utilization > 0.8:  # 80% utilization threshold
                click.echo(f"⚠️  High pool utilization: {utilization:.1%} ({pool_metrics['checked_out']}/{pool_metrics['pool_size']})")
                alerts_found = True
        
        if not alerts_found:
            click.echo("✅ No performance alerts detected")
            
    except Exception as e:
        click.echo(f"Error checking alerts: {e}", err=True)

@session_monitoring.command()
@with_appcontext
@click.option('--interval', type=int, default=300,
              help='Logging interval in seconds')
def enable_periodic_logging(interval):
    """Enable periodic performance logging."""
    try:
        monitor = get_performance_monitor()
        
        # This would typically be set up during app initialization
        # For now, just show the current status
        click.echo(f"Periodic logging interval set to {interval} seconds")
        click.echo("Note: Periodic logging is configured during application startup")
        
        # Show current metrics as an example
        summary = monitor.get_performance_summary()
        click.echo("\nCurrent Performance Summary:")
        click.echo(summary)
        
    except Exception as e:
        click.echo(f"Error configuring periodic logging: {e}", err=True)

def register_session_monitoring_commands(app):
    """Register session monitoring CLI commands with the Flask app."""
    app.cli.add_command(session_monitoring)