"""
Example of how to use the new middleware in your Django WAF project
"""

# =============================================================================
# 1. BASIC USAGE - Add to settings.py
# =============================================================================

"""
# In your settings.py file:

MIDDLEWARE = [
    # Django built-in middleware first
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    
    # Your custom WAF middleware
    'site_mangement.request_id_middleware.RequestIDMiddleware',        # Add request IDs
    'site_mangement.rate_limiting_middleware.RateLimitMiddleware',     # Rate limiting
    'site_mangement.request_logging_middleware.RequestLoggingMiddleware', # Request logging
    'site_mangement.security_headers_middleware.SecurityHeadersMiddleware', # Security headers
    'site_mangement.middleware.AnalyticsMiddleware',                   # Your existing analytics
    'site_mangement.waf_middleware.WAFMiddleware',                     # Your existing WAF
    'site_mangement.proxy_middleware.ProxyMiddleware',                 # Your existing proxy
]

# Middleware configuration
WAF_LOG_HEADERS = True
WAF_LOG_BODY = False
WAF_SENSITIVE_HEADERS = ['authorization', 'cookie', 'x-api-key', 'x-auth-token']
REQUEST_ID_HEADER = 'X-Request-ID'
RESPONSE_ID_HEADER = 'X-Request-ID'
"""


# =============================================================================
# 2. FUNCTION-BASED MIDDLEWARE EXAMPLE
# =============================================================================

def simple_logging_middleware(get_response):
    """
    Simple function-based middleware that logs all requests
    """
    import logging
    logger = logging.getLogger('waf.simple_logging')
    
    def middleware(request):
        # Log request
        logger.info(f"Request: {request.method} {request.path} from {request.META.get('REMOTE_ADDR')}")
        
        # Process request
        response = get_response(request)
        
        # Log response
        logger.info(f"Response: {response.status_code}")
        
        return response
    
    return middleware


# =============================================================================
# 3. CLASS-BASED MIDDLEWARE WITH CONFIGURATION
# =============================================================================

class ConfigurableMiddleware:
    """
    Example of configurable middleware using Django settings
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Get configuration from Django settings
        from django.conf import settings
        self.enabled = getattr(settings, 'CUSTOM_MIDDLEWARE_ENABLED', True)
        self.log_level = getattr(settings, 'CUSTOM_MIDDLEWARE_LOG_LEVEL', 'INFO')
        self.skip_paths = getattr(settings, 'CUSTOM_MIDDLEWARE_SKIP_PATHS', ['/admin/', '/static/'])
    
    def __call__(self, request):
        if not self.enabled:
            return self.get_response(request)
        
        if self._should_skip(request):
            return self.get_response(request)
        
        # Your middleware logic here
        response = self.get_response(request)
        
        return response
    
    def _should_skip(self, request):
        """Check if request should be skipped"""
        return any(request.path.startswith(path) for path in self.skip_paths)


# =============================================================================
# 4. MIDDLEWARE WITH DATABASE INTEGRATION
# =============================================================================

class DatabaseLoggingMiddleware:
    """
    Middleware that logs requests to database
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Log request to database
        self._log_request(request)
        
        response = self.get_response(request)
        
        # Update log with response
        self._log_response(request, response)
        
        return response
    
    def _log_request(self, request):
        """Log request to database"""
        try:
            from .models import RequestLog  # Your model
            
            RequestLog.objects.create(
                method=request.method,
                path=request.path,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                timestamp=timezone.now(),
            )
        except Exception as e:
            # Don't break the request if logging fails
            print(f"Database logging error: {e}")
    
    def _log_response(self, request, response):
        """Update log with response information"""
        try:
            from .models import RequestLog
            
            # Find the most recent log for this request
            log = RequestLog.objects.filter(
                method=request.method,
                path=request.path,
                ip_address=self._get_client_ip(request)
            ).order_by('-timestamp').first()
            
            if log:
                log.status_code = response.status_code
                log.response_time = getattr(request, '_response_time', 0)
                log.save()
        except Exception as e:
            print(f"Response logging error: {e}")
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '127.0.0.1')


# =============================================================================
# 5. MIDDLEWARE WITH CACHING
# =============================================================================

class CacheMiddleware:
    """
    Middleware that implements simple caching
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.cache_timeout = 300  # 5 minutes
    
    def __call__(self, request):
        # Only cache GET requests
        if request.method != 'GET':
            return self.get_response(request)
        
        # Check cache
        cache_key = self._get_cache_key(request)
        cached_response = cache.get(cache_key)
        
        if cached_response:
            return cached_response
        
        # Process request
        response = self.get_response(request)
        
        # Cache successful responses
        if response.status_code == 200:
            cache.set(cache_key, response, self.cache_timeout)
        
        return response
    
    def _get_cache_key(self, request):
        """Generate cache key for request"""
        return f"cache:{request.method}:{request.path}:{hash(str(request.GET))}"


# =============================================================================
# 6. MIDDLEWARE TESTING
# =============================================================================

"""
# Example of testing middleware

from django.test import RequestFactory, TestCase
from django.http import HttpResponse

class TestMiddleware(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = YourMiddleware(lambda req: HttpResponse("OK"))
    
    def test_middleware_processing(self):
        request = self.factory.get('/test/')
        response = self.middleware(request)
        
        self.assertEqual(response.status_code, 200)
        # Add more assertions as needed
"""


# =============================================================================
# 7. MIDDLEWARE DEBUGGING
# =============================================================================

class DebugMiddleware:
    """
    Debug middleware for development
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.request_count = 0
    
    def __call__(self, request):
        self.request_count += 1
        
        # Add debug information
        request._debug = {
            'request_number': self.request_count,
            'middleware_stack': self._get_middleware_stack(),
            'start_time': time.time(),
        }
        
        print(f"DEBUG: Request #{self.request_count} - {request.method} {request.path}")
        
        response = self.get_response(request)
        
        # Add debug headers
        response['X-Debug-Request-Number'] = str(self.request_count)
        response['X-Debug-Processing-Time'] = str(time.time() - request._debug['start_time'])
        
        return response
    
    def _get_middleware_stack(self):
        """Get current middleware stack for debugging"""
        # This would need to be implemented based on your needs
        return "Middleware stack info"


# =============================================================================
# 8. MIDDLEWARE ORDER MATTERS!
# =============================================================================

"""
IMPORTANT: Middleware order is crucial!

Good order:
1. Security (HTTPS redirects, etc.)
2. Sessions (needs to run early)
3. Common (URL rewriting, etc.)
4. CSRF (needs sessions)
5. Authentication (needs sessions)
6. Messages (needs authentication)
7. Your custom middleware (in logical order)
8. View middleware (runs closest to views)

Bad order example:
- Authentication before Sessions (won't work)
- CSRF before Sessions (won't work)
- Your WAF after Proxy (defeats the purpose)
"""