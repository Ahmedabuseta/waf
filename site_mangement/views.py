from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from django.utils.text import slugify
from datetime import timedelta
import csv
import json

from .models import (
    Site, RequestAnalytics, GeographicStats, ThreatAlert,
    EmailReport, Addresses, LoadBalancers, WafTemplate, Logs
)


def index(request):
    """Home page with real-time stats"""
    context = {
        'sites_count': Site.objects.count(),
        'templates_count': WafTemplate.objects.count(),
        'logs_count': Logs.objects.count(),
        'total_requests': RequestAnalytics.objects.count(),
        'blocked_today': RequestAnalytics.objects.filter(
            timestamp__gte=timezone.now().date(),
            action_taken='blocked'
        ).count(),
    }
    return render(request, 'index.html', context)


def analytics_dashboard(request, site_slug=None):
    """Main analytics dashboard with geographic visualization"""
    sites = Site.objects.all()

    # Get site or default to first one
    if site_slug:
        site = get_object_or_404(Site, slug=site_slug)
    else:
        site = sites.first()
        # Redirect to the first site's URL if no slug provided
        if site:
            days = request.GET.get('days', 7)
            return redirect(f'/analytics/{site.slug}/?days={days}')

    if not site:
        return render(request, 'analytics/dashboard.html', {
            'error': 'No sites configured. Please add a site first.'
        })

    # Time range filter (default: last 7 days)
    days = int(request.GET.get('days', 7))
    start_date = timezone.now() - timedelta(days=days)

    # Get analytics for the site
    analytics_qs = RequestAnalytics.objects.filter(
        site=site,
        timestamp__gte=start_date
    )

    # Calculate key metrics
    total_requests = analytics_qs.count()
    blocked_requests = analytics_qs.filter(action_taken='blocked').count()
    unique_countries = analytics_qs.values('country_code').distinct().count()
    unique_ips = analytics_qs.values('ip_address').distinct().count()
    avg_response_time = analytics_qs.aggregate(Avg('response_time'))['response_time__avg'] or 0

    # Get recent threat alerts
    recent_alerts = ThreatAlert.objects.filter(
        site=site,
        is_resolved=False
    ).order_by('-timestamp')[:5]

    context = {
        'sites': sites,
        'current_site': site,
        'days': days,
        'total_requests': total_requests,
        'blocked_requests': blocked_requests,
        'blocked_percentage': (blocked_requests / total_requests * 100) if total_requests > 0 else 0,
        'unique_countries': unique_countries,
        'unique_ips': unique_ips,
        'avg_response_time': round(avg_response_time, 2),
        'recent_alerts': recent_alerts,
    }

    return render(request, 'analytics/dashboard.html', context)


def api_geographic_data(request, site_slug):
    """API endpoint to get geographic data for map visualization"""
    site = get_object_or_404(Site, slug=site_slug)

    days = int(request.GET.get('days', 7))
    start_date = timezone.now() - timedelta(days=days)

    # Get geographic data grouped by country
    from django.db.models import Min
    geo_data = RequestAnalytics.objects.filter(
        site=site,
        timestamp__gte=start_date,
        country_code__isnull=False
    ).values(
        'country', 'country_code'
    ).annotate(
        total_requests=Count('id'),
        blocked=Count('id', filter=Q(action_taken='blocked')),
        high_threats=Count('id', filter=Q(threat_level='high')),
        critical_threats=Count('id', filter=Q(threat_level='critical')),
        lat=Min('latitude'),
        lng=Min('longitude')
    )

    # Format for frontend
    map_data = []
    for item in geo_data:
        map_data.append({
            'country': item['country'],
            'country_code': item['country_code'],
            'lat': float(item['lat']),
            'lng': float(item['lng']),
            'total_requests': item['total_requests'],
            'blocked': item['blocked'],
            'allowed': item['total_requests'] - item['blocked'],
            'high_threats': item['high_threats'],
            'critical_threats': item['critical_threats'],
            'threat_level': 'critical' if item['critical_threats'] > 0 else ('high' if item['high_threats'] > 0 else 'low')
        })

    return JsonResponse({'data': map_data})


def api_geographic_table(request, site_slug):
    """API endpoint for geographic breakdown table"""
    site = get_object_or_404(Site, slug=site_slug)

    days = int(request.GET.get('days', 7))
    start_date = timezone.now() - timedelta(days=days)

    # Get data grouped by country and city
    geo_table = RequestAnalytics.objects.filter(
        site=site,
        timestamp__gte=start_date
    ).values(
        'country', 'country_code', 'city'
    ).annotate(
        total_requests=Count('id'),
        blocked=Count('id', filter=Q(action_taken='blocked')),
        unique_ips=Count('ip_address', distinct=True),
        avg_response=Avg('response_time')
    ).order_by('-total_requests')[:50]

    table_data = []
    for item in geo_table:
        table_data.append({
            'country': item['country'] or 'Unknown',
            'country_code': item['country_code'] or 'XX',
            'city': item['city'] or 'Unknown',
            'total_requests': item['total_requests'],
            'blocked': item['blocked'],
            'allowed': item['total_requests'] - item['blocked'],
            'unique_ips': item['unique_ips'],
            'avg_response': round(item['avg_response'] or 0, 2)
        })

    return JsonResponse({'data': table_data})


def api_timeline_data(request, site_slug):
    """API endpoint for requests timeline chart"""
    site = get_object_or_404(Site, slug=site_slug)

    days = int(request.GET.get('days', 7))
    start_date = timezone.now() - timedelta(days=days)

    # Group by date
    from django.db.models.functions import TruncDate

    timeline = RequestAnalytics.objects.filter(
        site=site,
        timestamp__gte=start_date
    ).annotate(
        date=TruncDate('timestamp')
    ).values('date').annotate(
        total=Count('id'),
        blocked=Count('id', filter=Q(action_taken='blocked')),
        allowed=Count('id', filter=Q(action_taken='allowed'))
    ).order_by('date')

    chart_data = {
        'labels': [item['date'].strftime('%Y-%m-%d') for item in timeline],
        'total': [item['total'] for item in timeline],
        'blocked': [item['blocked'] for item in timeline],
        'allowed': [item['allowed'] for item in timeline]
    }

    return JsonResponse(chart_data)


def api_top_ips(request, site_slug):
    """API endpoint for top requesting IPs"""
    site = get_object_or_404(Site, slug=site_slug)

    days = int(request.GET.get('days', 7))
    start_date = timezone.now() - timedelta(days=days)

    top_ips = RequestAnalytics.objects.filter(
        site=site,
        timestamp__gte=start_date
    ).values(
        'ip_address', 'country', 'country_code'
    ).annotate(
        total_requests=Count('id'),
        blocked=Count('id', filter=Q(action_taken='blocked')),
        is_blacklisted=Count('id', filter=Q(is_blacklisted=True))
    ).order_by('-total_requests')[:20]

    ips_data = []
    for item in top_ips:
        ips_data.append({
            'ip': item['ip_address'],
            'country': item['country'] or 'Unknown',
            'country_code': item['country_code'] or 'XX',
            'requests': item['total_requests'],
            'blocked': item['blocked'],
            'is_blacklisted': item['is_blacklisted'] > 0
        })

    return JsonResponse({'data': ips_data})


def api_request_methods(request, site_slug):
    """API endpoint for request methods distribution"""
    site = get_object_or_404(Site, slug=site_slug)

    days = int(request.GET.get('days', 7))
    start_date = timezone.now() - timedelta(days=days)

    methods = RequestAnalytics.objects.filter(
        site=site,
        timestamp__gte=start_date
    ).values('request_method').annotate(
        count=Count('id')
    ).order_by('-count')

    methods_data = {
        'labels': [item['request_method'] for item in methods],
        'values': [item['count'] for item in methods]
    }

    return JsonResponse(methods_data)


@require_http_methods(["POST"])
def blacklist_ip(request, site_slug):
    """Add IP to blacklist"""
    site = get_object_or_404(Site, slug=site_slug)

    data = json.loads(request.body)
    ip_address = data.get('ip_address')

    if not ip_address:
        return JsonResponse({'error': 'IP address required'}, status=400)

    # Mark all analytics for this IP as blacklisted
    RequestAnalytics.objects.filter(
        site=site,
        ip_address=ip_address
    ).update(is_blacklisted=True)

    # Add to blocked addresses
    Addresses.objects.get_or_create(
        site=site,
        ip_address=ip_address,
        port=80,  # Default port
        defaults={'is_allowed': False}
    )

    return JsonResponse({'success': True, 'message': f'IP {ip_address} blacklisted'})


@require_http_methods(["POST"])
def remove_from_blacklist(request, site_slug):
    """Remove IP from blacklist"""
    site = get_object_or_404(Site, slug=site_slug)

    data = json.loads(request.body)
    ip_address = data.get('ip_address')

    if not ip_address:
        return JsonResponse({'error': 'IP address required'}, status=400)

    # Unmark analytics
    RequestAnalytics.objects.filter(
        site=site,
        ip_address=ip_address
    ).update(is_blacklisted=False)

    # Remove from blocked addresses
    Addresses.objects.filter(
        site=site,
        ip_address=ip_address,
        is_allowed=False
    ).delete()

    return JsonResponse({'success': True, 'message': f'IP {ip_address} removed from blacklist'})


def export_analytics_csv(request, site_slug):
    """Export analytics data as CSV"""
    site = get_object_or_404(Site, slug=site_slug)

    days = int(request.GET.get('days', 7))
    start_date = timezone.now() - timedelta(days=days)

    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="analytics_{site.slug}_{timezone.now().strftime("%Y%m%d")}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Timestamp', 'IP Address', 'Country', 'City', 'Request Method',
        'Request URL', 'Status Code', 'Action Taken', 'Threat Level',
        'Response Time (ms)', 'User Agent'
    ])

    analytics = RequestAnalytics.objects.filter(
        site=site,
        timestamp__gte=start_date
    ).order_by('-timestamp')

    for item in analytics:
        writer.writerow([
            item.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            item.ip_address,
            item.country or '',
            item.city or '',
            item.request_method,
            item.request_url,
            item.status_code,
            item.action_taken,
            item.threat_level,
            item.response_time,
            item.user_agent or ''
        ])

    return response


def export_analytics_json(request, site_slug):
    """Export analytics data as JSON"""
    site = get_object_or_404(Site, slug=site_slug)

    days = int(request.GET.get('days', 7))
    start_date = timezone.now() - timedelta(days=days)

    analytics = RequestAnalytics.objects.filter(
        site=site,
        timestamp__gte=start_date
    ).order_by('-timestamp')

    data = []
    for item in analytics:
        data.append({
            'timestamp': item.timestamp.isoformat(),
            'ip_address': item.ip_address,
            'country': item.country,
            'country_code': item.country_code,
            'city': item.city,
            'latitude': float(item.latitude) if item.latitude else None,
            'longitude': float(item.longitude) if item.longitude else None,
            'request_method': item.request_method,
            'request_url': item.request_url,
            'status_code': item.status_code,
            'action_taken': item.action_taken,
            'threat_level': item.threat_level,
            'threat_type': item.threat_type,
            'response_time': item.response_time,
            'user_agent': item.user_agent,
            'is_blacklisted': item.is_blacklisted
        })

    response = HttpResponse(
        json.dumps(data, indent=2),
        content_type='application/json'
    )
    response['Content-Disposition'] = f'attachment; filename="analytics_{site.slug}_{timezone.now().strftime("%Y%m%d")}.json"'

    return response


# ============= SITE MANAGEMENT VIEWS =============

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


@require_http_methods(["POST"])
def site_delete(request, slug):
    """Delete site"""
    site = get_object_or_404(Site, slug=slug)
    host = site.host
    site.delete()
    messages.success(request, f'Site {host} deleted successfully!')
    return redirect('sites_list')


# ============= ADDRESS MANAGEMENT =============

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


@require_http_methods(["POST"])
def address_delete(request, address_id):
    """Delete address"""
    address = get_object_or_404(Addresses, id=address_id)
    site_slug = address.site.slug
    address.delete()
    messages.success(request, f'Address removed successfully!')
    return redirect('site_detail', slug=site_slug)


# ============= LOAD BALANCER MANAGEMENT =============

def load_balancer_add(request, site_slug):
    """Add or edit load balancer for site"""
    site = get_object_or_404(Site, slug=site_slug)

    # Check if load balancer exists
    has_load_balancer = hasattr(site, 'load_balancer')
    load_balancer = site.load_balancer if has_load_balancer else None

    if request.method == 'POST':
        algorithm = request.POST.get('algorithm', 'round_robin')
        health_check_url = request.POST.get('health_check_url')

        if load_balancer:
            load_balancer.algorithm = algorithm
            load_balancer.health_check_url = health_check_url
            load_balancer.save()
            messages.success(request, 'Load balancer updated successfully!')
        else:
            LoadBalancers.objects.create(
                site=site,
                algorithm=algorithm,
                health_check_url=health_check_url
            )
            messages.success(request, 'Load balancer created successfully!')

        return redirect('site_detail', slug=site.slug)

    context = {
        'site': site,
        'load_balancer': load_balancer,
        'is_edit': has_load_balancer,
    }
    return render(request, 'site_management/load_balancer_form.html', context)


@require_http_methods(["POST"])
def load_balancer_delete(request, site_slug):
    """Delete load balancer"""
    site = get_object_or_404(Site, slug=site_slug)
    if hasattr(site, 'load_balancer'):
        site.load_balancer.delete()
        messages.success(request, 'Load balancer deleted successfully!')
    return redirect('site_detail', slug=site.slug)


# ============= WAF TEMPLATE MANAGEMENT =============

def waf_templates_list(request):
    """List all WAF templates"""
    templates = WafTemplate.objects.all().order_by('-created_at')

    # Get sites count for each template
    template_stats = []
    for template in templates:
        stats = {
            'template': template,
            'sites_count': template.sites.count(),
        }
        template_stats.append(stats)

    context = {
        'template_stats': template_stats,
    }
    return render(request, 'site_management/waf_templates_list.html', context)


def waf_template_add(request):
    """Add new WAF template"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        template_type = request.POST.get('template_type', 'basic')

        WafTemplate.objects.create(
            name=name,
            description=description,
            template_type=template_type
        )

        messages.success(request, f'WAF template "{name}" created successfully!')
        return redirect('waf_templates_list')

    return render(request, 'site_management/waf_template_form.html')


def waf_template_detail(request, template_id):
    """View WAF template details"""
    template = get_object_or_404(WafTemplate, id=template_id)

    # Get all sites using this template
    sites = template.sites.all().order_by('host')

    context = {
        'template': template,
        'sites': sites,
        'sites_count': sites.count(),
    }
    return render(request, 'site_management/waf_template_detail.html', context)


def waf_template_edit(request, template_id):
    """Edit WAF template"""
    template = get_object_or_404(WafTemplate, id=template_id)

    if request.method == 'POST':
        template.name = request.POST.get('name')
        template.description = request.POST.get('description')
        template.template_type = request.POST.get('template_type', 'basic')
        template.save()

        messages.success(request, f'WAF template "{template.name}" updated successfully!')
        return redirect('waf_templates_list')

    context = {
        'template': template,
        'is_edit': True,
    }
    return render(request, 'site_management/waf_template_form.html', context)


@require_http_methods(["POST"])
def waf_template_delete(request, template_id):
    """Delete WAF template"""
    template = get_object_or_404(WafTemplate, id=template_id)
    name = template.name
    template.delete()
    messages.success(request, f'WAF template "{name}" deleted successfully!')
    return redirect('waf_templates_list')


# ============= LOGS MANAGEMENT =============

def logs_list(request):
    """List and filter logs"""
    logs = Logs.objects.all().order_by('-timestamp')

    # Filters
    site_slug = request.GET.get('site')
    action = request.GET.get('action')
    ip = request.GET.get('ip')
    method = request.GET.get('request_method')

    if site_slug:
        logs = logs.filter(site__slug=site_slug)
    if action:
        logs = logs.filter(action_taken=action)
    if ip:
        logs = logs.filter(ip_address__icontains=ip)
    if method:
        logs = logs.filter(request_method=method)

    # Pagination (limit to 100 records)
    logs = logs[:100]

    # Get filter options
    sites = Site.objects.all()

    context = {
        'logs': logs,
        'sites': sites,
        'selected_site': site_slug,
        'selected_action': action,
        'selected_ip': ip,
        'selected_method': method,
    }
    return render(request, 'site_management/logs_list.html', context)


def log_detail(request, log_id):
    """Log detail view"""
    log = get_object_or_404(Logs, id=log_id)

    context = {
        'log': log,
    }
    return render(request, 'site_management/log_detail.html', context)


@require_http_methods(["POST"])
def logs_clear(request, site_slug):
    """Clear all logs for a site"""
    site = get_object_or_404(Site, slug=site_slug)
    count = site.logs.count()
    site.logs.all().delete()
    messages.success(request, f'Cleared {count} logs for site {site.host}')
    return redirect('logs_list')
