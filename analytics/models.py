from django.db import models
from django.utils import timezone
from datetime import timedelta


class RequestAnalytics(models.Model):
    """Store detailed analytics for each request with geographic information"""
    
    site = models.ForeignKey('site_mangement.Site', on_delete=models.CASCADE, related_name='analytics')
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(db_index=True)
    
    # Geographic
    country = models.CharField(max_length=100, blank=True, null=True)
    country_code = models.CharField(max_length=2, blank=True, null=True, db_index=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    region = models.CharField(max_length=100, blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    
    # Request
    request_method = models.CharField(max_length=10)
    request_url = models.TextField()
    request_path = models.TextField()
    user_agent = models.TextField(blank=True, null=True)
    referer = models.TextField(blank=True, null=True)
    
    # Response
    status_code = models.IntegerField()
    response_time = models.FloatField(help_text="Response time in milliseconds")
    
    # Security
    ACTION_CHOICES = [('allowed', 'Allowed'), ('blocked', 'Blocked'), ('rate_limited', 'Rate Limited')]
    THREAT_CHOICES = [('none', 'None'), ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')]
    
    action_taken = models.CharField(max_length=20, choices=ACTION_CHOICES, default='allowed', db_index=True)
    threat_level = models.CharField(max_length=10, choices=THREAT_CHOICES, default='none', db_index=True)
    threat_type = models.CharField(max_length=50, blank=True, null=True)
    is_blacklisted = models.BooleanField(default=False, db_index=True)

    class Meta:
        verbose_name_plural = "Request Analytics"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['site', 'timestamp']),
            models.Index(fields=['site', 'country_code']),
            models.Index(fields=['site', 'action_taken']),
            models.Index(fields=['ip_address', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.ip_address} - {self.country_code} - {self.timestamp}"


class GeographicStats(models.Model):
    """Aggregated daily statistics by geographic location"""
    
    site = models.ForeignKey('site_mangement.Site', on_delete=models.CASCADE, related_name='geographic_stats')
    date = models.DateField(db_index=True)
    country = models.CharField(max_length=100)
    country_code = models.CharField(max_length=2, db_index=True)
    
    # Metrics
    total_requests = models.IntegerField(default=0)
    blocked_requests = models.IntegerField(default=0)
    allowed_requests = models.IntegerField(default=0)
    unique_ips = models.IntegerField(default=0)
    avg_response_time = models.FloatField(default=0)
    high_threat_count = models.IntegerField(default=0)
    medium_threat_count = models.IntegerField(default=0)
    low_threat_count = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = "Geographic Statistics"
        unique_together = ['site', 'date', 'country_code']
        ordering = ['-date', '-total_requests']
        indexes = [
            models.Index(fields=['site', 'date']),
            models.Index(fields=['site', 'country_code', 'date']),
        ]

    def __str__(self):
        return f"{self.country} - {self.date} - {self.total_requests} requests"


class ThreatAlert(models.Model):
    """Store threat alerts for monitoring and email notifications"""
    
    ALERT_TYPE_CHOICES = [
        ('high_volume', 'High Volume Attack'),
        ('geographic_anomaly', 'Geographic Anomaly'),
        ('repeated_blocks', 'Repeated Blocks from IP'),
        ('new_threat', 'New Threat Pattern'),
        ('ddos', 'Possible DDoS'),
    ]
    SEVERITY_CHOICES = [('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')]
    
    site = models.ForeignKey('site_mangement.Site', on_delete=models.CASCADE, related_name='threat_alerts')
    timestamp = models.DateTimeField(auto_now_add=True)
    alert_type = models.CharField(max_length=50, choices=ALERT_TYPE_CHOICES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='medium')
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    country_code = models.CharField(max_length=2, blank=True, null=True)
    description = models.TextField()
    request_count = models.IntegerField(default=0)
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(blank=True, null=True)
    is_notified = models.BooleanField(default=False)
    analytics = models.ManyToManyField(RequestAnalytics, related_name='alerts', blank=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['site', 'timestamp']),
            models.Index(fields=['is_resolved', 'severity']),
        ]

    def __str__(self):
        return f"{self.alert_type} - {self.severity} - {self.timestamp}"


class EmailReport(models.Model):
    """Track scheduled email reports for analytics"""
    
    FREQUENCY_CHOICES = [('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly')]
    
    site = models.ForeignKey('site_mangement.Site', on_delete=models.CASCADE, related_name='email_reports')
    recipient_email = models.EmailField()
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='weekly')
    include_geographic = models.BooleanField(default=True)
    include_threats = models.BooleanField(default=True)
    include_top_ips = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    last_sent = models.DateTimeField(blank=True, null=True)
    next_send = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['next_send']

    def __str__(self):
        return f"{self.recipient_email} - {self.frequency} - {self.site.host}"
    
    def calculate_next_send(self):
        now = timezone.now()
        days = {'daily': 1, 'weekly': 7, 'monthly': 30}
        return now + timedelta(days=days.get(self.frequency, 7))
