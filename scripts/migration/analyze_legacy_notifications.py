#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Legacy Notification System Analysis CLI

Command-line interface for analyzing legacy notification systems and generating
migration plans for the unified WebSocket notification framework.
"""

import argparse
import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from legacy_system_analyzer import (
    LegacySystemAnalyzer,
    create_migration_backup,
    validate_migration_prerequisites
)


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('legacy_analysis.log')
        ]
    )


def print_summary(results: dict, dependencies: dict, plans: list) -> None:
    """Print analysis summary to console"""
    print("\n" + "="*60)
    print("LEGACY NOTIFICATION SYSTEM ANALYSIS SUMMARY")
    print("="*60)
    
    # Pattern summary
    print(f"\n📊 LEGACY PATTERNS FOUND:")
    total_patterns = sum(len(patterns) for patterns in results.values())
    print(f"   Total Patterns: {total_patterns}")
    
    for pattern_type, patterns in results.items():
        if patterns:
            print(f"   • {pattern_type.replace('_', ' ').title()}: {len(patterns)}")
            
            # Show risk distribution
            risk_counts = {}
            for pattern in patterns:
                risk_counts[pattern.risk_level] = risk_counts.get(pattern.risk_level, 0) + 1
            
            if risk_counts:
                risk_str = ", ".join([f"{risk}: {count}" for risk, count in risk_counts.items()])
                print(f"     Risk levels: {risk_str}")
    
    # Dependency summary
    print(f"\n🔗 DEPENDENCIES FOUND:")
    total_deps = sum(len(deps) for deps in dependencies.values())
    print(f"   Total Dependencies: {total_deps}")
    
    for dep_type, deps in dependencies.items():
        if deps:
            print(f"   • {dep_type.replace('_', ' ').title()}: {len(deps)}")
    
    # Migration plan summary
    print(f"\n📋 MIGRATION PLAN:")
    print(f"   Total Phases: {len(plans)}")
    
    for plan in plans:
        effort_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}
        emoji = effort_emoji.get(plan.estimated_effort, "⚪")
        print(f"   {emoji} Phase {plan.phase}: {plan.description}")
        print(f"      Files to modify: {len(plan.files_to_modify)}")
        print(f"      Patterns to remove: {len(plan.patterns_to_remove)}")
        print(f"      Effort: {plan.estimated_effort}")


def print_detailed_patterns(results: dict, show_code: bool = False) -> None:
    """Print detailed pattern information"""
    print("\n" + "="*60)
    print("DETAILED PATTERN ANALYSIS")
    print("="*60)
    
    for pattern_type, patterns in results.items():
        if not patterns:
            continue
            
        print(f"\n📁 {pattern_type.replace('_', ' ').upper()}:")
        
        # Group by file
        files = {}
        for pattern in patterns:
            if pattern.file_path not in files:
                files[pattern.file_path] = []
            files[pattern.file_path].append(pattern)
        
        for file_path, file_patterns in files.items():
            print(f"\n   📄 {file_path}")
            
            for pattern in file_patterns:
                risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴", "critical": "🚨"}
                emoji = risk_emoji.get(pattern.risk_level, "⚪")
                
                print(f"      {emoji} Line {pattern.line_number}: {pattern.risk_level} risk")
                
                if pattern.function_name:
                    print(f"         Function: {pattern.function_name}")
                
                if show_code:
                    print(f"         Code: {pattern.code_snippet}")
                
                if pattern.migration_notes:
                    print(f"         Migration: {pattern.migration_notes}")


def print_migration_plan_details(plans: list) -> None:
    """Print detailed migration plan"""
    print("\n" + "="*60)
    print("DETAILED MIGRATION PLAN")
    print("="*60)
    
    for plan in plans:
        effort_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}
        emoji = effort_emoji.get(plan.estimated_effort, "⚪")
        
        print(f"\n{emoji} PHASE {plan.phase}: {plan.description}")
        print(f"   Estimated Effort: {plan.estimated_effort}")
        
        if plan.files_to_modify:
            print(f"\n   📁 Files to Modify ({len(plan.files_to_modify)}):")
            for file_path in plan.files_to_modify[:10]:  # Show first 10
                print(f"      • {file_path}")
            if len(plan.files_to_modify) > 10:
                print(f"      ... and {len(plan.files_to_modify) - 10} more")
        
        if plan.patterns_to_remove:
            print(f"\n   🗑️  Patterns to Remove ({len(plan.patterns_to_remove)}):")
            pattern_types = {}
            for pattern in plan.patterns_to_remove:
                pattern_types[pattern.pattern_type] = pattern_types.get(pattern.pattern_type, 0) + 1
            
            for pattern_type, count in pattern_types.items():
                print(f"      • {pattern_type}: {count}")
        
        if plan.rollback_procedures:
            print(f"\n   ↩️  Rollback Procedures:")
            for i, procedure in enumerate(plan.rollback_procedures, 1):
                print(f"      {i}. {procedure}")
        
        if plan.validation_steps:
            print(f"\n   ✅ Validation Steps:")
            for i, step in enumerate(plan.validation_steps, 1):
                print(f"      {i}. {step}")


def check_prerequisites() -> bool:
    """Check migration prerequisites"""
    print("\n🔍 CHECKING MIGRATION PREREQUISITES...")
    
    checks = validate_migration_prerequisites()
    all_passed = True
    
    for check_name, passed in checks.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        check_display = check_name.replace('_', ' ').title()
        print(f"   {status}: {check_display}")
        
        if not passed:
            all_passed = False
    
    if not all_passed:
        print("\n⚠️  Some prerequisites are not met. Please address these before migration.")
        print("   Refer to the migration documentation for setup instructions.")
    else:
        print("\n✅ All prerequisites met. Ready for migration!")
    
    return all_passed


def create_backup_if_requested(project_root: str, backup_path: str) -> bool:
    """Create backup if requested"""
    if backup_path:
        print(f"\n💾 Creating backup at {backup_path}...")
        
        if create_migration_backup(project_root, backup_path):
            print("   ✅ Backup created successfully")
            return True
        else:
            print("   ❌ Backup creation failed")
            return False
    
    return True


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="Analyze legacy notification systems for migration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic analysis
  python analyze_legacy_notifications.py

  # Detailed analysis with code snippets
  python analyze_legacy_notifications.py --detailed --show-code

  # Analysis with backup creation
  python analyze_legacy_notifications.py --backup ./backup

  # Check prerequisites only
  python analyze_legacy_notifications.py --check-prerequisites

  # Export detailed report
  python analyze_legacy_notifications.py --output report.json --detailed
        """
    )
    
    parser.add_argument(
        '--project-root',
        default='.',
        help='Root directory of the project to analyze (default: current directory)'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output file for detailed JSON report'
    )
    
    parser.add_argument(
        '--backup',
        help='Create backup before analysis at specified path'
    )
    
    parser.add_argument(
        '--detailed', '-d',
        action='store_true',
        help='Show detailed pattern and migration plan information'
    )
    
    parser.add_argument(
        '--show-code',
        action='store_true',
        help='Show code snippets in detailed output'
    )
    
    parser.add_argument(
        '--check-prerequisites',
        action='store_true',
        help='Check migration prerequisites only'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    print("🔍 LEGACY NOTIFICATION SYSTEM ANALYZER")
    print("=" * 50)
    print(f"Project Root: {os.path.abspath(args.project_root)}")
    print(f"Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check prerequisites if requested
    if args.check_prerequisites:
        prerequisites_met = check_prerequisites()
        sys.exit(0 if prerequisites_met else 1)
    
    # Create backup if requested
    if not create_backup_if_requested(args.project_root, args.backup):
        sys.exit(1)
    
    try:
        # Initialize analyzer
        analyzer = LegacySystemAnalyzer(args.project_root)
        
        # Perform analysis
        print("\n🔍 Scanning for legacy notification patterns...")
        results = analyzer.scan_legacy_notifications()
        
        print("🔗 Analyzing dependencies...")
        dependencies = analyzer.identify_dependencies()
        
        print("📋 Generating migration plan...")
        plans = analyzer.generate_removal_plan()
        
        # Print summary
        print_summary(results, dependencies, plans)
        
        # Print detailed information if requested
        if args.detailed:
            print_detailed_patterns(results, args.show_code)
            print_migration_plan_details(plans)
        
        # Check prerequisites
        check_prerequisites()
        
        # Export report if requested
        if args.output:
            print(f"\n💾 Exporting detailed report to {args.output}...")
            analyzer.export_analysis_report(args.output)
            print("   ✅ Report exported successfully")
        
        # Final recommendations
        print("\n" + "="*60)
        print("RECOMMENDATIONS")
        print("="*60)
        
        total_patterns = sum(len(patterns) for patterns in results.values())
        high_risk_patterns = sum(
            len([p for p in patterns if p.risk_level == 'high'])
            for patterns in results.values()
        )
        
        if total_patterns == 0:
            print("🎉 No legacy notification patterns found!")
            print("   Your codebase appears to already use a unified notification system.")
        elif high_risk_patterns > 10:
            print("⚠️  High number of high-risk patterns detected.")
            print("   Consider extended testing and gradual migration approach.")
            print("   Review each high-risk pattern carefully before removal.")
        else:
            print("✅ Analysis complete. Ready to proceed with migration.")
            print("   Follow the generated migration plan phases in order.")
            print("   Test thoroughly after each phase before proceeding.")
        
        print(f"\n📊 Analysis Statistics:")
        print(f"   • Total legacy patterns: {total_patterns}")
        print(f"   • High-risk patterns: {high_risk_patterns}")
        print(f"   • Migration phases: {len(plans)}")
        print(f"   • Files affected: {len(set(p.file_path for patterns in results.values() for p in patterns))}")
        
        if args.output:
            print(f"\n📄 Detailed report saved to: {args.output}")
        
        print("\n🚀 Next Steps:")
        print("   1. Review the migration plan phases")
        print("   2. Ensure all prerequisites are met")
        print("   3. Create a backup of your codebase")
        print("   4. Implement unified notification system")
        print("   5. Execute migration phases in order")
        print("   6. Test thoroughly after each phase")
        
    except Exception as e:
        logging.error(f"Analysis failed: {e}")
        print(f"\n❌ Analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()