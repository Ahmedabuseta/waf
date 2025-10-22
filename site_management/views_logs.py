
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from .models import (
    Site, Logs
)

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
