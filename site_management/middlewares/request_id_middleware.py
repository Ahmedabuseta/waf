"""
Request ID Middleware
Adds unique request ID to each request for tracking and debugging
"""
import uuid
import logging
from django.conf import settings

logger = logging.getLogger('waf.request_id')


class RequestIDMiddleware:
    """
    Adds unique request ID to each request for tracking
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.request_id_header = getattr(settings, 'REQUEST_ID_HEADER', 'X-Request-ID')
        self.response_id_header = getattr(settings, 'RESPONSE_ID_HEADER', 'X-Request-ID')

    def __call__(self, request):
        # Generate or extract request ID
        request_id = self._get_or_create_request_id(request)

        # Store in request for use by other middleware and views
        request._request_id = request_id

        # Add to logging context
        self._add_to_logging_context(request_id)

        response = self.get_response(request)

        # Add request ID to response headers
        response[self.response_id_header] = request_id

        return response

    def _get_or_create_request_id(self, request):
        """Get request ID from headers or create new one"""
        # Check if request ID is already in headers
        request_id = request.META.get(f'HTTP_{self.request_id_header.upper().replace("-", "_")}')

        if not request_id:
            # Generate new UUID
            request_id = str(uuid.uuid4())
            logger.debug(f"Generated new request ID: {request_id}")
        else:
            logger.debug(f"Using existing request ID: {request_id}")

        return request_id

    def _add_to_logging_context(self, request_id):
        """Add request ID to logging context"""
        # This can be used with structured logging
        extra = {'request_id': request_id}
        logger.info(f"Request started", extra=extra)
