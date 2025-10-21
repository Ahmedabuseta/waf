import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class CSRFDebugMiddleware(MiddlewareMixin):
    """
    Middleware to debug CSRF issues
    Only enabled in DEBUG mode
    """
    
    def process_request(self, request):
        if not hasattr(request, 'META'):
            return
        
        # Log CSRF-related information for debugging
        csrf_cookie = request.META.get('HTTP_COOKIE', '')
        csrf_token = request.POST.get('csrfmiddlewaretoken', '')
        
        # Only log for POST requests to avoid spam
        if request.method == 'POST':
            logger.debug(f"CSRF Debug - Path: {request.path}")
            logger.debug(f"CSRF Debug - Cookie: {csrf_cookie}")
            logger.debug(f"CSRF Debug - Token: {csrf_token}")
            logger.debug(f"CSRF Debug - Session: {request.session.session_key}")
            logger.debug(f"CSRF Debug - User: {request.user}")
    
    def process_response(self, request, response):
        # Log CSRF cookie setting
        if hasattr(response, 'cookies') and 'csrftoken' in response.cookies:
            logger.debug(f"CSRF Debug - Setting CSRF cookie: {response.cookies['csrftoken']}")
        
        return response