
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
