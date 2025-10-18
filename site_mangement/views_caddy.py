"""
Enhanced Caddy Management Views with SSL/TLS Validation
Integrates comprehensive certificate validation, DNS challenge support, and site management
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.utils import timezone
import json
import os

from .models import Site
from .ssl_helpers import get_ssl_helper
from .utils.enhanced_caddy_manager import EnhancedCaddyManager, CaddyConfig, CaddyAPIError
from .utils.acme_dns_manager import ACMEDNSManager


# Initialize managers
def get_caddy_manager():
    """Get configured Caddy manager instance"""
    return EnhancedCaddyManager(
        api_url=getattr(settings, 'CADDY_API_URL', 'http://localhost:2019'),
        base_path=getattr(settings, 'CADDY_BASE_PATH', '/etc/caddy'),
        enable_logging=True,
        enable_validation=True
    )


@login_required
def caddy_status(request):
    """
    Display Caddy API status and configuration overview
    """
    caddy = get_caddy_manager()

    is_connected, error_message = caddy.check_connection()

    context = {
        'connected': is_connected,
        'api_url': caddy.api_url,
        'error_message': error_message,
        'sites_count': 0,
        'active_sites_count': 0,
    }

    if is_connected:
        try:
            # Get all managed sites
            sites = caddy.list_sites()
            context['sites_count'] = len(sites)
            context['managed_sites'] = sites

            # Count active sites
            active_sites = Site.objects.filter(status='active').count()
            context['active_sites_count'] = active_sites

        except Exception as e:
            context['error'] = str(e)

    return render(request, 'site_management/caddy_status.html', context)


@login_required
def sync_site_to_caddy(request, site_slug):
    """
    Sync a single site configuration to Caddy with full validation
    """
    site = get_object_or_404(Site, slug=site_slug)

    try:
        caddy = get_caddy_manager()
        ssl_helper = get_ssl_helper()

        # Check Caddy connection
        is_connected, error_message = caddy.check_connection()
        if not is_connected:
            messages.error(request, f'Cannot connect to Caddy: {error_message}')
            return redirect('site_detail', slug=site_slug)

        # Validate site SSL configuration
        is_valid, validation_errors = ssl_helper.ssl_validator.validate_site_ssl_configuration(
            protocol=site.protocol,
            auto_ssl=site.auto_ssl,
            support_subdomains=site.support_subdomains,
            host=site.host,
            ssl_certificate=site.ssl_certificate,
            ssl_key=site.ssl_key,
            ssl_chain=site.ssl_chain
        )

        if not is_valid:
            for error in validation_errors:
                messages.error(request, f'Validation error: {error}')
            return redirect('site_detail', slug=site_slug)

        # Build Caddy configuration
        caddy_config = CaddyConfig(
            host=site.host,
            protocol=site.protocol,
            auto_ssl=site.auto_ssl,
            support_subdomains=site.support_subdomains,
            ssl_cert_path=site.ssl_certificate.path if site.ssl_certificate else None,
            ssl_key_path=site.ssl_key.path if site.ssl_key else None,
            ssl_chain_path=site.ssl_chain.path if site.ssl_chain else None,
            auto_https_redirect=(site.protocol == 'https')
        )

        # Sync to Caddy
        if site.status == 'active':
            result = caddy.add_site(caddy_config)

            if result['success']:
                messages.success(request, f'Site {site.host} synced to Caddy successfully')

                # Check if DNS challenge is required
                if result.get('dns_challenge') and result['dns_challenge'].get('required'):
                    messages.info(
                        request,
                        f'DNS challenge required for wildcard certificate. '
                        f'Please configure DNS TXT record: {result["dns_challenge"]["challenge_record"]}'
                    )
                    # Store DNS challenge info in session for display
                    request.session['dns_challenge_info'] = result['dns_challenge']
            else:
                error_msg = result.get('error', 'Unknown error')
                messages.error(request, f'Failed to sync site: {error_msg}')

                # Show validation errors if any
                if 'validation_errors' in result:
                    for error in result['validation_errors']:
                        messages.error(request, f'• {error}')
        else:
            # Remove from Caddy if inactive
            result = caddy.remove_site(site.host)
            if result['success']:
                messages.success(request, f'Site {site.host} removed from Caddy')
            else:
                messages.error(request, f'Failed to remove site: {result.get("error")}')

    except CaddyAPIError as e:
        messages.error(request, f'Caddy API error: {str(e)}')
    except Exception as e:
        messages.error(request, f'Error syncing to Caddy: {str(e)}')

    return redirect('site_detail', slug=site_slug)


@login_required
@require_http_methods(["POST"])
def sync_all_sites(request):
    """
    Sync all active sites to Caddy with comprehensive validation
    """
    try:
        caddy = get_caddy_manager()

        is_connected, error_message = caddy.check_connection()
        if not is_connected:
            messages.error(request, f'Cannot connect to Caddy: {error_message}')
            return redirect('sites_list')

        sites = Site.objects.filter(status='active')
        success_count = 0
        error_count = 0
        skipped_count = 0
        errors = []

        for site in sites:
            try:
                # Check for backend addresses
              

                # Build configuration
                caddy_config = CaddyConfig(
                    host=site.host,
                    
                    protocol=site.protocol,
                    auto_ssl=site.auto_ssl,
                    support_subdomains=site.support_subdomains,
                    ssl_cert_path=site.ssl_certificate.path if site.ssl_certificate else None,
                    ssl_key_path=site.ssl_key.path if site.ssl_key else None,
                    ssl_chain_path=site.ssl_chain.path if site.ssl_chain else None,
                    auto_https_redirect=(site.protocol == 'https')
                )

                result = caddy.add_site(caddy_config)

                if result['success']:
                    success_count += 1
                else:
                    error_count += 1
                    errors.append(f'{site.host}: {result.get("error", "Unknown error")}')

            except Exception as e:
                error_count += 1
                errors.append(f'{site.host}: {str(e)}')

        # Display results
        messages.success(request, f'Synced {success_count} sites successfully')

        if skipped_count > 0:
            messages.warning(request, f'Skipped {skipped_count} sites (no backend addresses)')

        if error_count > 0:
            messages.error(request, f'{error_count} errors occurred')
            for error in errors[:5]:  # Show first 5 errors
                messages.error(request, f'• {error}')

    except Exception as e:
        messages.error(request, f'Error: {str(e)}')

    return redirect('sites_list')


@login_required
def ssl_upload_page(request, site_slug):
    """
    Page to upload and validate SSL certificates with comprehensive validation
    """
    site = get_object_or_404(Site, slug=site_slug)
    ssl_helper = get_ssl_helper()

    if request.method == 'POST':
        try:
            cert_file = request.FILES.get('ssl_certificate')
            key_file = request.FILES.get('ssl_key')
            chain_file = request.FILES.get('ssl_chain')

            if not cert_file or not key_file:
                messages.error(request, 'Certificate and private key are required')
                return redirect('ssl_upload', site_slug=site_slug)

            # Validate uploaded certificates
            is_valid, errors, cert_info = ssl_helper.validate_uploaded_certificate(
                cert_file=cert_file,
                key_file=key_file,
                chain_file=chain_file,
                host=site.host,
                support_subdomains=site.support_subdomains
            )

            if not is_valid:
                for error in errors:
                    messages.error(request, error)
                return redirect('ssl_upload', site_slug=site_slug)

            # Save certificates
            if site.ssl_certificate:
                site.ssl_certificate.delete()
            if site.ssl_key:
                site.ssl_key.delete()
            if site.ssl_chain:
                site.ssl_chain.delete()

            site.ssl_certificate = cert_file
            site.ssl_key = key_file
            if chain_file:
                site.ssl_chain = chain_file
            site.auto_ssl = False
            site.protocol = 'https'  # Ensure HTTPS is set
            site.save()

            messages.success(request, 'SSL certificates uploaded and validated successfully')

            # Display certificate info
            if cert_info:
                messages.info(
                    request,
                    f'Certificate valid until: {cert_info.get("valid_until")} '
                    f'(expires in {cert_info.get("days_until_expiry")} days)'
                )
                if cert_info.get('has_wildcard'):
                    messages.info(request, '✓ Certificate includes wildcard support')

            return redirect('site_detail', slug=site_slug)

        except Exception as e:
            messages.error(request, f'Error uploading SSL: {str(e)}')

    # Get current SSL info
    ssl_info = None
    ssl_warnings = []

    if site.ssl_certificate:
        try:
            ssl_info = ssl_helper.get_site_ssl_info(site)
            ssl_warnings = ssl_helper.get_ssl_configuration_warnings(site)
        except Exception as e:
            messages.warning(request, f'Could not read certificate info: {str(e)}')

    context = {
        'site': site,
        'ssl_info': ssl_info,
        'ssl_warnings': ssl_warnings,
    }
    return render(request, 'site_management/ssl_upload.html', context)


@login_required
@require_http_methods(["POST"])
def validate_ssl_api(request):
    """
    API endpoint to validate SSL certificate before upload
    """
    try:
        if 'certificate' not in request.FILES:
            return JsonResponse({'error': 'No certificate file provided'}, status=400)

        cert_file = request.FILES['certificate']
        key_file = request.FILES.get('private_key')
        chain_file = request.FILES.get('chain')
        host = request.POST.get('host', 'example.com')
        support_subdomains = request.POST.get('support_subdomains') == 'true'

        ssl_helper = get_ssl_helper()

        # Validate
        is_valid, errors, cert_info = ssl_helper.validate_uploaded_certificate(
            cert_file=cert_file,
            key_file=key_file,
            chain_file=chain_file,
            host=host,
            support_subdomains=support_subdomains
        )

        result = {
            'valid': is_valid,
            'errors': errors,
            'certificate_info': cert_info
        }

        return JsonResponse(result)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def toggle_auto_ssl(request, site_slug):
    """
    Toggle auto SSL for a site with validation
    """
    site = get_object_or_404(Site, slug=site_slug)

    new_auto_ssl = not site.auto_ssl

    # Validate the change
    if new_auto_ssl:
        # Enabling auto SSL - ensure protocol is HTTPS
        if site.protocol != 'https':
            messages.error(request, 'Cannot enable auto SSL on HTTP sites. Change protocol to HTTPS first.')
            return redirect('site_detail', slug=site_slug)

        # Remove uploaded certificates
        if site.ssl_certificate:
            site.ssl_certificate.delete()
        if site.ssl_key:
            site.ssl_key.delete()
        if site.ssl_chain:
            site.ssl_chain.delete()

        site.auto_ssl = True
        site.save()

        messages.success(request, f'Auto SSL enabled for {site.host}')

        # Check if DNS challenge is needed
        if site.support_subdomains:
            messages.info(
                request,
                'Wildcard certificate requires DNS challenge. See DNS Challenge section for instructions.'
            )
    else:
        # Disabling auto SSL - user must upload certificates
        site.auto_ssl = False
        site.save()

        messages.warning(
            request,
            f'Auto SSL disabled for {site.host}. Please upload SSL certificates to maintain HTTPS.'
        )

    return redirect('site_detail', slug=site_slug)


@login_required
def dns_challenge_page(request, site_slug):
    """
    Display DNS challenge instructions for wildcard certificates
    """
    site = get_object_or_404(Site, slug=site_slug)
    ssl_helper = get_ssl_helper()
    acme_manager = ACMEDNSManager()

    # Check if DNS challenge is required
    if not site.requires_dns_challenge():
        messages.info(request, 'DNS challenge not required for this site configuration')
        return redirect('site_detail', slug=site_slug)

    # Generate or refresh challenge if needed
    if request.method == 'POST' and request.POST.get('action') == 'generate_challenge':
        # Generate new challenge
        challenge_data = acme_manager.generate_challenge_value(site.host)
        site.dns_challenge_key = challenge_data['key']
        site.dns_challenge_value = challenge_data['value']
        site.dns_challenge_created_at = timezone.now()
        site.save(update_fields=['dns_challenge_key', 'dns_challenge_value', 'dns_challenge_created_at'])
        messages.success(request, 'New DNS challenge generated successfully!')
        return redirect('dns_challenge', slug=site_slug)

    # Clear challenge if requested
    if request.method == 'POST' and request.POST.get('action') == 'clear_challenge':
        site.clear_dns_challenge()
        messages.info(request, 'DNS challenge cleared successfully!')
        return redirect('dns_challenge', slug=site_slug)

    # Check if we need to generate a new challenge
    if not site.has_dns_challenge() or site.is_dns_challenge_expired():
        # Generate new challenge automatically
        challenge_data = acme_manager.generate_challenge_value(site.host)
        site.dns_challenge_key = challenge_data['key']
        site.dns_challenge_value = challenge_data['value']
        site.dns_challenge_created_at = timezone.now()
        site.save(update_fields=['dns_challenge_key', 'dns_challenge_value', 'dns_challenge_created_at'])

    # Get DNS challenge instructions with actual challenge value
    instructions = acme_manager.generate_challenge_instructions(
        domain=site.host,
        support_subdomains=site.support_subdomains,
        challenge_value=site.dns_challenge_value
    )

    # Format for HTML display
    html_instructions = ssl_helper.format_dns_instructions_html(instructions)

    # Check if verification was requested
    verification_result = None
    propagation_result = None

    if request.method == 'POST':
        action = request.POST.get('action')
        expected_value = request.POST.get('expected_value', '')

        if action == 'verify':
            # Use stored challenge value if no value provided
            verify_value = expected_value if expected_value else site.dns_challenge_value
            if verify_value:
                verification_result = acme_manager.verify_dns_challenge_record(
                    domain=site.host,
                    expected_value=verify_value
                )
            else:
                messages.warning(request, 'No challenge value provided for verification')
        elif action == 'check_propagation':
            # Use stored challenge value if no value provided
            check_value = expected_value if expected_value else site.dns_challenge_value
            if check_value:
                propagation_result = acme_manager.check_dns_propagation(
                    domain=site.host,
                    expected_value=check_value
                )
            else:
                messages.warning(request, 'No challenge value provided for propagation check')

    context = {
        'site': site,
        'instructions': instructions,
        'html_instructions': html_instructions,
        'verification_result': verification_result,
        'propagation_result': propagation_result,
        'has_challenge': site.has_dns_challenge(),
        'challenge_expired': site.is_dns_challenge_expired(),
    }

    return render(request, 'site_management/dns_challenge.html', context)


@login_required
@require_http_methods(["POST"])
def verify_dns_record_api(request):
    """
    API endpoint to verify DNS TXT record
    """
    try:
        data = json.loads(request.body)
        domain = data.get('domain')
        expected_value = data.get('expected_value')

        if not domain:
            return JsonResponse({'error': 'Domain is required'}, status=400)

        acme_manager = ACMEDNSManager()
        result = acme_manager.verify_dns_challenge_record(domain, expected_value)

        return JsonResponse(result)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def check_dns_propagation_api(request):
    """
    API endpoint to check DNS propagation across multiple servers
    """
    try:
        data = json.loads(request.body)
        domain = data.get('domain')
        expected_value = data.get('expected_value')

        if not domain or not expected_value:
            return JsonResponse({'error': 'Domain and expected_value are required'}, status=400)

        acme_manager = ACMEDNSManager()
        result = acme_manager.check_dns_propagation(domain, expected_value)

        return JsonResponse(result)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def caddy_config_view(request, site_slug):
    """
    View generated Caddy configuration for a site
    """
    site = get_object_or_404(Site, slug=site_slug)

    config_text = None
    validation_result = None

    try:
        caddy = get_caddy_manager()

        addresses = site.addresses.filter(is_allowed=True)
        if addresses.exists():
            # Build configuration
            caddy_config = CaddyConfig(
                host=site.host,
                protocol=site.protocol,
                auto_ssl=site.auto_ssl,
                support_subdomains=site.support_subdomains,
                ssl_cert_path=site.ssl_certificate.path if site.ssl_certificate else None,
                ssl_key_path=site.ssl_key.path if site.ssl_key else None,
                ssl_chain_path=site.ssl_chain.path if site.ssl_chain else None,
                auto_https_redirect=(site.protocol == 'https')
            )

            # Generate configuration
            config_text = caddy._generate_site_config(caddy_config)

            # Validate configuration
            validation_result = caddy.validate_site_config(caddy_config)
        else:
            messages.warning(request, 'No backend addresses configured')

    except Exception as e:
        messages.error(request, f'Error generating config: {str(e)}')

    context = {
        'site': site,
        'config_text': config_text,
        'validation_result': validation_result,
    }
    return render(request, 'site_management/caddy_config.html', context)


@login_required
def site_ssl_status(request, site_slug):
    """
    Display comprehensive SSL status for a site
    """
    site = get_object_or_404(Site, slug=site_slug)
    ssl_helper = get_ssl_helper()

    # Get SSL information
    ssl_info = ssl_helper.get_site_ssl_info(site)
    warnings = ssl_helper.get_ssl_configuration_warnings(site)
    renewal_status = ssl_helper.get_certificate_renewal_status(site)

    # Get Caddy status
    caddy_status = None
    try:
        caddy = get_caddy_manager()
        caddy_status = caddy.get_site_status(site.host)
    except Exception as e:
        messages.warning(request, f'Could not get Caddy status: {str(e)}')

    context = {
        'site': site,
        'ssl_info': ssl_info,
        'warnings': warnings,
        'renewal_status': renewal_status,
        'caddy_status': caddy_status,
    }

    return render(request, 'site_management/ssl_status.html', context)


@login_required
def export_caddy_logs(request, site_slug):
    """
    Export Caddy logs for a site
    """
    site = get_object_or_404(Site, slug=site_slug)

    try:
        caddy = get_caddy_manager()

        # Create temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tar.gz', delete=False) as tmp:
            output_file = tmp.name

        result = caddy.export_site_logs(site.host, output_file)

        if result['success']:
            # Read and return file
            with open(output_file, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/gzip')
                response['Content-Disposition'] = f'attachment; filename="logs_{site.slug}.tar.gz"'

            # Cleanup
            os.unlink(output_file)

            return response
        else:
            messages.error(request, f'Failed to export logs: {result.get("error")}')

    except Exception as e:
        messages.error(request, f'Error exporting logs: {str(e)}')

    return redirect('site_detail', slug=site_slug)


@login_required
def caddy_cleanup_logs(request):
    """
    Cleanup old Caddy logs
    """
    if request.method == 'POST':
        days = int(request.POST.get('days', 30))

        try:
            caddy = get_caddy_manager()
            result = caddy.cleanup_logs(days)

            if 'error' not in result:
                messages.success(
                    request,
                    f'Cleaned up {result["cleaned_files"]} log files older than {days} days'
                )
            else:
                messages.error(request, result['error'])

        except Exception as e:
            messages.error(request, f'Error cleaning logs: {str(e)}')

    return redirect('caddy_status')


@login_required
def validate_all_certificates(request):
    """
    Validate all SSL certificates for all sites
    """
    ssl_helper = get_ssl_helper()

    sites_with_certs = Site.objects.filter(ssl_certificate__isnull=False)

    results = {
        'total': sites_with_certs.count(),
        'valid': 0,
        'expiring_soon': 0,
        'expired': 0,
        'errors': 0,
        'details': []
    }

    for site in sites_with_certs:
        try:
            renewal_status = ssl_helper.get_certificate_renewal_status(site)

            if renewal_status:
                status = renewal_status['status']
                days = renewal_status['days_until_expiry']

                result = {
                    'site': site.host,
                    'status': status,
                    'days_until_expiry': days,
                    'action': renewal_status['action_required']
                }

                results['details'].append(result)

                if status == 'expired':
                    results['expired'] = results['expired'] + 1
                elif status == 'expiring_soon':
                    results['expiring_soon'] = results['expiring_soon'] + 1
                elif status == 'valid':
                    results['valid'] = results['valid'] + 1
        
        except Exception as e:
            results['errors'] = results['errors'] + 1
            results['details'].append({
                'site': site.host,
                'status': 'error',
                'error': str(e)
            })

    context = {
        'results': results,
    }

    return render(request, 'site_management/certificate_validation.html', context)


