"""
Enhanced WAF Middleware with Rule Engine Integration
"""
import time
import logging
from django.utils import timezone
from django.http import HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin
from django.template import loader
from site_management.models import Site, RequestAnalytics, Logs, BlockedIP
from site_management.utils.ip_utils import get_client_ip, geolocate_ip
from site_management.rules_engine import create_rule_engine, RuleAction, ThreatLevel

logger = logging.getLogger('waf.request')


class WAFMiddleware(MiddlewareMixin):
    """
    WAF Middleware with rule engine for threat detection and blocking
    """

    def process_request(self, request):
        """Store request start time and evaluate WAF rules"""
        request._analytics_start_time = time.time()
        logger.info("phase=start path=%s method=%s", request.path, request.method)

        # Skip for admin and static files
        if request.path.startswith('/admin/') or request.path.startswith('/static/'):
            logger.info("phase=skip reason=admin_or_static path=%s", request.path)
            return None

        # Skip WAF blocking and analytics for authenticated users on management paths
        # Still collect analytics, but don't block legitimate admin actions
        # if request.user.is_authenticated and (
        #     request.path.startswith('/sites/') or
        #     request.path.startswith('/templates/') or
        #     request.path.startswith('/logs/') or
        #     request.path.startswith('/analytics/')
        # ):
        #     # Mark as management request (analytics only, no blocking)
        #     request._waf_management = True
        #     logger.info("phase=management_request user=%s path=%s", getattr(request.user, 'username', None), request.path)

        # Get site configuration
        site = self._get_site(request)
        if not site:
            logger.info("phase=no_site_config host=%s path=%s", request.get_host(), request.path)
            return None

        # Enforce timed IP blocks
        client_ip = get_client_ip(request)
        try:
            active_block = BlockedIP.objects.filter(site=site, ip_address=client_ip, expires_at__gt=timezone.now()).first()
        except Exception:
            active_block = None
        if active_block:
            logger.info("phase=blocked_by_timed_block ip=%s site=%s until=%s", client_ip, site.host, active_block.expires_at)
            # Render blocked page immediately
            class MatchObj:
                rule_name = 'TimedBlock'
                threat_type = f"blocked_ip_level_{active_block.escalation_level}"
                details = active_block.reason
                # Map to high for display
                class TL:
                    value = 'high'
                threat_level = TL()
            return self._block_request(request, site, MatchObj)

        request._waf_site = site
        logger.info("phase=site_loaded host=%s action_type=%s sensitivity=%s", site.host, site.action_type, site.sensitivity_level)

        # Prepare request data for rule engine
        request_data = self._prepare_request_data(request)

        # Create rule engine based on site's WAF template
        rule_engine = create_rule_engine(site.WafTemplate)

        # Evaluate request
        action, match = rule_engine.evaluate(request_data)

        # Store evaluation result
        request._waf_action = action
        request._waf_match = match
        logger.info(
            "phase=evaluated action=%s matched=%s rule=%s threat_type=%s level=%s details=%s",
            action.name,
            bool(match),
            getattr(match, 'rule_name', None),
            getattr(match, 'threat_type', None),
            getattr(match, 'threat_level', None).value if match else None,
            getattr(match, 'details', None),
        )

        # Block if action is BLOCK and site action_type is 'block'
        is_management = getattr(request, '_waf_management', False)
        if action == RuleAction.BLOCK and site.action_type == 'block' and not is_management:
            logger.info("phase=block_response reason=policy path=%s", request.path)
            return self._block_request(request, site, match)

        logger.info("phase=allow_response path=%s", request.path)
        return None

    def process_response(self, request, response):
        """Capture analytics and log the request"""
        # Skip for admin, static files, API endpoints, and management UI
        # if (
        #     request.path.startswith('/admin/') or
        #     request.path.startswith('/static/') or
        #     request.path.startswith('/api/') or
        #     getattr(request, '_waf_management', False)
        # ):
        #     return response

        try:
            site = getattr(request, '_waf_site', None)
            if not site:
                return response

            # Calculate response time
            start_time = getattr(request, '_analytics_start_time', None)
            response_time = (time.time() - start_time) * 1000 if start_time else 0

            # Get client IP
            ip_address = get_client_ip(request)

            # Get WAF evaluation results
            action = getattr(request, '_waf_action', RuleAction.ALLOW)
            match = getattr(request, '_waf_match', None)

            # Determine action taken and threat level
            if match:
                action_taken = 'blocked' if action == RuleAction.BLOCK and site.action_type == 'block' else 'logged'
                threat_level = match.threat_level.value
                threat_type = match.threat_type
                details = f"{match.rule_name}: {match.details}"
            else:
                action_taken = 'allowed'
                threat_level = 'none'
                threat_type = None
                details = None

            # Geolocate IP
            geo_data = geolocate_ip(ip_address)

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
                threat_type=threat_type,
            )
            logger.info(
                "phase=analytics_saved status=%s time_ms=%.2f ip=%s action_taken=%s threat_level=%s",
                response.status_code,
                response_time,
                ip_address,
                action_taken,
                threat_level,
            )

            # Create log entry if blocked or threat detected
            if match:
                Logs.objects.create(
                    site=site,
                    ip_address=ip_address,
                    request_method=request.method,
                    request_url=request.build_absolute_uri(),
                    action_taken=action_taken,
                    details=details,
                )
                logger.info("phase=security_log_saved action_taken=%s details=%s", action_taken, details)

        except Exception as e:
            # Log error but don't break the request
            logger.exception("phase=error error=%s", e)

        return response

    def _get_site(self, request):
        """Get site based on request host"""
        # Try to match by hostname
        host = request.get_host().split(':')[0]  # Remove port
        try:
            return Site.objects.get(host=host, status='active')
        except Site.DoesNotExist:
            # No fallback: avoid mis-attributing requests to wrong site
            return None

    def _prepare_request_data(self, request):
        """Prepare request data for rule engine evaluation"""
        # Get query parameters
        params = dict(request.GET.items())

        # Get headers
        headers = {
            key.replace('HTTP_', '').replace('_', '-'): value
            for key, value in request.META.items()
            if key.startswith('HTTP_')
        }

        # Get body (for POST requests)
        # For management requests, only scan user input fields, not CSRF tokens
        body = ''
        if request.method == 'POST':
            is_management = getattr(request, '_waf_management', False)
            if is_management:
                # For authenticated management, skip body scanning
                # CSRF tokens and form data are safe
                body = ''
            else:
                # For public POST requests, scan the body
                try:
                    body = request.body.decode('utf-8')
                    # Remove CSRF token from scanning
                    if 'csrfmiddlewaretoken=' in body:
                        # Split by & and filter out CSRF token
                        parts = body.split('&')
                        filtered = [p for p in parts if not p.startswith('csrfmiddlewaretoken=')]
                        body = '&'.join(filtered)
                except:
                    body = ''

        return {
            'url': request.build_absolute_uri(),
            'path': request.path,
            'method': request.method,
            'headers': headers,
            'params': params,
            'body': body,
        }

    def _block_request(self, request, site, match):
        """Block the request and return 403 response"""
        context = {
            'site': site,
            'rule_name': match.rule_name,
            'threat_type': match.threat_type,
            'threat_level': match.threat_level.value,
            'details': match.details,
        }
        logger.info("phase=render_block_page rule=%s path=%s", match.rule_name, request.path)

        # Use custom template or default
        template = loader.get_template('waf/blocked.html')
        content = template.render(context, request)

        return HttpResponseForbidden(content)
