"""
Proxy Middleware for forwarding requests using httpx
"""
import httpx
import asyncio
from django.http import HttpResponse, StreamingHttpResponse
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from typing import Optional, Dict, List, Tuple
import time
import hashlib
import logging

from .models import Site, Addresses, LoadBalancers


class ProxyMiddleware(MiddlewareMixin):
    """
    Middleware to proxy/forward requests to backend servers using httpx
    """
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.logger = logging.getLogger('waf.proxy')
        self.client = httpx.Client(
            timeout=30.0,
            follow_redirects=False,
            verify=False  # For development; enable in production
        )
        self.async_client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=False,
            verify=False
        )
        # Load balancer state
        self.round_robin_index = {}
        self.connection_counts = {}
    
    def __del__(self):
        """Cleanup clients"""
        try:
            self.client.close()
        except:
            pass
    
    def process_request(self, request):
        """Process and forward the request"""
        self.logger.info("=== PROXY START === proxy_phase=start path=%s method=%s host=%s", request.path, request.method, request.get_host())
        
        # Skip admin, static, and API endpoints
        if self._should_skip(request):
            self.logger.info("=== PROXY SKIP === proxy_phase=skip path=%s", request.path)
            return None
        
        # Get site configuration
        site = getattr(request, '_waf_site', None)
        if not site:
            site = self._get_site(request)
        
        if not site or site.status != 'active':
            self.logger.info("=== PROXY NO-SITE === proxy_phase=no_site path=%s host=%s", request.path, request.get_host())
            return None
        
        # Check if request was blocked by WAF
        waf_action = getattr(request, '_waf_action', None)
        if waf_action and hasattr(waf_action, 'value') and waf_action.value == 'block':
            # Already handled by WAF middleware
            self.logger.info("=== PROXY BLOCKED === proxy_phase=blocked_by_waf path=%s", request.path)
            return None
        
        # Get backend server
        backend = self._select_backend(site, request)
        if not backend:
            self.logger.warning("=== PROXY NO-BACKEND === proxy_phase=no_backend_available site=%s path=%s", getattr(site, 'host', None), request.path)
            # No backend found; let the request continue to Django/WAF (don't block or return error)
            return None

        # Prevent forwarding loops: if backend points to the same host:port
        # # as this WAF instance (e.g., 127.0.0.1:8000), skip proxying
        # if self._is_self_backend(backend, request):
        #     # Let the request fall through to Django views instead of proxying to self
        #     self.logger.info("proxy_phase=loop_guard backend=%s:%s path=%s", backend.get('ip'), backend.get('port'), request.path)
        #     return None
        
        # Forward request
        try:
            self.logger.info("=== PROXY FORWARD === proxy_phase=forward target=%s:%s url=%s", backend.get('ip'), backend.get('port'), backend.get('url'))
            response = self._forward_request(request, backend, site)
            self.logger.info("=== PROXY COMPLETE === proxy_phase=forward_complete status=%s", getattr(response, 'status_code', 'unknown'))
            return response
        except Exception as e:
            self.logger.exception("proxy_phase=error error=%s", e)
            return HttpResponse(f"Gateway error: {str(e)}", status=502)
    
    def _should_skip(self, request) -> bool:
        """Check if request should be skipped"""
        skip_paths = ['/admin/', '/static/', '/media/', '/api/']
        return any(request.path.startswith(path) for path in skip_paths)
    
    def _get_site(self, request) -> Optional[Site]:
        """Get site based on request host"""
        host = request.get_host().split(':')[0]
        try:
            return Site.objects.get(host=host, status='active')
        except Site.DoesNotExist:
            return Site.objects.filter(status='active').first()
    
    def _select_backend(self, site: Site, request) -> Optional[Dict]:
        """Select backend server based on load balancing algorithm"""
        
        # Get allowed addresses
        backends = list(site.addresses.filter(is_allowed=True))
        
        if not backends:
            return None
        
        # Get load balancer configuration
        lb = getattr(site, 'load_balancer', None)
        algorithm = lb.algorithm if lb else 'round_robin'
        
        # Select backend based on algorithm
        if algorithm == 'round_robin':
            backend = self._round_robin_select(site, backends)
        elif algorithm == 'least_connections':
            backend = self._least_connections_select(backends)
        elif algorithm == 'ip_hash':
            backend = self._ip_hash_select(request, backends)
        else:
            backend = backends[0]
        
        selected_dict = {
            'ip': backend.ip_address,
            'port': backend.port,
            'url': f"http://{backend.ip_address}:{backend.port}"
        }
        self.logger.info("=== PROXY BACKEND === proxy_phase=backend_selected site=%s ip=%s port=%s", site.host, selected_dict['ip'], selected_dict['port'])
        return selected_dict

    def _is_self_backend(self, backend: Dict, request) -> bool:
        """Detect if selected backend equals the current WAF server address.
        This avoids proxying to ourselves (infinite loop / 503).
        """
        try:
            backend_ip = str(backend.get('ip'))
            backend_port = str(backend.get('port'))
            waf_port = str(request.get_port())  # current server port handling this request
            # Consider localhost aliases
            is_local_ip = backend_ip in ('127.0.0.1', '::1', 'localhost')
            return is_local_ip and backend_port == waf_port
        except Exception:
            return False
    
    def _round_robin_select(self, site: Site, backends: List) -> Addresses:
        """Round-robin load balancing"""
        site_key = f"site_{site.id}"
        
        if site_key not in self.round_robin_index:
            self.round_robin_index[site_key] = 0
        
        index = self.round_robin_index[site_key] % len(backends)
        self.round_robin_index[site_key] += 1
        
        return backends[index]
    
    def _least_connections_select(self, backends: List) -> Addresses:
        """Least connections load balancing"""
        min_connections = float('inf')
        selected = backends[0]
        
        for backend in backends:
            backend_key = f"{backend.ip_address}:{backend.port}"
            connections = self.connection_counts.get(backend_key, 0)
            
            if connections < min_connections:
                min_connections = connections
                selected = backend
        
        return selected
    
    def _ip_hash_select(self, request, backends: List) -> Addresses:
        """IP hash load balancing for session persistence"""
        client_ip = self._get_client_ip(request)
        hash_value = int(hashlib.md5(client_ip.encode()).hexdigest(), 16)
        index = hash_value % len(backends)
        return backends[index]
    
    def _get_client_ip(self, request) -> str:
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')
    
    def _forward_request(self, request, backend: Dict, site: Site) -> HttpResponse:
        """Forward request to backend server"""
        
        # Build target URL
        target_url = f"{backend['url']}{request.path}"
        if request.META.get('QUERY_STRING'):
            target_url += f"?{request.META['QUERY_STRING']}"
        
        # Prepare headers
        headers = self._prepare_headers(request, site)
        
        # Track connection
        backend_key = f"{backend['ip']}:{backend['port']}"
        self.connection_counts[backend_key] = self.connection_counts.get(backend_key, 0) + 1
        
        try:
            # Forward request based on method
            if request.method == 'GET':
                response = self.client.get(target_url, headers=headers)
            elif request.method == 'POST':
                response = self.client.post(
                    target_url, 
                    headers=headers,
                    content=request.body
                )
            elif request.method == 'PUT':
                response = self.client.put(
                    target_url,
                    headers=headers,
                    content=request.body
                )
            elif request.method == 'DELETE':
                response = self.client.delete(target_url, headers=headers)
            elif request.method == 'PATCH':
                response = self.client.patch(
                    target_url,
                    headers=headers,
                    content=request.body
                )
            elif request.method == 'HEAD':
                response = self.client.head(target_url, headers=headers)
            elif request.method == 'OPTIONS':
                response = self.client.options(target_url, headers=headers)
            else:
                return HttpResponse(f"Method {request.method} not supported", status=405)
            
            # Create Django response from httpx response
            django_response = self._create_response(response)
            
            return django_response
            
        finally:
            # Release connection
            self.connection_counts[backend_key] -= 1
            if self.connection_counts[backend_key] <= 0:
                del self.connection_counts[backend_key]
    
    def _prepare_headers(self, request, site: Site) -> Dict[str, str]:
        """Prepare headers for forwarding"""
        headers = {}
        
        # Copy relevant headers
        for key, value in request.META.items():
            if key.startswith('HTTP_'):
                header_name = key[5:].replace('_', '-').title()
                
                # Skip hop-by-hop headers
                if header_name.lower() not in ['connection', 'keep-alive', 'proxy-authenticate',
                                                 'proxy-authorization', 'te', 'trailers',
                                                 'transfer-encoding', 'upgrade']:
                    headers[header_name] = value
        
        # Add/modify headers
        headers['X-Forwarded-For'] = self._get_client_ip(request)
        headers['X-Forwarded-Proto'] = 'https' if request.is_secure() else 'http'
        headers['X-Forwarded-Host'] = request.get_host()
        headers['X-Real-IP'] = self._get_client_ip(request)
        
        # Add custom headers
        headers['X-WAF-Protected'] = 'true'
        headers['X-WAF-Site'] = site.host
        
        return headers
    
    def _create_response(self, httpx_response: httpx.Response) -> HttpResponse:
        """Create Django response from httpx response"""
        
        # Create response
        response = HttpResponse(
            content=httpx_response.content,
            status=httpx_response.status_code
        )
        
        # Copy headers
        for key, value in httpx_response.headers.items():
            # Skip hop-by-hop headers
            if key.lower() not in ['connection', 'keep-alive', 'transfer-encoding']:
                response[key] = value
        
        return response


