"""
Security Headers Middleware
Adds security headers to all responses for enhanced security
"""

import logging

logger = logging.getLogger('waf.security_headers')

def security_headers_middleware(get_response):
    """Function-based security headers middleware"""

    def middleware(request):
        response = get_response(request)

        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        # response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['X-WAF-Protected'] = 'true'

        # Add HSTS for HTTPS
        if request.is_secure():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        return response

    return middleware
