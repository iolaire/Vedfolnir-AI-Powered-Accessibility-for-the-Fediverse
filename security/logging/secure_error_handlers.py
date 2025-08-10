# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Secure Error Handlers

Provides secure error handling that doesn't leak sensitive information.
"""

from flask import render_template, jsonify, request
import logging

logger = logging.getLogger(__name__)

def register_secure_error_handlers(app):
    """Register secure error handlers with the Flask app"""
    
    @app.errorhandler(400)
    def bad_request(error):
        """Handle bad request errors securely"""
        logger.warning(f"Bad request from {request.remote_addr}: {request.path}")
        
        if request.is_json:
            return jsonify({
                'error': 'Bad Request',
                'message': 'The request could not be understood by the server.'
            }), 400
        
        return render_template('errors/400.html'), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        """Handle unauthorized errors securely"""
        logger.warning(f"Unauthorized access attempt from {request.remote_addr}: {request.path}")
        
        if request.is_json:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Authentication required.'
            }), 401
        
        return render_template('errors/401.html'), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        """Handle forbidden errors securely"""
        logger.warning(f"Forbidden access attempt from {request.remote_addr}: {request.path}")
        
        if request.is_json:
            return jsonify({
                'error': 'Forbidden',
                'message': 'You do not have permission to access this resource.'
            }), 403
        
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle not found errors securely"""
        logger.info(f"404 error from {request.remote_addr}: {request.path}")
        
        if request.is_json:
            return jsonify({
                'error': 'Not Found',
                'message': 'The requested resource was not found.'
            }), 404
        
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        """Handle rate limit errors securely"""
        logger.warning(f"Rate limit exceeded from {request.remote_addr}: {request.path}")
        
        if request.is_json:
            return jsonify({
                'error': 'Rate Limit Exceeded',
                'message': 'Too many requests. Please try again later.'
            }), 429
        
        return render_template('errors/429.html'), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle internal server errors securely"""
        logger.error(f"Internal server error from {request.remote_addr}: {request.path}")
        
        if request.is_json:
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'An internal server error occurred.'
            }), 500
        
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle unexpected exceptions securely"""
        logger.exception(f"Unhandled exception from {request.remote_addr}: {request.path}")
        
        if request.is_json:
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred.'
            }), 500
        
        return render_template('errors/500.html'), 500
