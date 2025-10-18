from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from django.contrib.auth.decorators import login_required
from django.views.decorators.http  import require_POST
from .models import (
    Site, Addresses, LoadBalancers, WafTemplate,
)

# ============= SITE MANAGEMENT VIEWS =============
@login_required
def sites_list(request):
    """List all sites"""
    sites = Site.objects.all().order_by('-created_at')

    # Get stats for each site
    site_stats = []
    for site in sites:
        stats = {
            'site': site,
            'addresses_count': site.addresses.count(),
            'logs_count': site.logs.count(),
            'has_load_balancer': hasattr(site, 'load_balancer'),
        }
        site_stats.append(stats)

    context = {
        'site_stats': site_stats,
    }
    return render(request, 'site_management/sites_list.html', context)

@login_required
def site_detail(request, slug):
    """Site detail view"""
    site = get_object_or_404(Site, slug=slug)

    # Get related data
    addresses = site.addresses.all().order_by('-created_at')
    recent_logs = site.logs.all().order_by('-timestamp')[:50]
    has_load_balancer = hasattr(site, 'load_balancer')
    load_balancer = site.load_balancer if has_load_balancer else None

    context = {
        'site': site,
        'addresses': addresses,
        'recent_logs': recent_logs,
        'load_balancer': load_balancer,
    }
    return render(request, 'site_management/site_detail.html', context)

@login_required
def site_add(request):
    """Add new site with enhanced SSL validation"""
    from .forms import SiteForm

    if request.method == 'POST':
        form = SiteForm(request.POST, request.FILES)

        if form.is_valid():
            site = form.save()
            messages.success(request, f'Site {site.host} added successfully!')

            # Check if DNS challenge is required
            dns_challenge_info = form.get_dns_challenge_info()
            if dns_challenge_info and dns_challenge_info.get('required'):
                messages.info(
                    request,
                    'DNS challenge required for wildcard certificate. '
                    'Please configure DNS TXT record.'
                )
                # Store DNS challenge info in session
                request.session['dns_challenge_info'] = dns_challenge_info
                return redirect('dns_challenge', site_slug=site.slug)

            return redirect('site_detail', slug=site.slug)
        else:
            # Form validation failed, display errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = SiteForm()

    waf_templates = WafTemplate.objects.all()
    context = {
        'form': form,
        'waf_templates': waf_templates,
    }
    return render(request, 'site_management/site_form_enhanced.html', context)

@login_required
def site_edit(request, slug):
    """Edit existing site with enhanced SSL validation"""
    from .forms import SiteForm

    site = get_object_or_404(Site, slug=slug)

    if request.method == 'POST':
        form = SiteForm(request.POST, request.FILES, instance=site)

        if form.is_valid():
            site = form.save()
            messages.success(request, f'Site {site.host} updated successfully!')

            # Check if DNS challenge is required
            dns_challenge_info = form.get_dns_challenge_info()
            if dns_challenge_info and dns_challenge_info.get('required'):
                messages.info(
                    request,
                    'DNS challenge required for wildcard certificate. '
                    'Please configure DNS TXT record.'
                )
                request.session['dns_challenge_info'] = dns_challenge_info
                return redirect('dns_challenge', site_slug=site.slug)

            return redirect('site_detail', slug=site.slug)
        else:
            # Form validation failed, display errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = SiteForm(instance=site)

    waf_templates = WafTemplate.objects.all()
    context = {
        'form': form,
        'site': site,
        'waf_templates': waf_templates,
        'is_edit': True,
    }
    return render(request, 'site_management/site_form_enhanced.html', context)


@require_POST
@login_required
def site_delete(request, slug):
    """Delete site"""
    site = get_object_or_404(Site, slug=slug)
    host = site.host
    site.delete()
    messages.success(request, f'Site {host} deleted successfully!')
    return redirect('sites_list')


# ============= ADDRESS MANAGEMENT =============
@login_required
def address_add(request, site_slug):
    """Add address to site"""
    site = get_object_or_404(Site, slug=site_slug)

    if request.method == 'POST':
        ip_address = request.POST.get('ip_address')
        port = request.POST.get('port', 80)
        is_allowed = request.POST.get('is_allowed') == 'on'

        Addresses.objects.create(
            site=site,
            ip_address=ip_address,
            port=port,
            is_allowed=is_allowed
        )

        action = "allowlist" if is_allowed else "blocklist"
        messages.success(request, f'IP {ip_address}:{port} added to {action}')
        return redirect('site_detail', slug=site.slug)

    context = {
        'site': site,
    }
    return render(request, 'site_management/address_form.html', context)

@login_required
@require_POST
def address_delete(request, address_id):
    """Delete address"""
    address = get_object_or_404(Addresses, id=address_id)
    site_slug = address.site.slug
    address.delete()
    messages.success(request, f'Address removed successfully!')
    return redirect('site_detail', slug=site_slug)


# ============= LOAD BALANCER MANAGEMENT =============
# get or add or edit load balancer
@login_required
def load_balancer_add(request, site_slug):
    """Add or edit load balancer for site"""
    site = get_object_or_404(Site, slug=site_slug)
    lb, created = LoadBalancers.objects.get_or_create(site=site)

    if request.method == 'POST':
        lb.algorithm = request.POST.get('algorithm', 'round_robin')
        lb.health_check_url = request.POST.get('health_check_url')
        lb.save()
        messages.success(request, f'Load balancer {"updated" if not created else "created"}!')
        return redirect('site_detail', slug=site.slug)

    return render(request, 'load_balancer_form.html', {'site': site, 'load_balancer': lb, 'is_edit': not created})

# delete load balancer
@login_required
@require_POST
def load_balancer_delete(request, site_slug):
    """Delete load balancer"""
    site = get_object_or_404(Site, slug=site_slug)
    if hasattr(site, 'load_balancer'):
        site.load_balancer.delete()
        messages.success(request, 'Load balancer deleted successfully!')
    return redirect('site_detail', slug=site.slug)
