from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from .managers import SiteManager, RequestAnalyticsManager, LogsManager

def ssl_upload_path(instance, filename):
    # Store SSL files under site slug
    return f'ssl/{instance.slug}/{filename}'

class Site(models.Model):
    host = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Host",
        help_text="Domain or IP address of the site"
    )

    objects = SiteManager()
    status = models.CharField(
        max_length=10,
        choices=[('active', 'Active'), ('inactive', 'Inactive')],
        default='active',
        verbose_name="Status"
    )

    support_subdomains = models.BooleanField(
        default=False,
        verbose_name="Support Subdomains",
    )

    auto_ssl = models.BooleanField(
        default=True,
        verbose_name="Auto SSL",
        help_text="Enable automatic SSL management"
    )
    protocol = models.CharField(
        max_length=10,
        choices=[('http', 'HTTP'), ('https', 'HTTPS')],
        verbose_name="Protocol"
    )
    ssl_certificate = models.FileField(
        upload_to=ssl_upload_path,
        blank=True,
        null=True,
        verbose_name="SSL Certificate"
    )
    ssl_key = models.FileField(
        upload_to=ssl_upload_path,
        blank=True,
        null=True,
        verbose_name="SSL Key"
    )
    ssl_chain = models.FileField(
        upload_to=ssl_upload_path,
        blank=True,
        null=True,
        verbose_name="SSL Chain"
    )

    action_type = models.CharField(
        max_length=20,
        choices=[('block', 'Block'), ('log', 'Log')],
        default='log',
        verbose_name="Action Type"
    )
    sensitivity_level = models.CharField(
        max_length=10,
        choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')],
        default='medium',
        verbose_name="Sensitivity Level"
    )
    WafTemplate = models.ForeignKey(
        'WafTemplate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name='sites',
        verbose_name="WAF Template"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(max_length=255, unique=True)

    # DNS Challenge fields for wildcard certificates
    dns_challenge_key = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="DNS Challenge Key",
        help_text="The DNS record name for ACME challenge (e.g., _acme-challenge.example.com)"
    )
    dns_challenge_value = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="DNS Challenge Value",
        help_text="The TXT record value for ACME challenge"
    )
    dns_challenge_created_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="DNS Challenge Created At",
        help_text="When the DNS challenge was generated"
    )

    def clean(self):
        """
        Model-level validation for SSL/TLS configuration
        Ensures protocol, certificates, and settings are consistent
        """
        super().clean()

        errors = {}

        # Rule 1: HTTP cannot have SSL-related fields
        if self.protocol == 'http':
            if self.auto_ssl:
                errors['auto_ssl'] = 'HTTP protocol cannot have auto_ssl enabled. Change to HTTPS or disable auto_ssl.'

            if self.ssl_certificate or self.ssl_key or self.ssl_chain:
                errors['protocol'] = 'HTTP protocol cannot have SSL certificates. Change to HTTPS or remove certificates.'

        # Rule 2: HTTPS requires SSL configuration
        if self.protocol == 'https':
            if not self.auto_ssl and not self.ssl_certificate:
                errors['protocol'] = 'HTTPS requires either auto_ssl=True or manual SSL certificate upload.'

            if not self.auto_ssl:
                # Manual certificates require both cert and key
                if self.ssl_certificate and not self.ssl_key:
                    errors['ssl_key'] = 'SSL private key is required when certificate is provided.'
                if self.ssl_key and not self.ssl_certificate:
                    errors['ssl_certificate'] = 'SSL certificate is required when private key is provided.'

        # Rule 3: Subdomain support validation
        if self.support_subdomains:
            if self.protocol == 'http':
                errors['support_subdomains'] = 'Subdomain support requires HTTPS protocol.'

            # If using manual certificates, they must support wildcards
            # This is validated in the form with actual certificate content

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Override save to run full_clean validation"""
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Site"
        verbose_name_plural = "Sites"
        indexes = [
            models.Index(fields=['host']),
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        return f"{self.host} ({self.status})"

    def get_ssl_status(self):
        """
        Get SSL/TLS configuration status for this site
        Returns dict with SSL configuration details
        """
        if self.protocol == 'http':
            return {
                'enabled': False,
                'type': 'none',
                'message': 'HTTP - No SSL'
            }

        if self.auto_ssl:
            ssl_type = 'auto_wildcard' if self.support_subdomains else 'auto_single'
            return {
                'enabled': True,
                'type': ssl_type,
                'message': f'Auto SSL (Let\'s Encrypt) - {"Wildcard" if self.support_subdomains else "Single Domain"}'
            }

        if self.ssl_certificate:
            return {
                'enabled': True,
                'type': 'manual',
                'message': 'Manual SSL Certificate',
                'has_chain': bool(self.ssl_chain)
            }

        return {
            'enabled': False,
            'type': 'invalid',
            'message': 'HTTPS enabled but no SSL configuration'
        }

    def requires_dns_challenge(self):
        """
        Check if this site requires DNS challenge for SSL
        (wildcard certificates with auto SSL)
        """
        return (
            self.protocol == 'https' and
            self.auto_ssl and
            self.support_subdomains
        )

    def has_dns_challenge(self):
        """
        Check if this site has an active DNS challenge
        """
        return bool(self.dns_challenge_key and self.dns_challenge_value)

    def is_dns_challenge_expired(self, hours=24):
        """
        Check if the DNS challenge has expired
        """
        if not self.dns_challenge_created_at:
            return True
        
        from django.utils import timezone
        from datetime import timedelta
        return timezone.now() > self.dns_challenge_created_at + timedelta(hours=hours)

    def clear_dns_challenge(self):
        """
        Clear the DNS challenge data
        """
        self.dns_challenge_key = None
        self.dns_challenge_value = None
        self.dns_challenge_created_at = None
        self.save(update_fields=['dns_challenge_key', 'dns_challenge_value', 'dns_challenge_created_at'])

class Addresses(models.Model):
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='addresses',
        verbose_name="Site"
    )
    ip_address = models.GenericIPAddressField(verbose_name="IP Address")
    port = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(65535)],
        verbose_name="Port"
    )
    is_allowed = models.BooleanField(
        default=True,
        verbose_name="Is Allowed",
        help_text="True for allowlist, False for blocklist"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Address"
        verbose_name_plural = "Addresses"
        indexes = [
            models.Index(fields=['ip_address', 'port']),
        ]

    def __str__(self):
        status = "Allowed" if self.is_allowed else "Blocked"
        return f"{self.ip_address}:{self.port} ({status}) for {self.site.host}"

class LoadBalancers(models.Model):
    site = models.OneToOneField(
        Site,
        on_delete=models.CASCADE,
        related_name='load_balancer',
        verbose_name="Site"
    )
    algorithm = models.CharField(
        max_length=20,
        choices=[
            ('round_robin', 'Round Robin'),
            ('least_connections', 'Least Connections'),
            ('ip_hash', 'IP Hash')
        ],
        default='round_robin',
        verbose_name="Algorithm"
    )
    health_check_url = models.URLField(verbose_name="Health Check URL")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Load Balancer"
        verbose_name_plural = "Load Balancers"

    def __str__(self):
        return f"LoadBalancer for {self.site.host} using {self.algorithm}"

class WafTemplate(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Template Name"
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Description"
    )
    template_type = models.CharField(
        max_length=20,
        choices=[('basic', 'Basic'), ('advanced', 'Advanced')],
        default='basic',
        verbose_name="Template Type"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "WAF Template"
        verbose_name_plural = "WAF Templates"

    def __str__(self):
        return self.name

class Logs(models.Model):
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='logs',
        verbose_name="Site"
    )

    objects = LogsManager()
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(verbose_name="IP Address")
    request_method = models.CharField(max_length=10, verbose_name="Request Method")
    request_url = models.URLField(verbose_name="Request URL")
    action_taken = models.CharField(
        max_length=20,
        choices=[('blocked', 'Blocked'), ('logged', 'Logged')],
        verbose_name="Action Taken"
    )
    details = models.TextField(blank=True, null=True, verbose_name="Details")

    class Meta:
        verbose_name = "Log"
        verbose_name_plural = "Logs"
        ordering = ['-timestamp']

    def __str__(self):
        return f"Log {self.id} for {self.site.host} at {self.timestamp}"


class RequestAnalytics(models.Model):
    """Store detailed analytics for each request with geographic information"""
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='analytics',
        verbose_name="Site"
    )

    objects = RequestAnalyticsManager()
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(verbose_name="IP Address", db_index=True)

    # Geographic data
    country = models.CharField(max_length=100, blank=True, null=True, verbose_name="Country")
    country_code = models.CharField(max_length=2, blank=True, null=True, db_index=True, verbose_name="Country Code")
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name="City")
    region = models.CharField(max_length=100, blank=True, null=True, verbose_name="Region")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, verbose_name="Latitude")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, verbose_name="Longitude")

    # Request details
    request_method = models.CharField(max_length=10, verbose_name="Request Method")
    request_url = models.TextField(verbose_name="Request URL")
    request_path = models.TextField(verbose_name="Request Path")
    user_agent = models.TextField(blank=True, null=True, verbose_name="User Agent")
    referer = models.TextField(blank=True, null=True, verbose_name="Referer")

    # Response details
    status_code = models.IntegerField(verbose_name="Status Code")
    response_time = models.FloatField(verbose_name="Response Time (ms)", help_text="Response time in milliseconds")

    # Security details
    action_taken = models.CharField(
        max_length=20,
        choices=[('allowed', 'Allowed'), ('blocked', 'Blocked'), ('rate_limited', 'Rate Limited')],
        default='allowed',
        verbose_name="Action Taken",
        db_index=True
    )
    threat_level = models.CharField(
        max_length=10,
        choices=[('none', 'None'), ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')],
        default='none',
        verbose_name="Threat Level",
        db_index=True
    )
    threat_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Threat Type",
        help_text="Type of threat detected (SQL Injection, XSS, etc.)"
    )

    # Flag for blacklisting
    is_blacklisted = models.BooleanField(default=False, verbose_name="Is Blacklisted", db_index=True)

    class Meta:
        verbose_name = "Request Analytics"
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
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='geographic_stats',
        verbose_name="Site"
    )
    date = models.DateField(verbose_name="Date", db_index=True)
    country = models.CharField(max_length=100, verbose_name="Country")
    country_code = models.CharField(max_length=2, verbose_name="Country Code", db_index=True)

    # Aggregated counts
    total_requests = models.IntegerField(default=0, verbose_name="Total Requests")
    blocked_requests = models.IntegerField(default=0, verbose_name="Blocked Requests")
    allowed_requests = models.IntegerField(default=0, verbose_name="Allowed Requests")
    unique_ips = models.IntegerField(default=0, verbose_name="Unique IPs")

    # Performance metrics
    avg_response_time = models.FloatField(default=0, verbose_name="Average Response Time (ms)")

    # Threat metrics
    high_threat_count = models.IntegerField(default=0, verbose_name="High Threat Count")
    medium_threat_count = models.IntegerField(default=0, verbose_name="Medium Threat Count")
    low_threat_count = models.IntegerField(default=0, verbose_name="Low Threat Count")

    class Meta:
        verbose_name = "Geographic Statistics"
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
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='threat_alerts',
        verbose_name="Site"
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    alert_type = models.CharField(
        max_length=50,
        choices=[
            ('high_volume', 'High Volume Attack'),
            ('geographic_anomaly', 'Geographic Anomaly'),
            ('repeated_blocks', 'Repeated Blocks from IP'),
            ('new_threat', 'New Threat Pattern'),
            ('ddos', 'Possible DDoS'),
        ],
        verbose_name="Alert Type"
    )
    severity = models.CharField(
        max_length=10,
        choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')],
        default='medium',
        verbose_name="Severity"
    )

    # Alert details
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name="IP Address")
    country_code = models.CharField(max_length=2, blank=True, null=True, verbose_name="Country Code")
    description = models.TextField(verbose_name="Description")
    request_count = models.IntegerField(default=0, verbose_name="Related Request Count")

    # Status tracking
    is_resolved = models.BooleanField(default=False, verbose_name="Is Resolved")
    resolved_at = models.DateTimeField(blank=True, null=True, verbose_name="Resolved At")
    is_notified = models.BooleanField(default=False, verbose_name="Email Sent")

    # Related analytics
    analytics = models.ManyToManyField(
        RequestAnalytics,
        related_name='alerts',
        blank=True,
        verbose_name="Related Analytics"
    )

    class Meta:
        verbose_name = "Threat Alert"
        verbose_name_plural = "Threat Alerts"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['site', 'timestamp']),
            models.Index(fields=['is_resolved', 'severity']),
        ]

    def __str__(self):
        return f"{self.alert_type} - {self.severity} - {self.timestamp}"


class EmailReport(models.Model):
    """Track scheduled email reports for analytics"""
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='email_reports',
        verbose_name="Site"
    )
    recipient_email = models.EmailField(verbose_name="Recipient Email")
    frequency = models.CharField(
        max_length=20,
        choices=[
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
        ],
        default='weekly',
        verbose_name="Frequency"
    )

    # Report configuration
    include_geographic = models.BooleanField(default=True, verbose_name="Include Geographic Analytics")
    include_threats = models.BooleanField(default=True, verbose_name="Include Threat Summary")
    include_top_ips = models.BooleanField(default=True, verbose_name="Include Top IPs")

    # Scheduling
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    last_sent = models.DateTimeField(blank=True, null=True, verbose_name="Last Sent")
    next_send = models.DateTimeField(verbose_name="Next Send Date")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Email Report"
        verbose_name_plural = "Email Reports"
        ordering = ['next_send']

    def __str__(self):
        return f"{self.recipient_email} - {self.frequency} - {self.site.host}"

    def calculate_next_send(self):
        """Calculate next send date based on frequency"""
        now = timezone.now()
        if self.frequency == 'daily':
            return now + timedelta(days=1)
        elif self.frequency == 'weekly':
            return now + timedelta(weeks=1)
        elif self.frequency == 'monthly':
            return now + timedelta(days=30)
        return now


class BlockedIP(models.Model):
    """Timed IP blocking with escalation per site."""
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='blocked_ips',
        verbose_name='Site'
    )
    ip_address = models.GenericIPAddressField(db_index=True)
    reason = models.CharField(max_length=100, default='manual', db_index=True)
    blocked_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    # Escalation level for this IP on this site
    escalation_level = models.IntegerField(default=0)
    # Optional metadata
    notes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Blocked IP'
        verbose_name_plural = 'Blocked IPs'
        indexes = [
            models.Index(fields=['site', 'ip_address']),
            models.Index(fields=['site', 'expires_at']),
        ]
        unique_together = [('site', 'ip_address')]

    def __str__(self):
        return f"{self.ip_address} blocked on {self.site.host} until {self.expires_at} (level {self.escalation_level})"

    @property
    def is_active(self) -> bool:
        return timezone.now() < self.expires_at

    def extend(self, duration: timedelta, reason: str = None):
        self.expires_at = max(self.expires_at, timezone.now()) + duration
        if reason:
            self.reason = reason
        self.save(update_fields=['expires_at', 'reason'])
