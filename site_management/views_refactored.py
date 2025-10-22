"""
Refactored views using DRY principles with class-based views
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.views import View
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.db.models import Count, Q

from .models import (
    Site, RequestAnalytics,  ThreatAlert,
 Addresses,WafTemplate, Logs
)
from .forms import SiteForm, AddressForm, LoadBalancerForm, WafTemplateForm
from .mixins import SiteRequiredMixin, SuccessMessageMixin
from site_management.utils.utils_common import (
   get_days_from_request,
 format_response_time
)


# ============= HOME & ANALYTICS =============

class IndexView(TemplateView):
    """Home page dashboard"""
    template_name = 'index.html'


class AnalyticsDashboardView(TemplateView):
    """Main analytics dashboard with geographic visualization"""
    template_name = 'analytics/dashboard.html'

    def get_site(self):
        """Get site from slug or first site"""
        site_slug = self.kwargs.get('site_slug')
        if site_slug:
            return get_object_or_404(Site, slug=site_slug)
        return Site.objects.first()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        site = self.get_site()

        if not site:
            context['error'] = 'No sites configured. Please add a site first.'
            return context

        days = get_days_from_request(self.request)
        metrics = RequestAnalytics.objects.get_metrics(site=site, days=days)

        context.update({
            'sites': Site.objects.all(),
            'current_site': site,
            'days': days,
            'recent_alerts': ThreatAlert.objects.filter(
                site=site, is_resolved=False
            ).order_by('-timestamp')[:5],
            **metrics,
        })
        return context


# ============= API VIEWS =============

class BaseAPIView(View):
    """Base view for API endpoints"""

    def get_site(self):
        return get_object_or_404(Site, slug=self.kwargs['site_slug'])

    def get_days(self):
        return get_days_from_request(self.request)

    def get_analytics_queryset(self):
        site = self.get_site()
        days = self.get_days()
        return RequestAnalytics.objects.for_site(site).recent(days)


class GeographicDataAPIView(BaseAPIView):
    """API endpoint for geographic data"""

    def get(self, request, site_slug):
        geo_data = self.get_analytics_queryset().filter(
            country_code__isnull=False,
            latitude__isnull=False,
            longitude__isnull=False
        ).values(
            'country', 'country_code', 'latitude', 'longitude'
        ).annotate(
            total_requests=Count('id'),
            blocked=Count('id', filter=Q(action_taken='blocked')),
            high_threats=Count('id', filter=Q(threat_level='high')),
            critical_threats=Count('id', filter=Q(threat_level='critical'))
        )

        map_data = [{
            'country': item['country'],
            'country_code': item['country_code'],
            'lat': float(item['latitude']),
            'lng': float(item['longitude']),
            'total_requests': item['total_requests'],
            'blocked': item['blocked'],
            'allowed': item['total_requests'] - item['blocked'],
            'high_threats': item['high_threats'],
            'critical_threats': item['critical_threats'],
            'threat_level': 'critical' if item['critical_threats'] > 0 else (
                'high' if item['high_threats'] > 0 else 'low'
            )
        } for item in geo_data]

        return JsonResponse({'data': map_data})


class GeographicTableAPIView(BaseAPIView):
    """API endpoint for geographic table"""

    def get(self, request, site_slug):
        geo_table = self.get_analytics_queryset().values(
            'country', 'country_code', 'city'
        ).annotate(
            total_requests=Count('id'),
            blocked=Count('id', filter=Q(action_taken='blocked')),
            unique_ips=Count('ip_address', distinct=True),
            avg_response=Q('response_time')
        ).order_by('-total_requests')[:50]

        table_data = [{
            'country': item['country'] or 'Unknown',
            'country_code': item['country_code'] or 'XX',
            'city': item['city'] or 'Unknown',
            'total_requests': item['total_requests'],
            'blocked': item['blocked'],
            'allowed': item['total_requests'] - item['blocked'],
            'unique_ips': item['unique_ips'],
            'avg_response': format_response_time(item.get('avg_response') or 0)
        } for item in geo_table]

        return JsonResponse({'data': table_data})


# ============= SITE MANAGEMENT =============

class SiteListView(ListView):
    """List all sites with stats"""
    model = Site
    template_name = 'site_management/sites_list.html'
    context_object_name = 'sites'

    def get_queryset(self):
        return Site.objects.with_stats().order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Transform to site_stats format for template
        context['site_stats'] = [{
            'site': site,
            'addresses_count': site.addresses_count,
            'logs_count': site.logs_count,
            'has_load_balancer': hasattr(site, 'load_balancer'),
        } for site in context['sites']]
        return context


class SiteDetailView(DetailView):
    """Site detail view"""
    model = Site
    template_name = 'site_management/site_detail.html'
    context_object_name = 'site'
    slug_field = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['addresses'] = self.object.addresses.all().order_by('-created_at')
        context['recent_logs'] = self.object.logs.recent(50)
        context['load_balancer'] = getattr(self.object, 'load_balancer', None)
        return context


class SiteCreateView(SuccessMessageMixin, CreateView):
    """Create new site"""
    model = Site
    form_class = SiteForm
    template_name = 'site_management/site_form.html'
    success_message = "Site {host} added successfully!"

    def get_success_url(self):
        return reverse('site_detail', kwargs={'slug': self.object.slug})

    def get_success_message(self):
        return self.success_message.format(host=self.object.host)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['waf_templates'] = WafTemplate.objects.all()
        return context


class SiteUpdateView(SuccessMessageMixin, UpdateView):
    """Update existing site"""
    model = Site
    form_class = SiteForm
    template_name = 'site_management/site_form.html'
    slug_field = 'slug'
    success_message = "Site {host} updated successfully!"

    def get_success_url(self):
        return reverse('site_detail', kwargs={'slug': self.object.slug})

    def get_success_message(self):
        return self.success_message.format(host=self.object.host)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['waf_templates'] = WafTemplate.objects.all()
        context['is_edit'] = True
        return context


class SiteDeleteView(DeleteView):
    """Delete site"""
    model = Site
    slug_field = 'slug'
    success_url = reverse_lazy('sites_list')

    def post(self, request, *args, **kwargs):
        site = self.get_object()
        host = site.host
        site.delete()
        messages.success(request, f'Site {host} deleted successfully!')
        return redirect(self.success_url)


# ============= ADDRESS MANAGEMENT =============

class AddressCreateView(SiteRequiredMixin, CreateView):
    """Add address to site"""
    model = Addresses
    form_class = AddressForm
    template_name = 'site_management/address_form.html'

    def form_valid(self, form):
        form.instance.site = self.site
        response = super().form_valid(form)
        action = "allowlist" if form.instance.is_allowed else "blocklist"
        messages.success(
            self.request,
            f'IP {form.instance.ip_address}:{form.instance.port} added to {action}'
        )
        return response

    def get_success_url(self):
        return reverse('site_detail', kwargs={'slug': self.site.slug})


class AddressDeleteView(DeleteView):
    """Delete address"""
    model = Addresses
    pk_url_kwarg = 'address_id'

    def get_success_url(self):
        return reverse('site_detail', kwargs={'slug': self.object.site.slug})

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        success_url = self.get_success_url()
        obj.delete()
        messages.success(request, 'Address removed successfully!')
        return redirect(success_url)


# ============= LOAD BALANCER MANAGEMENT =============

class LoadBalancerManageView(SiteRequiredMixin, View):
    """Add or edit load balancer"""
    template_name = 'site_management/load_balancer_form.html'

    def get_load_balancer(self):
        return getattr(self.site, 'load_balancer', None)

    def get(self, request, site_slug):
        form = LoadBalancerForm(instance=self.get_load_balancer())
        return render(request, self.template_name, {
            'form': form,
            'site': self.site,
            'load_balancer': self.get_load_balancer(),
            'is_edit': self.get_load_balancer() is not None,
        })

    def post(self, request, site_slug):
        lb = self.get_load_balancer()
        form = LoadBalancerForm(request.POST, instance=lb)

        if form.is_valid():
            load_balancer = form.save(commit=False)
            load_balancer.site = self.site
            load_balancer.save()

            msg = 'Load balancer updated' if lb else 'Load balancer created'
            messages.success(request, f'{msg} successfully!')
            return redirect('site_detail', slug=self.site.slug)

        return render(request, self.template_name, {
            'form': form,
            'site': self.site,
            'load_balancer': lb,
            'is_edit': lb is not None,
        })


# ============= WAF TEMPLATE MANAGEMENT =============

class WafTemplateListView(ListView):
    """List all WAF templates"""
    model = WafTemplate
    template_name = 'site_management/waf_templates_list.html'
    context_object_name = 'templates'

    def get_queryset(self):
        return WafTemplate.objects.annotate(
            sites_count=Count('sites')
        ).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['template_stats'] = [{
            'template': template,
            'sites_count': template.sites_count,
        } for template in context['templates']]
        return context


class WafTemplateCreateView(SuccessMessageMixin, CreateView):
    """Create WAF template"""
    model = WafTemplate
    form_class = WafTemplateForm
    template_name = 'site_management/waf_template_form.html'
    success_url = reverse_lazy('waf_templates_list')
    success_message = 'WAF template "{name}" created successfully!'

    def get_success_message(self):
        return self.success_message.format(name=self.object.name)


class WafTemplateUpdateView(SuccessMessageMixin, UpdateView):
    """Update WAF template"""
    model = WafTemplate
    form_class = WafTemplateForm
    template_name = 'site_management/waf_template_form.html'
    pk_url_kwarg = 'template_id'
    success_url = reverse_lazy('waf_templates_list')
    success_message = 'WAF template "{name}" updated successfully!'

    def get_success_message(self):
        return self.success_message.format(name=self.object.name)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = True
        return context


# ============= LOGS MANAGEMENT =============

class LogsListView(ListView):
    """List and filter logs"""
    model = Logs
    template_name = 'site_management/logs_list.html'
    context_object_name = 'logs'

    def get_queryset(self):
        qs = Logs.objects.all().order_by('-timestamp')

        # Apply filters
        if site_slug := self.request.GET.get('site'):
            qs = qs.filter(site__slug=site_slug)
        if action := self.request.GET.get('action'):
            qs = qs.filter(action_taken=action)
        if ip := self.request.GET.get('ip'):
            qs = qs.filter(ip_address__icontains=ip)
        if method := self.request.GET.get('request_method'):
            qs = qs.filter(request_method=method)

        return qs[:100]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'sites': Site.objects.all(),
            'selected_site': self.request.GET.get('site'),
            'selected_action': self.request.GET.get('action'),
            'selected_ip': self.request.GET.get('ip'),
            'selected_method': self.request.GET.get('request_method'),
        })
        return context


class LogDetailView(DetailView):
    """Log detail view"""
    model = Logs
    template_name = 'site_management/log_detail.html'
    pk_url_kwarg = 'log_id'
    context_object_name = 'log'


# Keep the old function-based views for backwards compatibility
# Import them from the refactored views
index = IndexView.as_view()
analytics_dashboard = AnalyticsDashboardView.as_view()
api_geographic_data = GeographicDataAPIView.as_view()
api_geographic_table = GeographicTableAPIView.as_view()
sites_list = SiteListView.as_view()
site_detail = SiteDetailView.as_view()
site_add = SiteCreateView.as_view()
site_edit = SiteUpdateView.as_view()
site_delete = SiteDeleteView.as_view()
address_add = AddressCreateView.as_view()
address_delete = AddressDeleteView.as_view()
load_balancer_add = LoadBalancerManageView.as_view()
waf_templates_list = WafTemplateListView.as_view()
waf_template_add = WafTemplateCreateView.as_view()
waf_template_edit = WafTemplateUpdateView.as_view()
logs_list = LogsListView.as_view()
log_detail = LogDetailView.as_view()
