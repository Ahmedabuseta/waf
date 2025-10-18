"""
Middleware for capturing request analytics and geolocation
"""
import time
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from .models import Site, RequestAnalytics
from .utils import get_client_ip, geolocate_ip


class AnalyticsMiddleware(MiddlewareMixin):
    """
    Middleware to capture request analytics with geographic information
    """
    
    def process_request(self, request):
        """Store request start time"""
        request._analytics_start_time = time.time()
        return None
    
    def process_response(self, request, response):
        """
        Capture request details and store analytics
        """
        # Skip for admin, static files, and API endpoints
        if request.path.startswith('/admin/') or request.path.startswith('/static/') or request.path.startswith('/api/'):
            return response
        
        try:
            # Calculate response time
            start_time = getattr(request, '_analytics_start_time', None)
            if start_time:
                response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            else:
                response_time = 0
            
            # Get client IP
            ip_address = get_client_ip(request)
            
            # Get site (for now, use first site or None)
            # In production, you'd determine site based on request.get_host()
            site = Site.objects.first()
            
            if not site:
                return response
            
            # Geolocate IP
            geo_data = geolocate_ip(ip_address)
            
            # Determine action taken (this is simplified - you'd integrate with your WAF logic)
            action_taken = 'allowed' if response.status_code < 400 else 'blocked'
            threat_level = 'none'
            
            # Create analytics record
            RequestAnalytics.objects.create(
                site=site,
                ip_address=ip_address,
                country=geo_data.get('country'),
                country_code=geo_data.get('country_code'),
                city=geo_data.get('city'),
                region=geo_data.get('region'),
                latitude=geo_data.get('latitude'),
                longitude=geo_data.get('longitude'),
                request_method=request.method,
                request_url=request.build_absolute_uri(),
                request_path=request.path,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                referer=request.META.get('HTTP_REFERER', ''),
                status_code=response.status_code,
                response_time=response_time,
                action_taken=action_taken,
                threat_level=threat_level,
            )
            
        except Exception as e:
            # Log error but don't break the request
            print(f"Analytics middleware error: {e}")
        
        return response
