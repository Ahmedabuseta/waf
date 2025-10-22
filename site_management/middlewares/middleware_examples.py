"""
Comprehensive Middleware Examples for WAF Project
Shows both new and old style middleware implementations
"""

# =============================================================================
# 1. NEW STYLE MIDDLEWARE (Django 1.10+) - RECOMMENDED
# =============================================================================

def new_style_middleware_example(get_response):
    """
    Example of new style function-based middleware
    This is the recommended approach for Django 1.10+
    """
    # One-time initialization code
    print("Middleware initialized once")

    def middleware(request):
        # Code executed for each request BEFORE the view
        print(f"Processing request: {request.method} {request.path}")

        # Call the next middleware/view
        response = get_response(request)

        # Code executed for each request AFTER the view
        print(f"Response status: {response.status_code}")

        return response

    return middleware


class NewStyleClassMiddleware:
    """
    Example of new style class-based middleware
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # One-time initialization
        print("Class middleware initialized")

    def __call__(self, request):
        # Code executed for each request BEFORE the view
        print(f"Class middleware processing: {request.path}")

        response = self.get_response(request)

        # Code executed for each request AFTER the view
        print(f"Class middleware response: {response.status_code}")

        return response


# =============================================================================
# 2. OLD STYLE MIDDLEWARE (Django < 1.10) - FOR COMPATIBILITY
# =============================================================================

from django.utils.deprecation import MiddlewareMixin

class OldStyleMiddleware(MiddlewareMixin):
    """
    Example of old style middleware using MiddlewareMixin
    This works with both old and new Django versions
    """

    def process_request(self, request):
        """Called during request phase"""
        print(f"Old style - Processing request: {request.path}")
        return None  # Continue processing

    def process_response(self, request, response):
        """Called during response phase"""
        print(f"Old style - Response status: {response.status_code}")
        return response


# =============================================================================
# 3. PRACTICAL WAF MIDDLEWARE EXAMPLES
# =============================================================================

import time
import json
from django.http import JsonResponse, HttpResponseForbidden
from django.core.cache import cache

class IPWhitelistMiddleware:
    """
    IP Whitelist Middleware - blocks requests from non-whitelisted IPs
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.whitelist_key = 'waf:ip_whitelist'
        self.cache_timeout = 300  # 5 minutes

    def __call__(self, request):
        client_ip = self._get_client_ip(request)

        # Skip for admin and static files
        if self._should_skip(request):
            return self.get_response(request)

        # Check IP whitelist
        if not self._is_ip_whitelisted(client_ip):
            return self._block_request(request, client_ip)

        response = self.get_response(request)
        return response

    def _should_skip(self, request):
        """Skip whitelist check for certain paths"""
        skip_paths = ['/admin/', '/static/', '/media/']
        return any(request.path.startswith(path) for path in skip_paths)

    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '127.0.0.1')

    def _is_ip_whitelisted(self, client_ip):
        """Check if IP is in whitelist"""
        # Get whitelist from cache or database
        whitelist = cache.get(self.whitelist_key, [])

        # Add localhost for development
        if client_ip in ['127.0.0.1', '::1', 'localhost']:
            return True

        return client_ip in whitelist

    def _block_request(self, request, client_ip):
        """Block the request"""
        if request.path.startswith('/api/'):
            return JsonResponse({
                'error': 'Access denied',
                'message': 'Your IP address is not whitelisted'
            }, status=403)
        else:
            return HttpResponseForbidden(
                f"<h1>403 - Access Denied</h1><p>IP {client_ip} is not whitelisted</p>"
            )


class RequestSizeLimitMiddleware:
    """
    Request Size Limit Middleware - limits request body size
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.max_size = 10 * 1024 * 1024  # 10MB default
        self.max_size_api = 1024 * 1024   # 1MB for API

    def __call__(self, request):
        # Check request size
        content_length = request.META.get('CONTENT_LENGTH')
        if content_length:
            try:
                content_length = int(content_length)
                max_size = self._get_max_size(request)

                if content_length > max_size:
                    return self._size_limit_response(request, content_length, max_size)
            except ValueError:
                pass  # Invalid content length, let it through

        response = self.get_response(request)
        return response

    def _get_max_size(self, request):
        """Get maximum allowed size for this request"""
        if request.path.startswith('/api/'):
            return self.max_size_api
        return self.max_size

    def _size_limit_response(self, request, actual_size, max_size):
        """Return size limit exceeded response"""
        if request.path.startswith('/api/'):
            return JsonResponse({
                'error': 'Request too large',
                'message': f'Request size {actual_size} exceeds limit of {max_size} bytes'
            }, status=413)
        else:
            return HttpResponseForbidden(
                f"<h1>413 - Request Too Large</h1>"
                f"<p>Request size {actual_size} bytes exceeds limit of {max_size} bytes</p>"
            )


class MaintenanceModeMiddleware:
    """
    Maintenance Mode Middleware - shows maintenance page when enabled
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.maintenance_key = 'waf:maintenance_mode'
        self.allowed_ips = ['127.0.0.1', '::1']  # IPs that can bypass maintenance

    def __call__(self, request):
        # Check if maintenance mode is enabled
        if self._is_maintenance_mode():
            if not self._can_bypass_maintenance(request):
                return self._maintenance_response(request)

        response = self.get_response(request)
        return response

    def _is_maintenance_mode(self):
        """Check if maintenance mode is enabled"""
        return cache.get(self.maintenance_key, False)

    def _can_bypass_maintenance(self, request):
        """Check if request can bypass maintenance mode"""
        client_ip = self._get_client_ip(request)

        # Allow admin users
        if hasattr(request, 'user') and request.user.is_authenticated and request.user.is_staff:
            return True

        # Allow whitelisted IPs
        if client_ip in self.allowed_ips:
            return True

        return False

    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '127.0.0.1')

    def _maintenance_response(self, request):
        """Return maintenance mode response"""
        if request.path.startswith('/api/'):
            return JsonResponse({
                'error': 'Maintenance mode',
                'message': 'The service is temporarily unavailable for maintenance'
            }, status=503)
        else:
            return HttpResponseForbidden(
                "<h1>503 - Service Temporarily Unavailable</h1>"
                "<p>We're currently performing maintenance. Please try again later.</p>"
            )


# =============================================================================
# 4. MIDDLEWARE STACK CONFIGURATION EXAMPLE
# =============================================================================

"""
Example Django settings.py configuration for middleware stack:

MIDDLEWARE = [
    # Django built-in middleware
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',

    # Custom WAF middleware (in order)
    'site_management.middleware_examples.RequestIDMiddleware',           # Add request IDs
    'site_management.middleware_examples.RequestLoggingMiddleware',      # Log requests
    'site_management.middleware_examples.IPWhitelistMiddleware',         # IP filtering
    'site_management.middleware_examples.RequestSizeLimitMiddleware',    # Size limits
    'site_management.middleware_examples.MaintenanceModeMiddleware',     # Maintenance mode
    'site_management.middleware.AnalyticsMiddleware',                    # Analytics
    'site_management.waf_middleware.WAFMiddleware',                      # WAF rules
    'site_management.proxy_middleware.ProxyMiddleware',                  # Proxy forwarding
    'site_management.middleware_examples.SecurityHeadersMiddleware',     # Security headers
]

# Middleware-specific settings
WAF_LOG_HEADERS = True
WAF_LOG_BODY = False
WAF_SENSITIVE_HEADERS = ['authorization', 'cookie', 'x-api-key']
REQUEST_ID_HEADER = 'X-Request-ID'
RESPONSE_ID_HEADER = 'X-Request-ID'
"""


# =============================================================================
# 5. TESTING MIDDLEWARE
# =============================================================================

class TestMiddleware:
    """
    Simple test middleware for development
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.request_count = 0

    def __call__(self, request):
        self.request_count += 1

        # Add debug information to request
        request._debug_info = {
            'request_number': self.request_count,
            'timestamp': time.time(),
            'path': request.path,
            'method': request.method,
        }

        print(f"Test Middleware - Request #{self.request_count}: {request.method} {request.path}")

        response = self.get_response(request)

        # Add debug information to response
        response['X-Debug-Request-Count'] = str(self.request_count)
        response['X-Debug-Processing-Time'] = str(time.time() - request._debug_info['timestamp'])

        return response
