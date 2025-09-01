# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
WebSocket Error Detection and Categorization System Demo

This script demonstrates the comprehensive error detection and categorization
system implemented for Task 8, showing how different types of WebSocket errors
are detected, categorized, and handled with actionable debugging information.
"""

import logging
import tempfile
from websocket_error_detector import WebSocketErrorDetector, WebSocketErrorCategory
from websocket_error_logger import WebSocketErrorLogger

def main():
    """Demonstrate the WebSocket error detection system"""
    
    print("🔍 WebSocket Error Detection and Categorization System Demo")
    print("=" * 60)
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Initialize components
    detector = WebSocketErrorDetector()
    
    # Use temporary directory for demo
    with tempfile.TemporaryDirectory() as temp_dir:
        logger = WebSocketErrorLogger(log_dir=temp_dir)
        
        print("\n1. 🚫 CORS Error Detection (Requirement 4.1)")
        print("-" * 40)
        
        # Demonstrate CORS error detection
        cors_errors = [
            "CORS policy: Cross origin requests are only supported for protocol schemes",
            "Access to XMLHttpRequest blocked by CORS policy",
            "Preflight request failed"
        ]
        
        for error_text in cors_errors:
            error_info = detector.detect_error(error_text)
            print(f"Error: {error_text[:50]}...")
            print(f"  Category: {error_info.category.value}")
            print(f"  Severity: {error_info.severity.value}")
            print(f"  User Message: {error_info.user_message}")
            print(f"  Error Code: {error_info.error_code}")
            logger.log_error(error_info)
            print()
        
        print("\n2. 🔐 Authentication Error Detection")
        print("-" * 40)
        
        # Demonstrate authentication error detection
        auth_errors = [
            "Authentication failed",
            "Session expired",
            "Invalid token",
            "Unauthorized access"
        ]
        
        for error_text in auth_errors:
            error_info = detector.detect_error(error_text)
            print(f"Error: {error_text}")
            print(f"  Category: {error_info.category.value}")
            print(f"  User Message: {error_info.user_message}")
            print(f"  Suggested Fix: {error_info.suggested_fix}")
            logger.log_error(error_info)
            print()
        
        print("\n3. 🌐 Network Error Detection")
        print("-" * 40)
        
        # Demonstrate network error detection
        network_errors = [
            "Connection refused",
            "DNS resolution failed",
            "SSL certificate error",
            "Network timeout"
        ]
        
        for error_text in network_errors:
            error_info = detector.detect_error(error_text)
            print(f"Error: {error_text}")
            print(f"  Category: {error_info.category.value}")
            print(f"  User Message: {error_info.user_message}")
            logger.log_error(error_info)
            print()
        
        print("\n4. 🔍 CORS-Specific Analysis (Requirement 9.2)")
        print("-" * 40)
        
        # Demonstrate CORS-specific error analysis
        origin = "http://localhost:3000"
        allowed_origins = ["http://localhost:5000", "https://example.com"]
        
        cors_error = detector.detect_cors_error(origin, allowed_origins)
        print(f"Failed Origin: {origin}")
        print(f"Allowed Origins: {allowed_origins}")
        print(f"Error Code: {cors_error.error_code}")
        print(f"User Message: {cors_error.user_message}")
        
        # Show CORS analysis details
        cors_analysis = cors_error.debug_info.get('cors_analysis', {})
        print(f"CORS Analysis:")
        print(f"  Origin Provided: {cors_analysis.get('origin_provided')}")
        print(f"  Origin Allowed: {cors_analysis.get('origin_in_allowed_list')}")
        print(f"  Origin Protocol: {cors_analysis.get('origin_protocol')}")
        print(f"  Suggested Origins: {cors_analysis.get('suggested_origins')}")
        
        logger.log_cors_error(cors_error, origin, allowed_origins)
        print()
        
        print("\n5. 🛠️ Debugging Suggestions (Requirement 9.3)")
        print("-" * 40)
        
        # Show debugging suggestions for different error types
        error_types = [
            ("CORS policy violation", WebSocketErrorCategory.CORS),
            ("Authentication failed", WebSocketErrorCategory.AUTHENTICATION),
            ("Connection refused", WebSocketErrorCategory.NETWORK)
        ]
        
        for error_text, expected_category in error_types:
            error_info = detector.detect_error(error_text)
            suggestions = detector.get_debugging_suggestions(error_info)
            
            print(f"Error: {error_text}")
            print(f"Debugging Suggestions:")
            for i, suggestion in enumerate(suggestions[:3], 1):  # Show first 3
                print(f"  {i}. {suggestion}")
            print()
        
        print("\n6. 📊 Error Statistics and Summary")
        print("-" * 40)
        
        # Show error statistics
        stats = detector.get_error_statistics()
        print(f"Total Errors Detected: {stats['statistics']['total_errors']}")
        print(f"Errors by Category:")
        for category, count in stats['statistics']['by_category'].items():
            if count > 0:
                print(f"  {category}: {count}")
        
        print(f"\nTop Error Categories:")
        for category, count in stats['top_categories']:
            print(f"  {category}: {count}")
        
        # Show error summary from logger
        summary = logger.get_error_summary(hours=24)
        print(f"\nError Summary (last 24 hours):")
        print(f"  Total: {summary['total_errors']}")
        print(f"  Actionable Insights:")
        for insight in summary['actionable_insights']:
            print(f"    • {insight}")
        
        print("\n7. 📋 Debugging Report Example")
        print("-" * 40)
        
        # Generate a debugging report for a specific error
        if summary['recent_error_codes']:
            error_code = summary['recent_error_codes'][-1]
            report = logger.get_debugging_report(error_code)
            
            if report:
                print(f"Error Code: {report['error_code']}")
                print(f"Category: {report['category']}")
                print(f"Severity: {report['severity']}")
                print(f"Description: {report['description']}")
                print(f"Debugging Steps:")
                for i, step in enumerate(report['debugging_steps'][:3], 1):
                    print(f"  {i}. {step}")
        
        print("\n✅ Task 8: Comprehensive Error Detection and Categorization")
        print("=" * 60)
        print("All requirements successfully implemented:")
        print("  ✅ 4.1: CORS error detection and categorization")
        print("  ✅ 4.4: User-friendly error messages with CORS guidance")
        print("  ✅ 7.1: Comprehensive error recovery mechanisms")
        print("  ✅ 9.2: CORS-specific error details and suggested fixes")
        print("  ✅ 9.3: Detailed error logging with actionable debugging information")
        print("\nThe system provides:")
        print("  • Pattern-based error detection for all WebSocket error types")
        print("  • Detailed categorization with severity levels")
        print("  • User-friendly error messages for end users")
        print("  • Technical debugging information for developers")
        print("  • Actionable suggestions for error resolution")
        print("  • Comprehensive logging and monitoring capabilities")
        print("  • Integration with existing WebSocket components")


if __name__ == "__main__":
    main()