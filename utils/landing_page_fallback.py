# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Landing Page Fallback and Error Handling

This module provides comprehensive fallback mechanisms and error handling
specifically for the Flask landing page functionality.
"""

import logging
from typing import Optional, Dict, Any, Tuple
from flask import Response, request, current_app, make_response
from datetime import datetime, timezone
import traceback
import json

logger = logging.getLogger(__name__)

class LandingPageError(Exception):
    """Custom exception for landing page specific errors"""
    
    def __init__(self, message: str, error_code: str = "LANDING_PAGE_ERROR", 
                 original_exception: Optional[Exception] = None):
        self.message = message
        self.error_code = error_code
        self.original_exception = original_exception
        self.timestamp = datetime.now(timezone.utc)
        super().__init__(message)

class AuthenticationFailureError(LandingPageError):
    """Exception for authentication-related failures"""
    
    def __init__(self, message: str, user_info: Optional[Dict[str, Any]] = None,
                 original_exception: Optional[Exception] = None):
        self.user_info = user_info or {}
        super().__init__(message, "AUTHENTICATION_FAILURE", original_exception)

class TemplateRenderingError(LandingPageError):
    """Exception for template rendering failures"""
    
    def __init__(self, template_name: str, message: str, 
                 template_context: Optional[Dict[str, Any]] = None,
                 original_exception: Optional[Exception] = None):
        self.template_name = template_name
        self.template_context = template_context or {}
        super().__init__(f"Template rendering failed for {template_name}: {message}", 
                        "TEMPLATE_RENDERING_ERROR", original_exception)

class SessionDetectionError(LandingPageError):
    """Exception for session detection failures"""
    
    def __init__(self, message: str, session_indicators: Optional[Dict[str, Any]] = None,
                 original_exception: Optional[Exception] = None):
        self.session_indicators = session_indicators or {}
        super().__init__(message, "SESSION_DETECTION_ERROR", original_exception)

def log_authentication_failure(error: Exception, user_context: Optional[Dict[str, Any]] = None) -> None:
    """
    Log authentication failures with comprehensive context information.
    
    Args:
        error: The authentication error that occurred
        user_context: Optional context about the user/session
    """
    try:
        # Gather request context safely
        request_info = {}
        if request:
            request_info = {
                'method': request.method,
                'url': request.url,
                'remote_addr': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', 'Unknown')[:200],  # Truncate for safety
                'referrer': request.headers.get('Referer', 'None'),
                'accept_language': request.headers.get('Accept-Language', 'None'),
                'has_cookies': len(request.cookies) > 0,
                'cookie_count': len(request.cookies),
                'content_type': request.headers.get('Content-Type', 'None')
            }
        
        # Sanitize user context
        safe_user_context = {}
        if user_context:
            for key, value in user_context.items():
                if key.lower() in ['password', 'token', 'secret', 'key']:
                    safe_user_context[key] = '[REDACTED]'
                else:
                    safe_user_context[key] = str(value)[:100]  # Truncate for safety
        
        # Create comprehensive log entry
        log_entry = {
            'event': 'authentication_failure',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error)[:500],  # Truncate for safety
            'request_info': request_info,
            'user_context': safe_user_context,
            'stack_trace': traceback.format_exc()[:1000] if current_app.debug else None
        }
        
        # Log with appropriate level
        if isinstance(error, AuthenticationFailureError):
            logger.warning(f"Authentication failure: {json.dumps(log_entry, indent=2)}")
        else:
            logger.error(f"Authentication error: {json.dumps(log_entry, indent=2)}")
            
    except Exception as logging_error:
        # Fallback logging if main logging fails
        logger.error(f"Failed to log authentication failure: {logging_error}")
        logger.error(f"Original authentication error: {error}")

def create_fallback_landing_html(error_context: Optional[Dict[str, Any]] = None) -> str:
    """
    Create fallback HTML for critical landing page failures.
    
    This provides a minimal but functional landing page when template
    rendering or other critical systems fail.
    
    Args:
        error_context: Optional context about the error for debugging
    
    Returns:
        Minimal HTML string for landing page
    """
    try:
        # Get basic app info safely
        app_name = "Vedfolnir"
        try:
            if current_app:
                app_name = current_app.config.get('APP_NAME', 'Vedfolnir')
        except RuntimeError:
            # Working outside of application context
            app_name = "Vedfolnir"
        
        # Create minimal but accessible HTML
        fallback_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{app_name} - AI-Powered Accessibility for the Fediverse</title>
    <meta name="description" content="AI-powered alt text generation for ActivityPub platforms like Mastodon and Pixelfed. Make your social media content accessible.">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f8f9fa;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }}
        
        .hero {{
            background: linear-gradient(135deg, #0d6efd 0%, #0a58ca 100%);
            color: white;
            padding: 4rem 0;
            text-align: center;
        }}
        
        .hero h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 1rem;
        }}
        
        .hero p {{
            font-size: 1.2rem;
            margin-bottom: 2rem;
            opacity: 0.9;
        }}
        
        .cta-button {{
            display: inline-block;
            background-color: white;
            color: #0d6efd;
            padding: 1rem 2rem;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
            font-size: 1.1rem;
            transition: all 0.3s ease;
            min-height: 48px;
            min-width: 120px;
            box-sizing: border-box;
            line-height: 1.4;
        }}
        
        .cta-button:hover {{
            background-color: #f8f9fa;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }}
        
        .features {{
            padding: 4rem 0;
            background-color: white;
        }}
        
        .features h2 {{
            text-align: center;
            font-size: 2rem;
            margin-bottom: 3rem;
            color: #333;
        }}
        
        .feature-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
            margin-top: 2rem;
        }}
        
        .feature-card {{
            text-align: center;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            background-color: #f8f9fa;
        }}
        
        .feature-card h3 {{
            font-size: 1.3rem;
            margin-bottom: 1rem;
            color: #0d6efd;
        }}
        
        .feature-card p {{
            color: #666;
        }}
        
        .login-link {{
            position: absolute;
            top: 20px;
            right: 20px;
            background-color: rgba(255, 255, 255, 0.2);
            color: white;
            padding: 0.5rem 1rem;
            text-decoration: none;
            border-radius: 4px;
            font-weight: 500;
            transition: background-color 0.3s ease;
        }}
        
        .login-link:hover {{
            background-color: rgba(255, 255, 255, 0.3);
            color: white;
            text-decoration: none;
        }}
        
        .error-notice {{
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            color: #856404;
            padding: 1rem;
            border-radius: 4px;
            margin: 1rem 0;
            text-align: center;
            font-size: 0.9rem;
        }}
        
        @media (max-width: 768px) {{
            .hero h1 {{
                font-size: 2rem;
            }}
            
            .hero p {{
                font-size: 1rem;
            }}
            
            .cta-button {{
                padding: 0.875rem 1.5rem;
                font-size: 1rem;
            }}
            
            .feature-grid {{
                grid-template-columns: 1fr;
                gap: 1.5rem;
            }}
            
            .login-link {{
                position: static;
                display: inline-block;
                margin-bottom: 1rem;
            }}
        }}
        
        /* Accessibility improvements */
        .cta-button:focus,
        .login-link:focus {{
            outline: 3px solid rgba(255, 255, 255, 0.5);
            outline-offset: 2px;
        }}
        
        /* Skip to content link for screen readers */
        .skip-link {{
            position: absolute;
            top: -40px;
            left: 6px;
            background: #000;
            color: #fff;
            padding: 8px;
            text-decoration: none;
            z-index: 1000;
        }}
        
        .skip-link:focus {{
            top: 6px;
        }}
    </style>
</head>
<body>
    <a href="#main-content" class="skip-link">Skip to main content</a>
    
    <div class="hero">
        <a href="/login" class="login-link">Login</a>
        <div class="container">
            <h1>{app_name}</h1>
            <p>AI-Powered Accessibility for the Fediverse</p>
            <p>Make your social media content accessible with automated alt text generation</p>
            <a href="/register" class="cta-button">Get Started</a>
        </div>
    </div>
    
    <main id="main-content">
        <section class="features">
            <div class="container">
                <h2>Key Features</h2>
                
                <div class="feature-grid">
                    <div class="feature-card">
                        <h3>🤖 AI-Powered Descriptions</h3>
                        <p>Advanced machine learning generates contextual alt text for your images automatically.</p>
                    </div>
                    
                    <div class="feature-card">
                        <h3>👥 Human Review</h3>
                        <p>Review and edit AI-generated descriptions to ensure accuracy and quality.</p>
                    </div>
                    
                    <div class="feature-card">
                        <h3>🌐 ActivityPub Integration</h3>
                        <p>Works seamlessly with Mastodon, Pixelfed, and other Fediverse platforms.</p>
                    </div>
                </div>
                
                <div style="text-align: center; margin-top: 3rem;">
                    <a href="/register" class="cta-button">Create Your Account</a>
                </div>
            </div>
        </section>
    </main>
    
    <script>
        // Basic error reporting for debugging
        window.addEventListener('error', function(e) {{
            console.error('Fallback page error:', e.error);
        }});
        
        // Ensure buttons are accessible
        document.addEventListener('DOMContentLoaded', function() {{
            const buttons = document.querySelectorAll('.cta-button, .login-link');
            buttons.forEach(button => {{
                button.addEventListener('keydown', function(e) {{
                    if (e.key === 'Enter' || e.key === ' ') {{
                        e.preventDefault();
                        button.click();
                    }}
                }});
            }});
        }});
    </script>
</body>
</html>"""
        
        return fallback_html
        
    except Exception as e:
        logger.error(f"Failed to create fallback HTML: {e}")
        # Ultra-minimal fallback if even the fallback fails
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vedfolnir - Service Temporarily Unavailable</title>
</head>
<body style="font-family: sans-serif; text-align: center; padding: 2rem; background-color: #f8f9fa;">
    <h1 style="color: #dc3545;">Service Temporarily Unavailable</h1>
    <p>We're experiencing technical difficulties. Please try again later.</p>
    <p><a href="/login" style="color: #0d6efd;">Login</a> | <a href="/register" style="color: #0d6efd;">Register</a></p>
</body>
</html>"""

def handle_template_rendering_error(template_name: str, error: Exception, 
                                  template_context: Optional[Dict[str, Any]] = None) -> Response:
    """
    Handle template rendering errors with graceful fallback.
    
    Args:
        template_name: Name of the template that failed to render
        error: The rendering error that occurred
        template_context: Context that was passed to the template
    
    Returns:
        Flask Response with fallback content
    """
    try:
        # Log the template rendering error
        error_context = {
            'template_name': template_name,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'template_context_keys': list(template_context.keys()) if template_context else [],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        logger.error(f"Template rendering failed: {json.dumps(error_context, indent=2)}")
        
        # Create template rendering error
        template_error = TemplateRenderingError(
            template_name=template_name,
            message=str(error),
            template_context=template_context,
            original_exception=error
        )
        
        # For landing page template, use fallback HTML
        if template_name == 'landing.html':
            fallback_html = create_fallback_landing_html(error_context)
            response = make_response(fallback_html)
            response.status_code = 200
            response.headers['Content-Type'] = 'text/html; charset=utf-8'
            response.headers['X-Fallback-Mode'] = 'template-error'
            return response
        
        # For other templates, try to render a generic error page
        try:
            from flask import render_template
            return make_response(render_template('500.html', error=template_error), 500)
        except Exception:
            # If even error template fails, use minimal HTML
            error_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Template Error</title>
</head>
<body style="font-family: sans-serif; text-align: center; padding: 2rem;">
    <h1>Template Error</h1>
    <p>We're experiencing technical difficulties with the page template.</p>
    <p><a href="/">Return to Home</a></p>
</body>
</html>"""
            response = make_response(error_html)
            response.status_code = 500
            response.headers['Content-Type'] = 'text/html; charset=utf-8'
            response.headers['X-Fallback-Mode'] = 'template-error-minimal'
            return response
            
    except Exception as fallback_error:
        logger.error(f"Fallback template handling failed: {fallback_error}")
        # Ultra-minimal response if everything fails
        response = make_response("Service temporarily unavailable. Please try again later.")
        response.status_code = 500
        response.headers['Content-Type'] = 'text/plain; charset=utf-8'
        response.headers['X-Fallback-Mode'] = 'ultra-minimal'
        return response

def handle_session_detection_error(error: Exception, 
                                 session_context: Optional[Dict[str, Any]] = None) -> bool:
    """
    Handle session detection errors with safe fallback.
    
    Args:
        error: The session detection error
        session_context: Context about the session detection attempt
    
    Returns:
        Safe boolean indicating whether to treat as having previous session
    """
    try:
        # Log session detection error
        error_context = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'session_context': session_context or {},
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        logger.warning(f"Session detection error: {json.dumps(error_context, indent=2)}")
        
        # Create session detection error
        session_error = SessionDetectionError(
            message=str(error),
            session_indicators=session_context,
            original_exception=error
        )
        
        # Safe fallback: assume no previous session to avoid redirect loops
        # This ensures new users can always access the landing page
        logger.info("Session detection failed, defaulting to no previous session for safety")
        return False
        
    except Exception as fallback_error:
        logger.error(f"Session detection error handling failed: {fallback_error}")
        # Ultra-safe fallback
        return False

def handle_authentication_error(error: Exception, 
                              user_context: Optional[Dict[str, Any]] = None) -> Tuple[str, int]:
    """
    Handle authentication errors with appropriate response.
    
    Args:
        error: The authentication error
        user_context: Context about the user/authentication attempt
    
    Returns:
        Tuple of (response_content, status_code)
    """
    try:
        # Log the authentication error
        log_authentication_failure(error, user_context)
        
        # Create authentication error
        auth_error = AuthenticationFailureError(
            message=str(error),
            user_info=user_context,
            original_exception=error
        )
        
        # For authentication errors, redirect to landing page with error indication
        fallback_html = create_fallback_landing_html({
            'error_type': 'authentication_error',
            'error_message': 'Authentication system temporarily unavailable'
        })
        
        return fallback_html, 200
        
    except Exception as fallback_error:
        logger.error(f"Authentication error handling failed: {fallback_error}")
        return "Authentication system temporarily unavailable. Please try again later.", 503

def ensure_system_stability(func):
    """
    Decorator to ensure system stability under edge conditions.
    
    This decorator wraps route functions to provide comprehensive error
    handling and fallback mechanisms.
    """
    from functools import wraps
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Execute the original function
            return func(*args, **kwargs)
            
        except TemplateRenderingError as e:
            logger.error(f"Template rendering error in {func.__name__}: {e}")
            return handle_template_rendering_error(e.template_name, e.original_exception, e.template_context)
            
        except AuthenticationFailureError as e:
            logger.error(f"Authentication error in {func.__name__}: {e}")
            content, status_code = handle_authentication_error(e.original_exception, e.user_info)
            return make_response(content, status_code)
            
        except SessionDetectionError as e:
            logger.error(f"Session detection error in {func.__name__}: {e}")
            # For session detection errors, fall back to showing landing page
            fallback_html = create_fallback_landing_html({
                'error_type': 'session_detection_error',
                'error_message': 'Session detection temporarily unavailable'
            })
            return make_response(fallback_html, 200)
            
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            
            # For any other error, provide appropriate fallback
            if 'index' in func.__name__ or 'landing' in func.__name__:
                # Landing page route - use fallback HTML
                fallback_html = create_fallback_landing_html({
                    'error_type': 'system_error',
                    'error_message': 'System temporarily unavailable'
                })
                response = make_response(fallback_html, 200)
                response.headers['X-Fallback-Mode'] = 'system-error'
                return response
            else:
                # Other routes - return appropriate error response
                return make_response("Service temporarily unavailable. Please try again later.", 503)
    
    return wrapper

def test_error_scenarios() -> Dict[str, Any]:
    """
    Test various error scenarios and recovery mechanisms.
    
    This function can be used to verify that error handling works correctly
    under different failure conditions.
    
    Returns:
        Dictionary with test results
    """
    test_results = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'tests': {}
    }
    
    try:
        # Test 1: Fallback HTML generation
        try:
            fallback_html = create_fallback_landing_html({'test': 'fallback_generation'})
            test_results['tests']['fallback_html_generation'] = {
                'status': 'pass',
                'html_length': len(fallback_html),
                'contains_title': 'Vedfolnir' in fallback_html,
                'contains_cta': 'Get Started' in fallback_html
            }
        except Exception as e:
            test_results['tests']['fallback_html_generation'] = {
                'status': 'fail',
                'error': str(e)
            }
        
        # Test 2: Authentication error logging
        try:
            test_error = Exception("Test authentication error")
            log_authentication_failure(test_error, {'test_user': 'test_context'})
            test_results['tests']['authentication_error_logging'] = {
                'status': 'pass',
                'message': 'Authentication error logging completed without exceptions'
            }
        except Exception as e:
            test_results['tests']['authentication_error_logging'] = {
                'status': 'fail',
                'error': str(e)
            }
        
        # Test 3: Session detection error handling
        try:
            test_error = Exception("Test session detection error")
            result = handle_session_detection_error(test_error, {'test_session': 'test_data'})
            test_results['tests']['session_detection_error_handling'] = {
                'status': 'pass',
                'fallback_result': result,
                'expected_false': result is False
            }
        except Exception as e:
            test_results['tests']['session_detection_error_handling'] = {
                'status': 'fail',
                'error': str(e)
            }
        
        # Test 4: Template rendering error handling
        try:
            test_error = Exception("Test template rendering error")
            response = handle_template_rendering_error('landing.html', test_error, {'test': 'context'})
            test_results['tests']['template_rendering_error_handling'] = {
                'status': 'pass',
                'response_type': type(response).__name__,
                'has_fallback_header': 'X-Fallback-Mode' in response.headers
            }
        except Exception as e:
            test_results['tests']['template_rendering_error_handling'] = {
                'status': 'fail',
                'error': str(e)
            }
        
        # Calculate overall test status
        passed_tests = sum(1 for test in test_results['tests'].values() if test.get('status') == 'pass')
        total_tests = len(test_results['tests'])
        test_results['summary'] = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': total_tests - passed_tests,
            'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0
        }
        
        logger.info(f"Error scenario testing completed: {test_results['summary']}")
        
    except Exception as e:
        logger.error(f"Error scenario testing failed: {e}")
        test_results['error'] = str(e)
    
    return test_results