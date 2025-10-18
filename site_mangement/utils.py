"""
Utility functions for site management and analytics
"""
import requests
from django.core.cache import cache


def get_client_ip(request):
    """
    Extract client IP address from request, handling proxies
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def geolocate_ip(ip_address):
    """
    Geolocate an IP address using free API service
    Returns dict with country, city, lat/lng, etc.
    
    Uses caching to avoid excessive API calls
    """
    # Check cache first (cache for 24 hours)
    cache_key = f'geo_{ip_address}'
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data
    
    # Skip geolocation for private/local IPs
    if ip_address in ['127.0.0.1', 'localhost'] or ip_address.startswith('192.168.') or ip_address.startswith('10.'):
        default_data = {
            'country': 'Local',
            'country_code': 'LO',
            'city': 'Localhost',
            'region': 'Local',
            'latitude': 0.0,
            'longitude': 0.0,
        }
        cache.set(cache_key, default_data, 86400)  # Cache for 24 hours
        return default_data
    
    try:
        # Use ip-api.com (free, no API key required, 45 requests/minute limit)
        import httpx
        response = httpx.get(
            f'http://ip-api.com/json/{ip_address}',
            timeout=2
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status') == 'success':
                geo_data = {
                    'country': data.get('country'),
                    'country_code': data.get('countryCode'),
                    'city': data.get('city'),
                    'region': data.get('regionName'),
                    'latitude': data.get('lat'),
                    'longitude': data.get('lon'),
                }
                
                # Cache the result
                cache.set(cache_key, geo_data, 86400)  # Cache for 24 hours
                return geo_data
    
    except Exception as e:
        print(f"Geolocation error for {ip_address}: {e}")
    
    # Return default values if geolocation fails
    default_data = {
        'country': None,
        'country_code': None,
        'city': None,
        'region': None,
        'latitude': None,
        'longitude': None,
    }
    return default_data
