from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
import csv
import json

from .models import (
    Site, RequestAnalytics, GeographicStats, ThreatAlert,
Addresses,WafTemplate, Logs
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
