"""
Request Logging Middleware
Logs detailed request information for monitoring and debugging
"""
import json
import time
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
import logging

logger = logging.getLogger('waf.request_logging')


class RequestLoggingMiddleware:
    """
    Logs detailed request information including headers, body, and response
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('waf.request_logging')

        # Configure what to log
        self.log_headers = getattr(settings, 'WAF_LOG_HEADERS', True)
        self.log_body = getattr(settings, 'WAF_LOG_BODY', False)
        self.log_response = getattr(settings, 'WAF_LOG_RESPONSE', False)
        self.sensitive_headers = getattr(settings, 'WAF_SENSITIVE_HEADERS', [
            'authorization', 'cookie', 'x-api-key', 'x-auth-token'
        ])

    def __call__(self, request):
        # Skip logging for certain paths
        if self._should_skip_logging(request):
            return self.get_response(request)

        # Start timing
        start_time = time.time()

        # Log request
        self._log_request(request)

        # Process request
        response = self.get_response(request)

        # Calculate processing time
        processing_time = time.time() - start_time

        # Log response
        self._log_response(request, response, processing_time)

        return response

    def _should_skip_logging(self, request):
        """Determine if request should be skipped from logging"""
        skip_paths = ['/admin/', '/static/', '/media/', '/favicon.ico']
        return any(request.path.startswith(path) for path in skip_paths)

    def _log_request(self, request):
        """Log incoming request details"""
        log_data = {
            'type': 'request',
            'timestamp': time.time(),
            'method': request.method,
            'path': request.path,
            'full_url': request.build_absolute_uri(),
            'client_ip': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'referer': request.META.get('HTTP_REFERER', ''),
        }

        # Add headers if enabled
        if self.log_headers:
            log_data['headers'] = self._sanitize_headers(request.META)

        # Add body if enabled and not too large
        if self.log_body and request.method in ['POST', 'PUT', 'PATCH']:
            body = self._get_request_body(request)
            if body and len(body) < 10000:  # Limit body size
                log_data['body'] = body

        # Add query parameters
        if request.GET:
            log_data['query_params'] = dict(request.GET)

        self.logger.info(json.dumps(log_data, default=str))

    def _log_response(self, request, response, processing_time):
        """Log response details"""
        log_data = {
            'type': 'response',
            'timestamp': time.time(),
            'method': request.method,
            'path': request.path,
            'status_code': response.status_code,
            'processing_time': round(processing_time * 1000, 2),  # Convert to milliseconds
            'response_size': len(response.content) if hasattr(response, 'content') else 0,
        }

        # Add response headers if enabled
        if self.log_headers:
            log_data['response_headers'] = dict(response.items())

        # Add response body for errors if enabled
        if self.log_response and response.status_code >= 400:
            if hasattr(response, 'content'):
                content = response.content.decode('utf-8', errors='ignore')
                if len(content) < 5000:  # Limit response body size
                    log_data['response_body'] = content

        self.logger.info(json.dumps(log_data, default=str))

    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '127.0.0.1')

    def _sanitize_headers(self, meta):
        """Sanitize headers by removing sensitive information"""
        headers = {}
        for key, value in meta.items():
            if key.startswith('HTTP_'):
                header_name = key[5:].replace('_', '-').lower()
                if header_name not in self.sensitive_headers:
                    headers[header_name] = value
                else:
                    headers[header_name] = '[REDACTED]'
        return headers

    def _get_request_body(self, request):
        """Safely get request body"""
        try:
            body = request.body.decode('utf-8')
            # Try to parse as JSON for better formatting
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                return body
        except Exception:
            return '[BINARY DATA]'
