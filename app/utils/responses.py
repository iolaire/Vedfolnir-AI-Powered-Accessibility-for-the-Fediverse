from flask import jsonify

def success_response(data=None, message=None):
    """Standard success response format"""
    response = {'success': True}
    if data is not None:
        response['data'] = data
    if message:
        response['message'] = message
    return jsonify(response)

def error_response(error, status_code=400):
    """Standard error response format"""
    return jsonify({'success': False, 'error': str(error)}), status_code

def api_success(data=None, message=None, status_code=200):
    """API success response with status code"""
    response = success_response(data, message)
    return response, status_code

def api_error(error, status_code=400):
    """API error response"""
    return error_response(error, status_code)
