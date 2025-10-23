"""
IP Utility Functions for WAF System
Provides client IP detection and geolocation functionality
"""
import requests
from typing import Optional, Dict, Tuple
from django.core.cache import cache
import logging

logger = logging.getLogger('waf.utils')


def get_client_ip(request) -> str:
    """
    Get the real client IP address from the request

    Checks various headers in order of priority:
    1. X-Forwarded-For (proxy/load balancer)
    2. X-Real-IP (nginx)
    3. HTTP_X_FORWARDED_FOR (alternative)
    4. REMOTE_ADDR (direct connection)

    Args:
        request: Django HttpRequest object

    Returns:
        str: Client IP address
    """
    # Check X-Forwarded-For header (most common with proxies)
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # X-Forwarded-For can contain multiple IPs, get the first one
        ip = x_forwarded_for.split(',')[0].strip()
        return ip

    # Check X-Real-IP header (nginx)
    x_real_ip = request.META.get('HTTP_X_REAL_IP')
    if x_real_ip:
        return x_real_ip.strip()

    # Check alternative X-Forwarded-For format
    http_x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if http_x_forwarded_for:
        ip = http_x_forwarded_for.split(',')[0].strip()
        return ip

    # Fallback to REMOTE_ADDR (direct connection)
    remote_addr = request.META.get('REMOTE_ADDR', '0.0.0.0')
    return remote_addr


def geolocate_ip(ip_address: str, use_cache: bool = True) -> Dict[str, Optional[str]]:
    """
    Get geolocation information for an IP address using ipapi.co

    Args:
        ip_address: IP address to geolocate
        use_cache: Whether to use cached results (default: True)

    Returns:
        dict: Geolocation information with keys:
            - country: Country name
            - country_code: 2-letter country code
            - city: City name
            - region: Region/state name
            - latitude: Latitude coordinate
            - longitude: Longitude coordinate
            - error: Error message if lookup failed
    """
    # Default response structure
    default_response = {
        'country': None,
        'country_code': None,
        'city': None,
        'region': None,
        'latitude': None,
        'longitude': None,
        'error': None
    }

    # Skip private/local IPs
    if is_private_ip(ip_address):
        return {
            **default_response,
            'country': 'Local',
            'country_code': 'XX',
            'city': 'Local',
            'error': 'Private IP address'
        }

    # Check cache first
    if use_cache:
        cache_key = f'geoip_{ip_address}'
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result

    try:
        # Use ipapi.co free API (no key required, 1000 requests/day)
        response = requests.get(
            f'https://ipapi.co/{ip_address}/json/',
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()

            # Check for API error
            if 'error' in data and data['error']:
                logger.warning(f"Geolocation API error for {ip_address}: {data.get('reason', 'Unknown')}")
                return {
                    **default_response,
                    'error': data.get('reason', 'API error')
                }

            result = {
                'country': data.get('country_name'),
                'country_code': data.get('country_code'),
                'city': data.get('city'),
                'region': data.get('region'),
                'latitude': data.get('latitude'),
                'longitude': data.get('longitude'),
                'error': None
            }

            # Cache successful result for 24 hours
            if use_cache:
                cache.set(cache_key, result, 86400)

            return result
        else:
            logger.warning(f"Geolocation API returned status {response.status_code} for {ip_address}")
            return {
                **default_response,
                'error': f'API returned status {response.status_code}'
            }

    except requests.Timeout:
        logger.error(f"Geolocation API timeout for {ip_address}")
        return {
            **default_response,
            'error': 'API timeout'
        }
    except requests.RequestException as e:
        logger.error(f"Geolocation API error for {ip_address}: {str(e)}")
        return {
            **default_response,
            'error': str(e)
        }
    except Exception as e:
        logger.error(f"Unexpected error geolocating {ip_address}: {str(e)}")
        return {
            **default_response,
            'error': str(e)
        }


def is_private_ip(ip_address: str) -> bool:
    """
    Check if an IP address is private/local

    Args:
        ip_address: IP address to check

    Returns:
        bool: True if IP is private, False otherwise
    """
    try:
        import ipaddress
        ip = ipaddress.ip_address(ip_address)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        # Invalid IP address
        return False


def get_ip_info(request) -> Tuple[str, Dict[str, Optional[str]]]:
    """
    Get client IP and geolocation information in one call

    Args:
        request: Django HttpRequest object

    Returns:
        tuple: (ip_address, geo_info)
    """
    ip_address = get_client_ip(request)
    geo_info = geolocate_ip(ip_address)
    return ip_address, geo_info


def validate_ip_address(ip_address: str) -> bool:
    """
    Validate if a string is a valid IP address (IPv4 or IPv6)

    Args:
        ip_address: String to validate

    Returns:
        bool: True if valid IP, False otherwise
    """
    try:
        import ipaddress
        ipaddress.ip_address(ip_address)
        return True
    except ValueError:
        return False


def is_ip_in_range(ip_address: str, ip_range: str) -> bool:
    """
    Check if an IP address is within a given IP range/network

    Args:
        ip_address: IP address to check
        ip_range: IP range in CIDR notation (e.g., '192.168.1.0/24')

    Returns:
        bool: True if IP is in range, False otherwise
    """
    try:
        import ipaddress
        ip = ipaddress.ip_address(ip_address)
        network = ipaddress.ip_network(ip_range, strict=False)
        return ip in network
    except ValueError:
        return False


def get_ip_version(ip_address: str) -> Optional[int]:
    """
    Get the IP version (4 or 6) of an IP address

    Args:
        ip_address: IP address to check

    Returns:
        int: 4 for IPv4, 6 for IPv6, None if invalid
    """
    try:
        import ipaddress
        ip = ipaddress.ip_address(ip_address)
        return ip.version
    except ValueError:
        return None


def normalize_ip(ip_address: str) -> Optional[str]:
    """
    Normalize an IP address to its canonical form

    Args:
        ip_address: IP address to normalize

    Returns:
        str: Normalized IP address, None if invalid
    """
    try:
        import ipaddress
        ip = ipaddress.ip_address(ip_address)
        return str(ip)
    except ValueError:
        return None


def geolocate_ip_ipwhois(ip_address: str) -> Dict[str, Optional[str]]:
    """
    Geolocate IP using ipwhois.app (free, no token needed)
    """
    default_response = {
        'country': None,
        'country_code': None,
        'city': None,
        'region': None,
        'latitude': None,
        'longitude': None,
        'isp': None,
        'org': None,
        'asn': None,
        'timezone': None,
        'error': None
    }

    # Handle private IPs
    if is_private_ip(ip_address):
        return {**default_response, 'country': 'Local', 'country_code': 'XX', 'city': 'Local'}

    url = f"https://ipwhois.app/json/{ip_address}"

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()  # Raises HTTPError for bad status
        data = response.json()

        # Check for API-level error
        if not data.get("success", True):
            error_msg = data.get("message", "Unknown error")
            return {**default_response, 'error': error_msg}

        # Parse `loc` field: "30.0444,31.2357"
        loc = data.get('loc', '')
        latitude = longitude = None
        if loc and ',' in loc:
            parts = loc.split(',', 1)
            try:
                latitude = float(parts[0].strip())
                longitude = float(parts[1].strip())
            except (ValueError, IndexError):
                pass  # Keep None if parsing fails

        result = {
            'country': str(data.get('country', 'Unknown')),
            'country_code': str(data.get('country_code', 'XX')).upper(),
            'city': str(data.get('city', 'Unknown')),
            'region': str(data.get('region', 'Unknown')),
            'latitude': latitude,
            'longitude': longitude,
            'isp': str(data.get('isp', 'Unknown')),
            'org': str(data.get('org', 'Unknown')),
            'asn': str(data.get('asn', 'Unknown')),
            'timezone': str(data.get('timezone', 'Unknown')),
            'error': None
        }
        return result

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error for {ip_address}: {e}")
        return {**default_response, 'error': f"Request failed: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error for {ip_address}: {e}")
        return {**default_response, 'error': str(e)}

def geolocate_ip_ipstack(ip_address: str, access_key: str) -> Dict[str, Optional[str]]:
    """
    Geolocate IP using ipstack.com (requires API key)

    Args:
        ip_address: IP address to geolocate
        access_key: API access key

    Returns:
        dict: Geolocation information
    """
    default_response = {
        'country': None,
        'country_code': None,
        'city': None,
        'region': None,
        'latitude': None,
        'longitude': None,
        'error': None
    }

    if is_private_ip(ip_address):
        return {**default_response, 'country': 'Local', 'country_code': 'XX', 'city': 'Local'}

    try:
        response = requests.get(
            f'http://api.ipstack.com/{ip_address}',
            params={'access_key': access_key},
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()

            if data.get('success') is False:
                return {**default_response, 'error': data.get('error', {}).get('info', 'Unknown error')}

            return {
                'country': data.get('country_name'),
                'country_code': data.get('country_code'),
                'city': data.get('city'),
                'region': data.get('region_name'),
                'latitude': data.get('latitude'),
                'longitude': data.get('longitude'),
                'error': None
            }
        else:
            return {**default_response, 'error': f'API returned status {response.status_code}'}

    except Exception as e:
        logger.error(f"ipstack error for {ip_address}: {str(e)}")
        return {**default_response, 'error': str(e)}
