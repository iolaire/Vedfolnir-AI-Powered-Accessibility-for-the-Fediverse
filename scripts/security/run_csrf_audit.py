#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
CSRF Security Audit CLI

Command-line interface for running CSRF security audits on templates
and generating compliance reports.
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from security.audit.csrf_template_scanner import CSRFTemplateScanner
from security.audit.csrf_compliance_validator import (
    CSRFComplianceValidator, SecurityAuditReporter, ContinuousIntegrationValidator
)

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='CSRF Security Audit Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan all templates
  python run_csrf_audit.py --templates-dir templates

  # Generate compliance report
  python run_csrf_audit.py --templates-dir templates --report --format json

  # CI validation with thresholds
  python run_csrf_audit.py --templates-dir templates --ci-gate --min-score 0.8

  # Export report in multiple formats
  python run_csrf_audit.py --templates-dir templates --report --format html,json,csv
        """
    )
    
    parser.add_argument(
        '--templates-dir',
        default='templates',
        help='Directory containing templates to scan (default: templates)'
    )
    
    parser.add_argument(
        '--output-dir',
        default='security/reports',
        help='Output directory for reports (default: security/reports)'
    )
    
    parser.add_argument(
        '--report',
        action='store_true',
        help='Generate compliance report'
    )
    
    parser.add_argument(
        '--format',
        default='json',
        help='Report format(s): json, html, csv (comma-separated for multiple)'
    )
    
    parser.add_argument(
        '--ci-gate',
        action='store_true',
        help='Run CI security gate validation'
    )
    
    parser.add_argument(
        '--min-score',
        type=float,
        default=0.8,
        help='Minimum compliance score for CI gate (default: 0.8)'
    )
    
    parser.add_argument(
        '--max-critical',
        type=int,
        default=0,
        help='Maximum critical issues for CI gate (default: 0)'
    )
    
    parser.add_argument(
        '--max-high',
        type=int,
        default=2,
        help='Maximum high issues for CI gate (default: 2)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )
    
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Quiet output (errors only)'
    )
    
    args = parser.parse_args()
    
    # Set up logging level
    if args.quiet:
        import logging
        logging.getLogger().setLevel(logging.ERROR)
    elif args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Initialize components
        scanner = CSRFTemplateScanner()
        validator = CSRFComplianceValidator()
        reporter = SecurityAuditReporter()
        ci_validator = ContinuousIntegrationValidator()
        
        # Check if templates directory exists
        templates_path = Path(args.templates_dir)
        if not templates_path.exists():
            print(f"Error: Templates directory '{args.templates_dir}' not found", file=sys.stderr)
            return 1
        
        if not args.quiet:
            print(f"🔍 Scanning templates in {args.templates_dir}...")
        
        # Scan all templates
        results = scanner.scan_all_templates(args.templates_dir)
        
        if not results:
            print(f"Warning: No templates found in {args.templates_dir}", file=sys.stderr)
            return 0
        
        # Calculate overall compliance
        overall_score = validator.calculate_overall_compliance(results)
        
        # Count issues
        total_issues = sum(len(r.issues) for r in results)
        critical_issues = sum(len([i for i in r.issues if i.severity == 'CRITICAL']) for r in results)
        high_issues = sum(len([i for i in r.issues if i.severity == 'HIGH']) for r in results)
        
        if not args.quiet:
            print(f"📊 Scan Results:")
            print(f"   Templates scanned: {len(results)}")
            print(f"   Overall compliance score: {overall_score:.2f}")
            print(f"   Total issues: {total_issues}")
            print(f"   Critical issues: {critical_issues}")
            print(f"   High issues: {high_issues}")
        
        # Generate report if requested
        if args.report:
            if not args.quiet:
                print(f"📝 Generating compliance report...")
            
            report = reporter.generate_compliance_report(results)
            
            # Create output directory
            output_path = Path(args.output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Export in requested formats
            formats = [f.strip() for f in args.format.split(',')]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            for format_type in formats:
                filename = f"csrf_compliance_report_{timestamp}.{format_type}"
                file_path = output_path / filename
                
                try:
                    reporter.export_report(report, str(file_path), format=format_type)
                    if not args.quiet:
                        print(f"   ✅ Report exported: {file_path}")
                except Exception as e:
                    print(f"   ❌ Failed to export {format_type} report: {e}", file=sys.stderr)
        
        # Run CI gate validation if requested
        if args.ci_gate:
            if not args.quiet:
                print(f"🚪 Running CI security gate validation...")
            
            gate_config = {
                'minimum_compliance_score': args.min_score,
                'max_critical_issues': args.max_critical,
                'max_high_issues': args.max_high
            }
            
            gate_result = ci_validator.validate_security_gate(results, gate_config)
            
            if gate_result['passed']:
                if not args.quiet:
                    print(f"   ✅ Security gate PASSED")
                    print(f"   Compliance score: {gate_result['overall_score']:.2f} (>= {args.min_score})")
                    print(f"   Critical issues: {gate_result['issue_counts']['CRITICAL']} (<= {args.max_critical})")
                    print(f"   High issues: {gate_result['issue_counts']['HIGH']} (<= {args.max_high})")
                return 0
            else:
                print(f"❌ Security gate FAILED", file=sys.stderr)
                print(f"   Compliance score: {gate_result['overall_score']:.2f} (required: >= {args.min_score})", file=sys.stderr)
                print(f"   Critical issues: {gate_result['issue_counts']['CRITICAL']} (max: {args.max_critical})", file=sys.stderr)
                print(f"   High issues: {gate_result['issue_counts']['HIGH']} (max: {args.max_high})", file=sys.stderr)
                
                if gate_result['violations']:
                    print(f"   Violations:", file=sys.stderr)
                    for violation in gate_result['violations']:
                        print(f"     - {violation}", file=sys.stderr)
                
                return gate_result['exit_code']
        
        # Show summary of issues if any
        if total_issues > 0 and not args.quiet:
            print(f"\n⚠️  Issues found:")
            
            # Group issues by template
            template_issues = {}
            for result in results:
                if result.issues:
                    template_issues[result.template_path] = result.issues
            
            for template_path, issues in template_issues.items():
                print(f"   {template_path}:")
                for issue in issues[:3]:  # Show first 3 issues
                    print(f"     - {issue.severity}: {issue.description}")
                if len(issues) > 3:
                    print(f"     ... and {len(issues) - 3} more issues")
        
        # Return appropriate exit code
        if critical_issues > 0:
            return 2  # Critical issues found
        elif high_issues > 0:
            return 1  # High issues found
        else:
            return 0  # Success
            
    except KeyboardInterrupt:
        print("\n❌ Audit interrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"❌ Audit failed: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())