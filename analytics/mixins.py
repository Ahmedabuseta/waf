from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from site_management.models import Site


class AnalyticsContextMixin:
    """Mixin to provide common analytics context"""

    def get_site(self):
        slug = self.kwargs.get('site_slug')
        return get_object_or_404(Site, slug=slug) if slug else Site.objects.first()

    def get_days(self):
        return int(self.request.GET.get('days', 7))

    def get_start_date(self):
        return timezone.now() - timedelta(days=self.get_days())

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['current_site'] = self.get_site()
        ctx['sites'] = Site.objects.all()
        ctx['days'] = self.get_days()
        return ctx


class SiteFilterMixin:
    """Mixin to filter queryset by site"""

    def get_queryset(self):
        qs = super().get_queryset()
        site = get_object_or_404(Site, slug=self.kwargs['site_slug'])
        return qs.filter(site=site)


class TimeRangeFilterMixin:
    """Mixin to filter by time range"""

    def get_queryset(self):
        qs = super().get_queryset()
        days = int(self.request.GET.get('days', 7))
        start_date = timezone.now() - timedelta(days=days)
        return qs.filter(timestamp__gte=start_date)


class GoogleAuthRequiredMixin(LoginRequiredMixin):
    """Require Google OAuth authentication"""
    login_url = '/auth/login/google/'
    redirect_field_name = 'next'
