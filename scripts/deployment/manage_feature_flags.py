# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Feature Flag Management Script
Manages feature flags for gradual rollout of admin capabilities
"""

import sys
import argparse
import json
from pathlib import Path
from typing import List

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.services.admin.components.feature_flags import FeatureFlagManager, RolloutStrategy, FeatureState

class FeatureFlagCLI:
    """Command-line interface for feature flag management"""
    
    def __init__(self):
        self.manager = FeatureFlagManager()
    
    def list_flags(self, verbose: bool = False):
        """List all feature flags"""
        flags = self.manager.list_flags()
        
        print("Feature Flags Status:")
        print("=" * 50)
        
        for name, status in flags.items():
            state_emoji = {
                'enabled': '✅',
                'disabled': '❌', 
                'beta': '🧪',
                'rollout': '🚀',
                'deprecated': '⚠️'
            }.get(status['state'], '❓')
            
            print(f"{state_emoji} {name}: {status['state'].upper()}")
            
            if verbose:
                print(f"   Description: {status['description']}")
                print(f"   Strategy: {status['rollout_strategy']}")
                if status['dependencies']:
                    deps_status = "✅" if status['dependencies_met'] else "❌"
                    print(f"   Dependencies: {deps_status} {', '.join(status['dependencies'])}")
                print()
    
    def enable_flag(self, flag_name: str, strategy: str = None, 
                   percentage: int = None, users: List[str] = None):
        """Enable a feature flag"""
        rollout_strategy = None
        if strategy:
            try:
                rollout_strategy = RolloutStrategy(strategy)
            except ValueError:
                print(f"Invalid rollout strategy: {strategy}")
                print(f"Valid strategies: {[s.value for s in RolloutStrategy]}")
                return False
        
        success = self.manager.enable_flag(
            flag_name, 
            rollout_strategy=rollout_strategy,
            rollout_percentage=percentage,
            allowed_users=users or []
        )
        
        if success:
            print(f"✅ Enabled feature flag: {flag_name}")
        else:
            print(f"❌ Failed to enable feature flag: {flag_name}")
        
        return success
    
    def disable_flag(self, flag_name: str):
        """Disable a feature flag"""
        success = self.manager.disable_flag(flag_name)
        
        if success:
            print(f"❌ Disabled feature flag: {flag_name}")
        else:
            print(f"❌ Failed to disable feature flag: {flag_name}")
        
        return success
    
    def show_flag(self, flag_name: str):
        """Show detailed information about a flag"""
        status = self.manager.get_flag_status(flag_name)
        
        if not status:
            print(f"❌ Feature flag not found: {flag_name}")
            return
        
        print(f"Feature Flag: {flag_name}")
        print("=" * (len(flag_name) + 14))
        print(f"State: {status['state'].upper()}")
        print(f"Description: {status['description']}")
        print(f"Rollout Strategy: {status['rollout_strategy']}")
        
        if status['rollout_percentage'] > 0:
            print(f"Rollout Percentage: {status['rollout_percentage']}%")
        
        if status['allowed_users']:
            print(f"Allowed Users: {', '.join(status['allowed_users'])}")
        
        if status['dependencies']:
            deps_status = "✅" if status['dependencies_met'] else "❌"
            print(f"Dependencies: {deps_status} {', '.join(status['dependencies'])}")
        
        time_status = "✅" if status['time_constraints_met'] else "❌"
        print(f"Time Constraints: {time_status}")
        
        if status['metadata']:
            print(f"Metadata: {json.dumps(status['metadata'], indent=2)}")
    
    def rollout_plan(self, plan_name: str):
        """Execute a predefined rollout plan"""
        plans = {
            'phase1_readonly': {
                'description': 'Phase 1: Enable read-only admin features',
                'flags': [
                    ('multi_tenant_admin', 'admin_only'),
                    ('admin_dashboard', 'admin_only'),
                    ('system_monitoring', 'admin_only')
                ]
            },
            'phase2_job_management': {
                'description': 'Phase 2: Enable job management',
                'flags': [
                    ('admin_job_management', 'admin_only'),
                    ('enhanced_error_handling', 'all_users'),
                    ('audit_logging', 'all_users')
                ]
            },
            'phase3_user_management': {
                'description': 'Phase 3: Enable user management',
                'flags': [
                    ('admin_user_management', 'admin_only'),
                    ('performance_metrics', 'all_users')
                ]
            },
            'phase4_monitoring': {
                'description': 'Phase 4: Enable monitoring and alerts',
                'flags': [
                    ('alert_system', 'admin_only'),
                    ('real_time_updates', 'admin_only')
                ]
            },
            'full_rollout': {
                'description': 'Full rollout: Enable all features',
                'flags': [
                    ('multi_tenant_admin', 'all_users'),
                    ('admin_dashboard', 'admin_only'),
                    ('admin_job_management', 'admin_only'),
                    ('admin_user_management', 'admin_only'),
                    ('system_monitoring', 'all_users'),
                    ('alert_system', 'admin_only'),
                    ('performance_metrics', 'all_users'),
                    ('enhanced_error_handling', 'all_users'),
                    ('audit_logging', 'all_users'),
                    ('real_time_updates', 'admin_only')
                ]
            }
        }
        
        if plan_name not in plans:
            print(f"❌ Unknown rollout plan: {plan_name}")
            print(f"Available plans: {', '.join(plans.keys())}")
            return False
        
        plan = plans[plan_name]
        print(f"Executing rollout plan: {plan_name}")
        print(f"Description: {plan['description']}")
        print()
        
        success_count = 0
        for flag_name, strategy in plan['flags']:
            print(f"Enabling {flag_name} with strategy {strategy}...")
            if self.enable_flag(flag_name, strategy):
                success_count += 1
            else:
                print(f"⚠️  Failed to enable {flag_name}")
        
        print()
        print(f"Rollout plan completed: {success_count}/{len(plan['flags'])} flags enabled")
        return success_count == len(plan['flags'])
    
    def emergency_disable(self):
        """Emergency disable all admin features"""
        print("🚨 EMERGENCY DISABLE: Disabling all admin features...")
        
        admin_flags = [
            'multi_tenant_admin',
            'admin_dashboard', 
            'admin_job_management',
            'admin_user_management',
            'alert_system',
            'real_time_updates'
        ]
        
        success_count = 0
        for flag_name in admin_flags:
            if self.disable_flag(flag_name):
                success_count += 1
        
        print(f"Emergency disable completed: {success_count}/{len(admin_flags)} flags disabled")
        return success_count == len(admin_flags)

def main():
    parser = argparse.ArgumentParser(description='Feature Flag Management')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all feature flags')
    list_parser.add_argument('--verbose', '-v', action='store_true', 
                           help='Show detailed information')
    
    # Enable command
    enable_parser = subparsers.add_parser('enable', help='Enable a feature flag')
    enable_parser.add_argument('flag_name', help='Name of the feature flag')
    enable_parser.add_argument('--strategy', choices=[s.value for s in RolloutStrategy],
                             help='Rollout strategy')
    enable_parser.add_argument('--percentage', type=int, 
                             help='Rollout percentage (for percentage strategy)')
    enable_parser.add_argument('--users', nargs='+', 
                             help='Allowed users (for user_list strategy)')
    
    # Disable command
    disable_parser = subparsers.add_parser('disable', help='Disable a feature flag')
    disable_parser.add_argument('flag_name', help='Name of the feature flag')
    
    # Show command
    show_parser = subparsers.add_parser('show', help='Show detailed flag information')
    show_parser.add_argument('flag_name', help='Name of the feature flag')
    
    # Rollout command
    rollout_parser = subparsers.add_parser('rollout', help='Execute rollout plan')
    rollout_parser.add_argument('plan_name', 
                               choices=['phase1_readonly', 'phase2_job_management', 
                                       'phase3_user_management', 'phase4_monitoring', 
                                       'full_rollout'],
                               help='Rollout plan to execute')
    
    # Emergency command
    emergency_parser = subparsers.add_parser('emergency', help='Emergency disable all admin features')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cli = FeatureFlagCLI()
    
    if args.command == 'list':
        cli.list_flags(args.verbose)
    elif args.command == 'enable':
        cli.enable_flag(args.flag_name, args.strategy, args.percentage, args.users)
    elif args.command == 'disable':
        cli.disable_flag(args.flag_name)
    elif args.command == 'show':
        cli.show_flag(args.flag_name)
    elif args.command == 'rollout':
        cli.rollout_plan(args.plan_name)
    elif args.command == 'emergency':
        cli.emergency_disable()

if __name__ == '__main__':
    main()