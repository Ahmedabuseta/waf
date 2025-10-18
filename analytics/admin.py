from django.contrib import admin
from .models import RequestAnalytics, GeographicStats, ThreatAlert, EmailReport


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
    list_display = ['alert_type', 'severity', 'ip_address', 'country_code', 'is_resolved', 'timestamp', 'site']
    list_filter = ['alert_type', 'severity', 'is_resolved', 'is_notified', 'site']
    search_fields = ['ip_address', 'description']
    date_hierarchy = 'timestamp'
    filter_horizontal = ['analytics']


@admin.register(EmailReport)
class EmailReportAdmin(admin.ModelAdmin):
    list_display = ['recipient_email', 'frequency', 'is_active', 'last_sent', 'next_send', 'site']
    list_filter = ['frequency', 'is_active', 'site']
    search_fields = ['recipient_email']
