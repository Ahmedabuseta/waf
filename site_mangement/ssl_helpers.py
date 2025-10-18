"""
SSL/TLS Helper Functions for Site Management Views
Provides utilities for certificate validation, DNS challenge display, and SSL configuration
"""
from typing import Dict, Optional, Tuple, List
from django.contrib import messages
from django.http import JsonResponse
from .models import Site
from .validators import SiteSSLValidator
from .utils.acme_dns_manager import ACMEDNSManager
from .utils.certificate_checker import CertificateChecker
import json


class SSLHelper:
    """Helper class for SSL-related operations in views"""

    def __init__(self):
        self.ssl_validator = SiteSSLValidator()
        self.acme_manager = ACMEDNSManager()
        self.cert_checker = CertificateChecker()

    def get_site_ssl_info(self, site: Site) -> Dict:
        """
        Get comprehensive SSL information for a site

        Args:
            site: Site model instance

        Returns:
            Dictionary with SSL configuration details
        """
        ssl_status = site.get_ssl_status()

        info = {
            'site_id': site.slug,
            'host': site.host,
            'protocol': site.protocol,
            'ssl_enabled': ssl_status['enabled'],
            'ssl_type': ssl_status['type'],
            'ssl_message': ssl_status['message'],
            'auto_ssl': site.auto_ssl,
            'support_subdomains': site.support_subdomains,
            'has_certificate': bool(site.ssl_certificate),
            'has_key': bool(site.ssl_key),
            'has_chain': bool(site.ssl_chain),
            'requires_dns_challenge': site.requires_dns_challenge(),
        }

        # Add certificate details if available
        if site.ssl_certificate:
            try:
                cert_info = self._get_certificate_info(site.ssl_certificate.path)
                info['certificate'] = cert_info
            except Exception as e:
                info['certificate_error'] = str(e)

        # Add DNS challenge info if needed
        if site.requires_dns_challenge():
            info['dns_challenge'] = self.acme_manager.generate_challenge_instructions(
                str(site.host), bool(site.support_subdomains)
            )

        return info

    def get_dns_challenge_instructions(self, host: str, support_subdomains: bool) -> Dict:
        """
        Get DNS challenge instructions for a domain

        Args:
            host: Domain name
            support_subdomains: Whether wildcard is needed

        Returns:
            Dictionary with DNS challenge instructions
        """
        return self.acme_manager.generate_challenge_instructions(host, support_subdomains)

    def verify_dns_challenge(self, host: str, expected_value: Optional[str] = None) -> Dict:
        """
        Verify DNS challenge record

        Args:
            host: Domain name
            expected_value: Expected TXT record value

        Returns:
            Dictionary with verification results
        """
        return self.acme_manager.verify_dns_challenge_record(host, expected_value)

    def check_dns_propagation(self, host: str, expected_value: str) -> Dict:
        """
        Check DNS propagation across multiple servers

        Args:
            host: Domain name
            expected_value: Expected TXT record value

        Returns:
            Dictionary with propagation status
        """
        return self.acme_manager.check_dns_propagation(host, expected_value)

    def validate_uploaded_certificate(
        self,
        cert_file,
        key_file,
        chain_file=None,
        host: Optional[str] = None,
        support_subdomains: bool = False
    ) -> Tuple[bool, List[str], Optional[Dict]]:
        """
        Validate uploaded certificate files

        Args:
            cert_file: Certificate file upload
            key_file: Private key file upload
            chain_file: Certificate chain file upload (optional)
            host: Domain name for coverage check
            support_subdomains: Whether wildcard coverage is required

        Returns:
            Tuple of (is_valid, error_messages, certificate_info)
        """
        is_valid, errors = self.ssl_validator.validate_site_ssl_configuration(
            protocol='https',
            auto_ssl=False,
            support_subdomains=support_subdomains,
            host=host or 'unknown.com',
            ssl_certificate=cert_file,
            ssl_key=key_file,
            ssl_chain=chain_file
        )

        cert_info = None
        if is_valid and cert_file:
            try:
                # Get certificate info for display
                import tempfile
                import os
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pem') as tmp:
                    for chunk in cert_file.chunks():
                        tmp.write(chunk)
                    tmp_path = tmp.name
                cert_file.seek(0)

                cert_info = self._get_certificate_info(tmp_path)
                os.unlink(tmp_path)
            except Exception as e:
                errors.append(f"Error reading certificate info: {str(e)}")

        return is_valid, errors, cert_info

    def _get_certificate_info(self, cert_path: str) -> Dict:
        """
        Get detailed certificate information

        Args:
            cert_path: Path to certificate file

        Returns:
            Dictionary with certificate details
        """
        cert_info = self.cert_checker.check_certificate_domains(cert_path)

        if 'error' in cert_info:
            return {'error': cert_info['error']}

        # Get validation status
        is_valid, message, details = self.cert_checker.validate_certificate(cert_path)

        return {
            'common_name': cert_info.get('common_name'),
            'san_domains': cert_info.get('san_domains', []),
            'all_domains': cert_info.get('all_domains', []),
            'has_wildcard': cert_info.get('has_wildcard', False),
            'wildcard_domains': cert_info.get('wildcard_domains', []),
            'issuer': cert_info.get('issuer', {}).get('commonName', 'Unknown'),
            'valid_from': cert_info.get('not_before'),
            'valid_until': cert_info.get('not_after'),
            'expires': cert_info.get('expires'),
            'days_until_expiry': details.get('days_until_expiry', 0),
            'is_valid': is_valid,
            'validation_message': message,
            'is_self_signed': details.get('is_self_signed', False)
        }

    def format_dns_instructions_html(self, instructions: Dict) -> str:
        """
        Format DNS challenge instructions as HTML

        Args:
            instructions: Instructions dictionary

        Returns:
            HTML formatted string
        """
        if not instructions.get('required'):
            return f"<p class='text-success'>{instructions.get('message', 'No DNS challenge required')}</p>"

        html_parts = []

        # Header
        html_parts.append('<div class="dns-challenge-instructions alert alert-info">')
        html_parts.append('<h4 class="alert-heading">🔐 DNS Challenge Required</h4>')
        html_parts.append(f'<p><strong>Domain:</strong> {instructions["domain"]}</p>')
        html_parts.append(f'<p><strong>Wildcard:</strong> {instructions["wildcard_domain"]}</p>')
        html_parts.append(f'<p><strong>Challenge Record:</strong> <code>{instructions["challenge_record"]}</code></p>')
        html_parts.append('</div>')

        # Steps
        html_parts.append('<div class="card mb-3">')
        html_parts.append('<div class="card-header"><h5>📋 Step-by-Step Instructions</h5></div>')
        html_parts.append('<div class="card-body">')
        html_parts.append('<ol class="list-group list-group-numbered">')

        for step_info in instructions['instructions']['steps']:
            html_parts.append('<li class="list-group-item">')
            html_parts.append(f'<strong>{step_info["action"]}</strong><br>')
            html_parts.append(f'<span class="text-muted">{step_info["description"]}</span>')

            if 'details' in step_info:
                html_parts.append('<div class="mt-2 p-2 bg-light border rounded">')
                for key, value in step_info['details'].items():
                    html_parts.append(f'<div><strong>{key}:</strong> <code>{value}</code></div>')
                html_parts.append('</div>')

            if 'command' in step_info:
                html_parts.append(f'<div class="mt-2"><code class="bg-dark text-light p-2 d-block">{step_info["command"]}</code></div>')

            html_parts.append('</li>')

        html_parts.append('</ol>')
        html_parts.append('</div>')
        html_parts.append('</div>')

        # Important notes
        html_parts.append('<div class="card mb-3 border-warning">')
        html_parts.append('<div class="card-header bg-warning"><h5>⚠️ Important Notes</h5></div>')
        html_parts.append('<div class="card-body">')
        html_parts.append('<ul class="list-unstyled">')
        for note in instructions['important_notes']:
            html_parts.append(f'<li class="mb-2">{note}</li>')
        html_parts.append('</ul>')
        html_parts.append('</div>')
        html_parts.append('</div>')

        # DNS providers
        if 'common_dns_providers' in instructions:
            html_parts.append('<div class="card">')
            html_parts.append('<div class="card-header"><h5>🌐 Common DNS Providers</h5></div>')
            html_parts.append('<div class="card-body">')
            html_parts.append('<div class="row">')
            for provider in instructions['common_dns_providers']:
                html_parts.append('<div class="col-md-6 mb-2">')
                html_parts.append(f'<strong>{provider["name"]}</strong>')
                if provider.get('api_support'):
                    html_parts.append(' <span class="badge bg-success">API Support</span>')
                html_parts.append(f'<br><a href="{provider["docs_url"]}" target="_blank" class="small">Documentation</a>')
                html_parts.append('</div>')
            html_parts.append('</div>')
            html_parts.append('</div>')
            html_parts.append('</div>')

        return '\n'.join(html_parts)

    def get_ssl_configuration_warnings(self, site: Site) -> List[Dict]:
        """
        Get warnings about SSL configuration

        Args:
            site: Site model instance

        Returns:
            List of warning dictionaries
        """
        warnings = []

        # Check for HTTP with SSL fields
        if site.protocol == 'http' and (site.ssl_certificate or site.ssl_key or site.auto_ssl):
            warnings.append({
                'level': 'danger',
                'message': 'HTTP protocol has SSL configuration. This is inconsistent and should be fixed.'
            })

        # Check for HTTPS without SSL
        if site.protocol == 'https' and not site.auto_ssl and not site.ssl_certificate:
            warnings.append({
                'level': 'danger',
                'message': 'HTTPS protocol requires SSL configuration (auto_ssl or certificate upload).'
            })

        # Check certificate expiration
        if site.ssl_certificate:
            try:
                cert_info = self._get_certificate_info(site.ssl_certificate.path)
                days_until_expiry = cert_info.get('days_until_expiry', 0)

                if days_until_expiry < 0:
                    warnings.append({
                        'level': 'danger',
                        'message': f'SSL certificate has expired! Expired {abs(days_until_expiry)} days ago.'
                    })
                elif days_until_expiry < 7:
                    warnings.append({
                        'level': 'warning',
                        'message': f'SSL certificate expires in {days_until_expiry} days. Renew soon!'
                    })
                elif days_until_expiry < 30:
                    warnings.append({
                        'level': 'info',
                        'message': f'SSL certificate expires in {days_until_expiry} days.'
                    })
            except Exception as e:
                warnings.append({
                    'level': 'warning',
                    'message': f'Unable to check certificate expiration: {str(e)}'
                })

        # Check subdomain support
        if site.support_subdomains and site.ssl_certificate:
            try:
                cert_info = self._get_certificate_info(site.ssl_certificate.path)
                if not cert_info.get('has_wildcard'):
                    warnings.append({
                        'level': 'warning',
                        'message': 'Subdomain support enabled but certificate does not include wildcard domain.'
                    })
            except Exception:
                pass

        # DNS challenge reminder
        if site.requires_dns_challenge():
            warnings.append({
                'level': 'info',
                'message': 'This site requires DNS challenge for wildcard certificate. Ensure DNS records are configured.'
            })

        return warnings

    def add_ssl_messages_to_request(self, request, site: Site):
        """
        Add SSL-related Django messages to the request

        Args:
            request: Django request object
            site: Site model instance
        """
        warnings = self.get_ssl_configuration_warnings(site)

        for warning in warnings:
            if warning['level'] == 'danger':
                messages.error(request, warning['message'])
            elif warning['level'] == 'warning':
                messages.warning(request, warning['message'])
            elif warning['level'] == 'info':
                messages.info(request, warning['message'])

    def get_certificate_renewal_status(self, site: Site) -> Optional[Dict]:
        """
        Get certificate renewal status and recommendations

        Args:
            site: Site model instance

        Returns:
            Dictionary with renewal status or None if not applicable
        """
        if not site.ssl_certificate or site.protocol == 'http':
            return None

        try:
            cert_info = self._get_certificate_info(site.ssl_certificate.path)
            days_until_expiry = cert_info.get('days_until_expiry', 0)

            if days_until_expiry < 0:
                status = 'expired'
                action = 'immediate'
                priority = 'critical'
            elif days_until_expiry < 7:
                status = 'expiring_soon'
                action = 'urgent'
                priority = 'high'
            elif days_until_expiry < 30:
                status = 'renew_soon'
                action = 'recommended'
                priority = 'medium'
            else:
                status = 'valid'
                action = 'none'
                priority = 'low'

            return {
                'status': status,
                'action_required': action,
                'priority': priority,
                'days_until_expiry': days_until_expiry,
                'expiration_date': cert_info.get('valid_until'),
                'auto_renewal_enabled': site.auto_ssl,
                'recommendation': self._get_renewal_recommendation(days_until_expiry, site.auto_ssl)
            }

        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'recommendation': 'Unable to check certificate status'
            }

    def _get_renewal_recommendation(self, days_until_expiry: int, auto_ssl: bool) -> str:
        """Get certificate renewal recommendation"""
        if days_until_expiry < 0:
            if auto_ssl:
                return "Certificate expired! Auto-renewal should have triggered. Check ACME client logs."
            else:
                return "Certificate expired! Upload a new certificate immediately."
        elif days_until_expiry < 7:
            if auto_ssl:
                return "Certificate expiring soon. Auto-renewal will trigger shortly."
            else:
                return "Certificate expiring soon. Upload a renewed certificate urgently."
        elif days_until_expiry < 30:
            if auto_ssl:
                return "Certificate will auto-renew before expiration."
            else:
                return "Consider renewing certificate soon."
        else:
            return "Certificate valid. No action needed."


# Standalone helper functions for use in views

def get_ssl_helper() -> SSLHelper:
    """Get SSLHelper instance (factory function)"""
    return SSLHelper()


def validate_site_ssl_config(site: Site) -> Tuple[bool, List[str]]:
    """
    Quick validation of site SSL configuration

    Args:
        site: Site model instance

    Returns:
        Tuple of (is_valid, error_messages)
    """
    helper = SSLHelper()
    validator = SiteSSLValidator()

    return validator.validate_site_ssl_configuration(
        protocol=str(site.protocol),
        auto_ssl=bool(site.auto_ssl),
        support_subdomains=bool(site.support_subdomains),
        host=str(site.host),
        ssl_certificate=site.ssl_certificate,
        ssl_key=site.ssl_key,
        ssl_chain=site.ssl_chain
    )


def get_dns_challenge_json(host: str, support_subdomains: bool) -> JsonResponse:
    """
    Get DNS challenge instructions as JSON response

    Args:
        host: Domain name
        support_subdomains: Whether wildcard is needed

    Returns:
        JsonResponse with DNS challenge instructions
    """
    helper = SSLHelper()
    instructions = helper.get_dns_challenge_instructions(host, support_subdomains)
    return JsonResponse(instructions)


def verify_dns_record_json(host: str, expected_value: Optional[str] = None) -> JsonResponse:
    """
    Verify DNS challenge record as JSON response

    Args:
        host: Domain name
        expected_value: Expected TXT record value

    Returns:
        JsonResponse with verification results
    """
    helper = SSLHelper()
    result = helper.verify_dns_challenge(host, expected_value)
    return JsonResponse(result)
