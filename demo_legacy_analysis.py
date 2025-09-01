#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Demo script showing the Legacy System Analyzer in action
"""

from legacy_system_analyzer import LegacySystemAnalyzer

def main():
    print("🔍 LEGACY NOTIFICATION SYSTEM ANALYZER DEMO")
    print("=" * 50)
    
    # Initialize analyzer
    analyzer = LegacySystemAnalyzer(".")
    
    # Scan for legacy patterns
    print("\n📊 Scanning for legacy notification patterns...")
    results = analyzer.scan_legacy_notifications()
    
    # Print summary
    total_patterns = sum(len(patterns) for patterns in results.values())
    print(f"\n✅ Scan complete! Found {total_patterns} legacy notification patterns:")
    
    for pattern_type, patterns in results.items():
        if patterns:
            print(f"   • {pattern_type.replace('_', ' ').title()}: {len(patterns)}")
            
            # Show first few examples
            for i, pattern in enumerate(patterns[:3]):
                risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴", "critical": "🚨"}
                emoji = risk_emoji.get(pattern.risk_level, "⚪")
                print(f"     {emoji} {pattern.file_path}:{pattern.line_number} - {pattern.code_snippet[:50]}...")
            
            if len(patterns) > 3:
                print(f"     ... and {len(patterns) - 3} more")
    
    # Analyze dependencies
    print(f"\n🔗 Analyzing dependencies...")
    dependencies = analyzer.identify_dependencies()
    
    total_deps = sum(len(deps) for deps in dependencies.values())
    print(f"✅ Found {total_deps} dependencies")
    
    # Generate migration plan
    print(f"\n📋 Generating migration plan...")
    plans = analyzer.generate_removal_plan()
    
    print(f"✅ Generated {len(plans)} migration phases:")
    for plan in plans:
        effort_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}
        emoji = effort_emoji.get(plan.estimated_effort, "⚪")
        print(f"   {emoji} Phase {plan.phase}: {plan.description}")
        print(f"      Files to modify: {len(plan.files_to_modify)}")
        print(f"      Patterns to remove: {len(plan.patterns_to_remove)}")
    
    # Export report
    print(f"\n💾 Exporting analysis report...")
    analyzer.export_analysis_report("demo_legacy_analysis_report.json")
    print("✅ Report exported to demo_legacy_analysis_report.json")
    
    print(f"\n🎉 Demo complete!")
    print(f"   • Total patterns found: {total_patterns}")
    print(f"   • Total dependencies: {total_deps}")
    print(f"   • Migration phases: {len(plans)}")
    print(f"   • Files affected: {len(set(p.file_path for patterns in results.values() for p in patterns))}")

if __name__ == "__main__":
    main()