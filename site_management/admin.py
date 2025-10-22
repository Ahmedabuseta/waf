from django.contrib import admin
from .models import (
    Site, Addresses, LoadBalancers, WafTemplate, Logs,
    RequestAnalytics, GeographicStats, ThreatAlert, EmailReport
)


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ['host', 'status', 'protocol', 'auto_ssl', 'created_at']
    list_filter = ['status', 'protocol', 'auto_ssl']
    search_fields = ['host', 'slug']
    prepopulated_fields = {'slug': ('host',)}


@admin.register(Addresses)
class AddressesAdmin(admin.ModelAdmin):
    list_display = ['ip_address', 'port', 'site', 'is_allowed', 'created_at']
    list_filter = ['is_allowed', 'site']
    search_fields = ['ip_address']


@admin.register(LoadBalancers)
class LoadBalancersAdmin(admin.ModelAdmin):
    list_display = ['site', 'algorithm', 'health_check_url', 'created_at']
    list_filter = ['algorithm']


@admin.register(WafTemplate)
class WafTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'template_type', 'created_at']
    list_filter = ['template_type']
    search_fields = ['name', 'description']


@admin.register(Logs)
class LogsAdmin(admin.ModelAdmin):
    list_display = ['id', 'site', 'ip_address', 'request_method', 'action_taken', 'timestamp']
    list_filter = ['action_taken', 'request_method', 'site']
    search_fields = ['ip_address', 'request_url']
    date_hierarchy = 'timestamp'


@admin.register(RequestAnalytics)
class RequestAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['ip_address', 'country', 'city', 'action_taken', 'threat_level', 'timestamp', 'site']
    list_filter = ['action_taken', 'threat_level', 'country_code', 'is_blacklisted', 'site']
    search_fields = ['ip_address', 'country', 'city', 'request_url']
    date_hierarchy = 'timestamp'
    readonly_fields = ['timestamp']


@admin.register(GeographicStats)
class GeographicStatsAdmin(admin.ModelAdmin):
    list_display = ['country', 'date', 'total_requests', 'blocked_requests', 'unique_ips', 'site']
    list_filter = ['date', 'country_code', 'site']
    search_fields = ['country']
    date_hierarchy = 'date'


@admin.register(ThreatAlert)
class ThreatAlertAdmin(admin.ModelAdmin):
    list_display = ['alert_type', 'severity', 'ip_address', 'country_code', 'is_resolved', 'is_notified', 'timestamp', 'site']
    list_filter = ['alert_type', 'severity', 'is_resolved', 'is_notified', 'site']
    search_fields = ['ip_address', 'description']
    date_hierarchy = 'timestamp'
    filter_horizontal = ['analytics']


@admin.register(EmailReport)
class EmailReportAdmin(admin.ModelAdmin):
    list_display = ['recipient_email', 'frequency', 'is_active', 'last_sent', 'next_send', 'site']
    list_filter = ['frequency', 'is_active', 'site']
    search_fields = ['recipient_email']
