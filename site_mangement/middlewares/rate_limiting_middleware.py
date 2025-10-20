"""
Rate Limiting Middleware for WAF
Implements rate limiting per IP address with configurable limits
"""
import time
from collections import defaultdict, deque
from django.http import HttpResponseTooManyRequests, JsonResponse
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger('waf.rate_limit')


class RateLimitMiddleware:
    """
    Rate limiting middleware using sliding window algorithm
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Rate limit configurations
        self.rate_limits = {
            'default': {'requests': 100, 'window': 60},  # 100 requests per minute
            'api': {'requests': 50, 'window': 60},       # 50 API requests per minute
            'login': {'requests': 5, 'window': 300},     # 5 login attempts per 5 minutes
        }
        self.ip_requests = defaultdict(lambda: deque())
    
    def __call__(self, request):
        # Determine rate limit type based on path
        rate_limit_type = self._get_rate_limit_type(request.path)
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Check rate limit
        if not self._is_allowed(client_ip, rate_limit_type):
            logger.warning(f"Rate limit exceeded for IP {client_ip} on {request.path}")
            return self._rate_limit_response(request)
        
        # Record this request
        self._record_request(client_ip, rate_limit_type)
        
        response = self.get_response(request)
        
        # Add rate limit headers to response
        self._add_rate_limit_headers(response, client_ip, rate_limit_type)
        
        return response
    
    def _get_rate_limit_type(self, path):
        """Determine rate limit type based on request path"""
        if path.startswith('/api/'):
            return 'api'
        elif path.startswith('/auth/login') or path.startswith('/login'):
            return 'login'
        else:
            return 'default'
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '127.0.0.1')
    
    def _is_allowed(self, client_ip, rate_limit_type):
        """Check if request is allowed based on rate limits"""
        config = self.rate_limits[rate_limit_type]
        now = time.time()
        window_start = now - config['window']
        
        # Clean old requests
        client_requests = self.ip_requests[client_ip]
        while client_requests and client_requests[0] < window_start:
            client_requests.popleft()
        
        # Check if under limit
        return len(client_requests) < config['requests']
    
    def _record_request(self, client_ip, rate_limit_type):
        """Record this request for rate limiting"""
        now = time.time()
        self.ip_requests[client_ip].append(now)
    
    def _rate_limit_response(self, request):
        """Return rate limit exceeded response"""
        if request.path.startswith('/api/'):
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'message': 'Too many requests. Please try again later.'
            }, status=429)
        else:
            return HttpResponseTooManyRequests(
                content="<h1>429 - Too Many Requests</h1><p>Rate limit exceeded. Please try again later.</p>",
                content_type="text/html"
            )
    
    def _add_rate_limit_headers(self, response, client_ip, rate_limit_type):
        """Add rate limit headers to response"""
        config = self.rate_limits[rate_limit_type]
        remaining = max(0, config['requests'] - len(self.ip_requests[client_ip]))
        
        response['X-RateLimit-Limit'] = str(config['requests'])
        response['X-RateLimit-Remaining'] = str(remaining)
        response['X-RateLimit-Reset'] = str(int(time.time() + config['window']))


# Alternative: Function-based middleware
def rate_limit_middleware(get_response):
    """Function-based rate limiting middleware"""
    # Initialize rate limiting data
    ip_requests = defaultdict(lambda: deque())
    rate_limits = {
        'default': {'requests': 100, 'window': 60},
        'api': {'requests': 50, 'window': 60},
        'login': {'requests': 5, 'window': 300},
    }
    
    def middleware(request):
        # Skip for admin and static files
        if request.path.startswith('/admin/') or request.path.startswith('/static/'):
            return get_response(request)
        
        # Rate limiting logic
        client_ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        rate_limit_type = 'api' if request.path.startswith('/api/') else 'default'
        
        config = rate_limits[rate_limit_type]
        now = time.time()
        window_start = now - config['window']
        
        # Clean old requests
        client_requests = ip_requests[client_ip]
        while client_requests and client_requests[0] < window_start:
            client_requests.popleft()
        
        # Check rate limit
        if len(client_requests) >= config['requests']:
            return HttpResponseTooManyRequests("Rate limit exceeded")
        
        # Record request
        client_requests.append(now)
        
        response = get_response(request)
        return response
    
    return middleware