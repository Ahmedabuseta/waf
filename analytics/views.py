from django.views.generic import TemplateView
from django.views.generic.base import View
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
import csv
import json

from .models import RequestAnalytics, ThreatAlert
from .mixins import AnalyticsContextMixin, GoogleAuthRequiredMixin
from site_management.models import Site, Addresses


class DashboardView(GoogleAuthRequiredMixin, AnalyticsContextMixin, TemplateView):
    """Main analytics dashboard"""
    template_name = 'analytics/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        site = ctx['current_site']

        if not site:
            ctx['error'] = 'No sites configured. Please add a site first.'
            return ctx

        analytics = RequestAnalytics.objects.filter(
            site=site,
            timestamp__gte=self.get_start_date()
        )

        ctx.update({
            'total_requests': analytics.count(),
            'blocked_requests': analytics.filter(action_taken='blocked').count(),
            'unique_countries': analytics.values('country_code').distinct().count(),
            'unique_ips': analytics.values('ip_address').distinct().count(),
            'avg_response_time': round(analytics.aggregate(Avg('response_time'))['response_time__avg'] or 0, 2),
            'recent_alerts': ThreatAlert.objects.filter(site=site, is_resolved=False).order_by('-timestamp')[:5],
        })

        total = ctx['total_requests']
        ctx['blocked_percentage'] = (ctx['blocked_requests'] / total * 100) if total > 0 else 0

        return ctx


class GeographicDataAPIView(GoogleAuthRequiredMixin, View):
    """API: Geographic data for map"""

    def get(self, request, site_slug):
        site = Site.objects.get(slug=site_slug)
        days = int(request.GET.get('days', 7))
        start_date = timezone.now() - timedelta(days=days)

        data = RequestAnalytics.objects.filter(
            site=site,
            timestamp__gte=start_date,
            country_code__isnull=False,
            latitude__isnull=False,
        ).values('country', 'country_code', 'latitude', 'longitude').annotate(
            total_requests=Count('id'),
            blocked=Count('id', filter=Q(action_taken='blocked')),
            high_threats=Count('id', filter=Q(threat_level='high')),
            critical_threats=Count('id', filter=Q(threat_level='critical'))
        )

        map_data = [{
            'country': d['country'],
            'country_code': d['country_code'],
            'lat': float(d['latitude']),
            'lng': float(d['longitude']),
            'total_requests': d['total_requests'],
            'blocked': d['blocked'],
            'allowed': d['total_requests'] - d['blocked'],
            'high_threats': d['high_threats'],
            'critical_threats': d['critical_threats'],
            'threat_level': 'critical' if d['critical_threats'] > 0 else ('high' if d['high_threats'] > 0 else 'low')
        } for d in data]

        return JsonResponse({'data': map_data})


class GeographicTableAPIView(GoogleAuthRequiredMixin, View):
    """API: Geographic table data"""

    def get(self, request, site_slug):
        site = Site.objects.get(slug=site_slug)
        days = int(request.GET.get('days', 7))
        start_date = timezone.now() - timedelta(days=days)

        data = RequestAnalytics.objects.filter(
            site=site,
            timestamp__gte=start_date
        ).values('country', 'country_code', 'city').annotate(
            total_requests=Count('id'),
            blocked=Count('id', filter=Q(action_taken='blocked')),
            unique_ips=Count('ip_address', distinct=True),
            avg_response=Avg('response_time')
        ).order_by('-total_requests')[:50]

        table_data = [{
            'country': d['country'] or 'Unknown',
            'country_code': d['country_code'] or 'XX',
            'city': d['city'] or 'Unknown',
            'total_requests': d['total_requests'],
            'blocked': d['blocked'],
            'allowed': d['total_requests'] - d['blocked'],
            'unique_ips': d['unique_ips'],
            'avg_response': round(d['avg_response'] or 0, 2)
        } for d in data]

        return JsonResponse({'data': table_data})


class TimelineAPIView(GoogleAuthRequiredMixin, View):
    """API: Timeline chart data"""

    def get(self, request, site_slug):
        from django.db.models.functions import TruncDate

        site = Site.objects.get(slug=site_slug)
        days = int(request.GET.get('days', 7))
        start_date = timezone.now() - timedelta(days=days)

        timeline = RequestAnalytics.objects.filter(
            site=site,
            timestamp__gte=start_date
        ).annotate(date=TruncDate('timestamp')).values('date').annotate(
            total=Count('id'),
            blocked=Count('id', filter=Q(action_taken='blocked')),
            allowed=Count('id', filter=Q(action_taken='allowed'))
        ).order_by('date')

        return JsonResponse({
            'labels': [t['date'].strftime('%Y-%m-%d') for t in timeline],
            'total': [t['total'] for t in timeline],
            'blocked': [t['blocked'] for t in timeline],
            'allowed': [t['allowed'] for t in timeline]
        })


class TopIPsAPIView(GoogleAuthRequiredMixin, View):
    """API: Top requesting IPs"""

    def get(self, request, site_slug):
        site = Site.objects.get(slug=site_slug)
        days = int(request.GET.get('days', 7))
        start_date = timezone.now() - timedelta(days=days)

        ips = RequestAnalytics.objects.filter(
            site=site,
            timestamp__gte=start_date
        ).values('ip_address', 'country', 'country_code').annotate(
            total_requests=Count('id'),
            blocked=Count('id', filter=Q(action_taken='blocked')),
            is_blacklisted=Count('id', filter=Q(is_blacklisted=True))
        ).order_by('-total_requests')[:20]

        return JsonResponse({'data': [{
            'ip': ip['ip_address'],
            'country': ip['country'] or 'Unknown',
            'country_code': ip['country_code'] or 'XX',
            'requests': ip['total_requests'],
            'blocked': ip['blocked'],
            'is_blacklisted': ip['is_blacklisted'] > 0
        } for ip in ips]})


class RequestMethodsAPIView(GoogleAuthRequiredMixin, View):
    """API: Request methods distribution"""

    def get(self, request, site_slug):
        site = Site.objects.get(slug=site_slug)
        days = int(request.GET.get('days', 7))
        start_date = timezone.now() - timedelta(days=days)

        methods = RequestAnalytics.objects.filter(
            site=site,
            timestamp__gte=start_date
        ).values('request_method').annotate(count=Count('id')).order_by('-count')

        return JsonResponse({
            'labels': [m['request_method'] for m in methods],
            'values': [m['count'] for m in methods]
        })


class BlacklistIPView(GoogleAuthRequiredMixin, View):
    """Add IP to blacklist"""

    def post(self, request, site_slug):
        site = Site.objects.get(slug=site_slug)
        data = json.loads(request.body)
        ip = data.get('ip_address')

        if not ip:
            return JsonResponse({'error': 'IP address required'}, status=400)

        RequestAnalytics.objects.filter(site=site, ip_address=ip).update(is_blacklisted=True)
        Addresses.objects.get_or_create(site=site, ip_address=ip, port=80, defaults={'is_allowed': False})

        return JsonResponse({'success': True, 'message': f'IP {ip} blacklisted'})


class UnblacklistIPView(GoogleAuthRequiredMixin, View):
    """Remove IP from blacklist"""

    def post(self, request, site_slug):
        site = Site.objects.get(slug=site_slug)
        data = json.loads(request.body)
        ip = data.get('ip_address')

        if not ip:
            return JsonResponse({'error': 'IP address required'}, status=400)

        RequestAnalytics.objects.filter(site=site, ip_address=ip).update(is_blacklisted=False)
        Addresses.objects.filter(site=site, ip_address=ip, is_allowed=False).delete()

        return JsonResponse({'success': True, 'message': f'IP {ip} removed from blacklist'})


class ExportCSVView(GoogleAuthRequiredMixin, View):
    """Export analytics as CSV"""

    def get(self, request, site_slug):
        site = Site.objects.get(slug=site_slug)
        days = int(request.GET.get('days', 7))
        start_date = timezone.now() - timedelta(days=days)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="analytics_{site.slug}_{timezone.now().strftime("%Y%m%d")}.csv"'

        writer = csv.writer(response)
        writer.writerow(['Timestamp', 'IP', 'Country', 'City', 'Method', 'URL', 'Status', 'Action', 'Threat', 'Response Time'])

        for a in RequestAnalytics.objects.filter(site=site, timestamp__gte=start_date).order_by('-timestamp'):
            writer.writerow([
                a.timestamp.strftime('%Y-%m-%d %H:%M:%S'), a.ip_address, a.country or '',
                a.city or '', a.request_method, a.request_url, a.status_code,
                a.action_taken, a.threat_level, a.response_time
            ])

        return response


class ExportJSONView(GoogleAuthRequiredMixin, View):
    """Export analytics as JSON"""

    def get(self, request, site_slug):
        site = Site.objects.get(slug=site_slug)
        days = int(request.GET.get('days', 7))
        start_date = timezone.now() - timedelta(days=days)

        data = [{
            'timestamp': a.timestamp.isoformat(),
            'ip_address': a.ip_address,
            'country': a.country,
            'country_code': a.country_code,
            'city': a.city,
            'latitude': float(a.latitude) if a.latitude else None,
            'longitude': float(a.longitude) if a.longitude else None,
            'request_method': a.request_method,
            'request_url': a.request_url,
            'status_code': a.status_code,
            'action_taken': a.action_taken,
            'threat_level': a.threat_level,
            'response_time': a.response_time,
            'is_blacklisted': a.is_blacklisted
        } for a in RequestAnalytics.objects.filter(site=site, timestamp__gte=start_date).order_by('-timestamp')]

        response = HttpResponse(json.dumps(data, indent=2), content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="analytics_{site.slug}_{timezone.now().strftime("%Y%m%d")}.json"'

        return response
