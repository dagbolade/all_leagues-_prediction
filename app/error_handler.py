"""
Enhanced Error Handling Middleware

Provides comprehensive error handling, logging, and user-friendly error pages.
"""

from flask import render_template, jsonify, request
from werkzeug.exceptions import HTTPException
import logging
import traceback
from datetime import datetime
from typing import Tuple, Any

logger = logging.getLogger(__name__)


class ErrorHandler:
    """Centralized error handling for the application"""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize error handlers for Flask app"""
        
        # Register error handlers
        app.register_error_handler(400, self.handle_bad_request)
        app.register_error_handler(404, self.handle_not_found)
        app.register_error_handler(500, self.handle_internal_error)
        app.register_error_handler(Exception, self.handle_exception)
        
        # Add before/after request handlers
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        
        logger.info("Error handler initialized")
    
    def before_request(self):
        """Log request details"""
        request.start_time = datetime.now()
        logger.debug(f"[Request] {request.method} {request.path}")
    
    def after_request(self, response):
        """Log response details"""
        if hasattr(request, 'start_time'):
            duration = (datetime.now() - request.start_time).total_seconds()
            logger.debug(f"[Response] {request.method} {request.path} - {response.status_code} ({duration:.3f}s)")
        return response
    
    def handle_bad_request(self, error):
        """Handle 400 Bad Request errors"""
        logger.warning(f"[400] Bad Request: {request.path} - {str(error)}")
        
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({
                'status': 'error',
                'error': 'Bad Request',
                'message': str(error),
                'code': 400
            }), 400
        
        return render_template('errors/400.html', error=error), 400
    
    def handle_not_found(self, error):
        """Handle 404 Not Found errors"""
        logger.warning(f"[404] Not Found: {request.path}")
        
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({
                'status': 'error',
                'error': 'Not Found',
                'message': f'The requested resource was not found',
                'code': 404
            }), 404
        
        return render_template('errors/404.html'), 404
    
    def handle_internal_error(self, error):
        """Handle 500 Internal Server errors"""
        logger.error(f"[500] Internal Error: {request.path}")
        logger.error(traceback.format_exc())
        
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({
                'status': 'error',
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred',
                'code': 500
            }), 500
        
        return render_template('errors/500.html'), 500
    
    def handle_exception(self, error):
        """Handle all unhandled exceptions"""
        # If it's an HTTP exception, let it be handled by specific handlers
        if isinstance(error, HTTPException):
            return error
        
        # Log the full error
        logger.error(f"[Exception] Unhandled exception on {request.path}")
        logger.error(f"Error type: {type(error).__name__}")
        logger.error(f"Error message: {str(error)}")
        logger.error(traceback.format_exc())
        
        # Return appropriate response
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({
                'status': 'error',
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred',
                'type': type(error).__name__,
                'code': 500
            }), 500
        
        return render_template('errors/500.html', error=error), 500


def create_error_handler(app):
    """Factory function to create and initialize error handler"""
    return ErrorHandler(app)


# Utility functions for error responses
def error_response(message: str, code: int = 400) -> Tuple[Any, int]:
    """Create a JSON error response"""
    return jsonify({
        'status': 'error',
        'message': message,
        'code': code,
        'timestamp': datetime.utcnow().isoformat()
    }), code


def success_response(data: Any = None, message: str = None) -> Tuple[Any, int]:
    """Create a JSON success response"""
    response = {
        'status': 'success',
        'timestamp': datetime.utcnow().isoformat()
    }
    
    if data is not None:
        response['data'] = data
    
    if message:
        response['message'] = message
    
    return jsonify(response), 200
