"""
Security Headers Middleware
Adds security headers to all responses for enhanced security
"""
from django.http import HttpResponse
from django.conf import settings
import logging

logger = logging.getLogger('waf.security_headers')


class SecurityHeadersMiddleware:
    """
    Adds security headers to all responses
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Default security headers
        self.security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
        }
        
        # CSP header (can be customized)
        self.csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        
        # HSTS header (only for HTTPS)
        self.hsts_max_age = 31536000  # 1 year
        self.hsts_include_subdomains = True
        self.hsts_preload = True
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Add security headers
        self._add_security_headers(request, response)
        
        return response
    
    def _add_security_headers(self, request, response):
        """Add security headers to response"""
        
        # Add basic security headers
        for header, value in self.security_headers.items():
            if header not in response:
                response[header] = value
        
        # Add Content Security Policy
        if 'Content-Security-Policy' not in response:
            response['Content-Security-Policy'] = self.csp_policy
        
        # Add HSTS header for HTTPS requests
        if request.is_secure():
            hsts_value = f"max-age={self.hsts_max_age}"
            if self.hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            if self.hsts_preload:
                hsts_value += "; preload"
            
            response['Strict-Transport-Security'] = hsts_value
        
        # Add custom security headers based on request
        self._add_custom_headers(request, response)
    
    def _add_custom_headers(self, request, response):
        """Add custom security headers based on request context"""
        
        # Add X-WAF-Protected header
        response['X-WAF-Protected'] = 'true'
        
        # Add X-Request-ID for tracking
        if hasattr(request, '_request_id'):
            response['X-Request-ID'] = request._request_id
        
        # Add server information (be careful in production)
        if settings.DEBUG:
            response['X-Server'] = 'Django-WAF'
            response['X-Debug'] = 'true'


# Function-based version
def security_headers_middleware(get_response):
    """Function-based security headers middleware"""
    
    def middleware(request):
        response = get_response(request)
        
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['X-WAF-Protected'] = 'true'
        
        # Add HSTS for HTTPS
        if request.is_secure():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response
    
    return middleware


# Advanced security middleware with configurable policies
class AdvancedSecurityMiddleware:
    """
    Advanced security middleware with configurable policies per site
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('waf.security')
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Get site-specific security policy
        site = getattr(request, '_waf_site', None)
        if site:
            self._apply_site_security_policy(request, response, site)
        else:
            self._apply_default_security_policy(request, response)
        
        return response
    
    def _apply_site_security_policy(self, request, response, site):
        """Apply site-specific security policy"""
        
        # Get security policy from site configuration
        security_config = getattr(site, 'security_config', {})
        
        # Apply CSP based on site configuration
        csp_policy = security_config.get('csp_policy', self._get_default_csp())
        response['Content-Security-Policy'] = csp_policy
        
        # Apply frame options based on site needs
        frame_options = security_config.get('frame_options', 'DENY')
        response['X-Frame-Options'] = frame_options
        
        # Add site-specific headers
        response['X-WAF-Site'] = site.host
        response['X-Security-Level'] = getattr(site, 'security_level', 'standard')
    
    def _apply_default_security_policy(self, request, response):
        """Apply default security policy"""
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
    
    def _get_default_csp(self):
        """Get default Content Security Policy"""
        return (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:;"
        )