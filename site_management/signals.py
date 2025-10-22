"""
Django Signals for WAF Management System

This module contains all signal handlers to decouple business logic
and make the codebase cleaner and more maintainable.
"""

from django.db.models.signals import post_save, pre_save, post_delete, pre_delete
from django.dispatch import receiver, Signal
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Count
from datetime import timedelta
import logging

from .models import (
    Site, RequestAnalytics, Logs, ThreatAlert, 
    GeographicStats, WafTemplate, LoadBalancers, Addresses, BlockedIP
)

logger = logging.getLogger(__name__)


# ============================================================================
# CUSTOM SIGNALS
# ============================================================================

# Signal fired when a threat is detected
threat_detected = Signal()

# Signal fired when site configuration changes
site_config_changed = Signal()

# Signal fired when Caddy needs to be synced
caddy_sync_required = Signal()

# Signal fired when SSL certificate is uploaded
ssl_certificate_uploaded = Signal()

# Signal fired when a request is blocked
request_blocked = Signal()


# ============================================================================
# SITE SIGNALS
# ============================================================================

@receiver(pre_save, sender=Site)
def site_pre_save_handler(sender, instance, **kwargs):
    """
    Handle site pre-save operations
    - Generate slug if not exists
    - Validate SSL configuration
    """
    # Auto-generate slug from host
    if not instance.slug:
        from django.utils.text import slugify
        # Clean the host name
        clean_host = instance.host.replace('http://', '').replace('https://', '').split('/')[0]
        # Generate slug using Django's slugify
        base_slug = slugify(clean_host)
        instance.slug = base_slug
        
        # Ensure uniqueness by appending a number if needed
        counter = 1
        original_slug = instance.slug
        while Site.objects.filter(slug=instance.slug).exclude(pk=instance.pk).exists():
            instance.slug = f"{original_slug}-{counter}"
            counter += 1
        
    # Mark that pre_save ran for this instance (used for ordering verification)
    try:
        instance._site_signal_pre_save_seen = True
        logger.info(f"[signals] site.pre_save host={instance.host} pre_seen=True")
    except Exception:
        pass

    # If auto_ssl is disabled, ensure SSL files are provided for HTTPS
    if not instance.auto_ssl and instance.protocol == 'https':
        if not instance.ssl_certificate or not instance.ssl_key:
            logger.warning(f"Site {instance.host}: HTTPS enabled with auto_ssl=False but SSL files missing")
    
    # Mark old instance for comparison
    if instance.pk:
        try:
            instance._old_instance = Site.objects.get(pk=instance.pk)
        except Site.DoesNotExist:
            instance._old_instance = None


@receiver(post_save, sender=Site)
def site_post_save_handler(sender, instance, created, **kwargs):
    """
    Handle site post-save operations
    - Send caddy sync signal if configuration changed
    - Clear cache
    - Log creation/update
    """
    if created:
        logger.info(f"New site created: {instance.host}")
        
        # Create initial log entry
        Logs.objects.create(
            site=instance,
            ip_address='127.0.0.1',
            request_method='SYSTEM',
            request_url=f'http://{instance.host}/admin',
            action_taken='logged',
            details=f"Site {instance.host} created successfully | pre_save_seen={getattr(instance, '_site_signal_pre_save_seen', False)}"
        )
    else:
        # Check if configuration changed
        old = getattr(instance, '_old_instance', None)
        if old:
            config_changed = (
                old.status != instance.status or
                old.auto_ssl != instance.auto_ssl or
                old.protocol != instance.protocol or
                old.WafTemplate_id != instance.WafTemplate_id or
                old.action_type != instance.action_type or
                old.sensitivity_level != instance.sensitivity_level
            )
            
            if config_changed:
                logger.info(f"Site configuration changed: {instance.host}")
                
                # Fire custom signal
                site_config_changed.send(
                    sender=sender,
                    instance=instance,
                    old_instance=old
                )
                
                # Fire Caddy sync signal
                caddy_sync_required.send(
                    sender=sender,
                    site=instance,
                    action='update'
                )

                # Record a log entry to easily verify signal execution from UI
                try:
                    Logs.objects.create(
                        site=instance,
                        ip_address='127.0.0.1',
                        request_method='SYSTEM',
                        request_url=f'http://{instance.host}/admin',
                        action_taken='logged',
                        details=f"Signal: site_config_changed for {instance.host} | pre_save_seen={getattr(instance, '_site_signal_pre_save_seen', False)}"
                    )
                except Exception as e:
                    logger.warning(f"Failed to create verification log for site update: {e}")
        else:
            # Even if not changed, write a minimal marker log to verify ordering when needed (debug-friendly)
            try:
                Logs.objects.create(
                    site=instance,
                    ip_address='127.0.0.1',
                    request_method='SYSTEM',
                    request_url=f'http://{instance.host}/admin',
                    action_taken='logged',
                    details=f"Signal: site_post_save no-change | pre_save_seen={getattr(instance, '_site_signal_pre_save_seen', False)}"
                )
            except Exception:
                pass
    
    # Clear cache
    cache.delete(f'site_{instance.slug}')
    cache.delete('sites_list')


@receiver(post_delete, sender=Site)
def site_post_delete_handler(sender, instance, **kwargs):
    """
    Handle site deletion
    - Trigger Caddy cleanup
    - Clear cache
    - Log deletion
    """
    logger.info(f"Site deleted: {instance.host}")
    
    # Fire Caddy sync signal for cleanup
    caddy_sync_required.send(
        sender=sender,
        site=instance,
        action='delete'
    )
    
    # Clear cache
    cache.delete(f'site_{instance.slug}')
    cache.delete('sites_list')


# ============================================================================
# REQUEST ANALYTICS SIGNALS
# ============================================================================

@receiver(post_save, sender=RequestAnalytics)
def request_analytics_post_save_handler(sender, instance, created, **kwargs):
    """
    Handle request analytics post-save
    - Update geographic stats
    - Check for anomalies
    - Create threat alerts if needed
    """
    if created:
        # Update or create geographic stats (aggregated by day)
        if instance.country and instance.country_code:
            # Get today's date for aggregation
            today = timezone.now().date()
            
            geo_stat, created = GeographicStats.objects.get_or_create(
                site=instance.site,
                date=today,
                country=instance.country,
                country_code=instance.country_code,
                defaults={
                    'total_requests': 0,
                    'blocked_requests': 0,
                    'allowed_requests': 0,
                    'unique_ips': 0,
                    'avg_response_time': 0.0,
                    'high_threat_count': 0,
                    'medium_threat_count': 0,
                    'low_threat_count': 0,
                }
            )
            
            # Update counts
            geo_stat.total_requests += 1
            if instance.action_taken == 'blocked':
                geo_stat.blocked_requests += 1
            else:
                geo_stat.allowed_requests += 1
            
            # Update threat counts based on threat level
            if instance.threat_level == 'high' or instance.threat_level == 'critical':
                geo_stat.high_threat_count += 1
            elif instance.threat_level == 'medium':
                geo_stat.medium_threat_count += 1
            elif instance.threat_level == 'low':
                geo_stat.low_threat_count += 1
            
            # Update average response time (running average)
            if geo_stat.total_requests == 1:
                geo_stat.avg_response_time = instance.response_time
            else:
                geo_stat.avg_response_time = (
                    (geo_stat.avg_response_time * (geo_stat.total_requests - 1) + instance.response_time) 
                    / geo_stat.total_requests
                )
            
            geo_stat.save()
        
        # Check for rate limiting / anomalies
        check_rate_limit_anomaly(instance)
        
        # Fire request blocked signal if blocked
        if instance.action_taken == 'blocked':
            request_blocked.send(
                sender=sender,
                request=instance
            )


def check_rate_limit_anomaly(request_analytics):
    """
    Checks if the IP address is making too many requests in a 5-minute window 
    (i.e., rate limiting). If the count exceeds the threshold, creates a ThreatAlert 
    and fires a threat_detected signal. This is a form of basic anti-DDoS/rate limiting
    anomaly monitoring.

    After a 'rate_limit' threshold is breached:
    - Checks if a related alert already exists (to avoid duplicates).
    - If not, creates a new ThreatAlert (severity: 'high') for the site & IP, with info 
      about the number of requests and threshold.
    - Fires the 'threat_detected' Django signal for response by listeners (e.g., actions, notifications).
    - Logs a warning about the anomaly.
    """
    # Define time window for rate limit check
    five_min_ago = timezone.now() - timedelta(minutes=5)
    
    # How many requests from this IP at this site in the last 5 minutes?
    recent_requests = RequestAnalytics.objects.filter(
        site=request_analytics.site,
        ip_address=request_analytics.ip_address,
        timestamp__gte=five_min_ago
    ).count()
    
    # If request count is above threshold (say 100 in 5 minutes)...
    if recent_requests > 100:
        # Avoid creating duplicate unresolved alerts for same window
        existing_alert = ThreatAlert.objects.filter(
            site=request_analytics.site,
            ip_address=request_analytics.ip_address,
            alert_type__in=['rate_limit','ddos','repeated_blocks'],
            is_resolved=False,
            timestamp__gte=five_min_ago
        ).exists()
        
        if not existing_alert:
            # Create new ThreatAlert record for the site & IP
            alert = ThreatAlert.objects.create(
                site=request_analytics.site,
                ip_address=request_analytics.ip_address,
                alert_type='ddos',
                severity='high',
                description=f"Rate limit exceeded: {recent_requests} requests in 5 minutes",
                details={
                    'request_count': recent_requests,
                    'time_window': '5 minutes',
                    'threshold': 100
                }
            )
            
            # Fire a Django signal indicating a threat was detected; listeners may act (notify, block, etc)
            threat_detected.send(
                sender=ThreatAlert,
                alert=alert,
                request=request_analytics
            )
            # Write warning to application log
            logger.warning(f"Rate limit anomaly detected for IP {request_analytics.ip_address}")

            # Timed block with escalation: 5m -> 10m -> 1d
            now = timezone.now()
            block, created = BlockedIP.objects.get_or_create(
                site=request_analytics.site,
                ip_address=request_analytics.ip_address,
                defaults={
                    'reason': 'rate_limit',
                    'expires_at': now + timedelta(minutes=5),
                    'escalation_level': 0,
                }
            )
            if not created:
                block.escalation_level = (block.escalation_level or 0) + 1
                if block.escalation_level == 1:
                    block.extend(timedelta(minutes=10), reason='rate_limit_escalated')
                else:
                    block.extend(timedelta(days=1), reason='rate_limit_day_block')
                block.save(update_fields=['escalation_level'])


# ============================================================================
# LOGS SIGNALS
# ============================================================================

@receiver(post_save, sender=Logs)
def logs_post_save_handler(sender, instance, created, **kwargs):
    """
    Handle logs post-save
    - Create threat alerts for critical logs
    - Update statistics
    
    Note: Logs model currently doesn't have severity or threat_type fields
    This handler is prepared for future enhancements
    """
    # TODO: Add severity and threat_type fields to Logs model
    # For now, just log that a log entry was created
    if created:
        logger.debug(f"Log entry created: {instance.request_method} {instance.request_url}")


# ============================================================================
# WAF TEMPLATE SIGNALS
# ============================================================================

@receiver(post_save, sender=WafTemplate)
def waf_template_post_save_handler(sender, instance, created, **kwargs):
    """
    Handle WAF template post-save
    - Clear cache for affected sites
    - Log template changes
    """
    if created:
        logger.info(f"New WAF template created: {instance.name}")
    else:
        logger.info(f"WAF template updated: {instance.name}")
        
        # Clear cache for all sites using this template
        affected_sites = Site.objects.filter(WafTemplate=instance)
        for site in affected_sites:
            cache.delete(f'waf_rules_{site.slug}')
            
            # Log the change
            Logs.objects.create(
                site=site,
                ip_address='127.0.0.1',
                request_method='SYSTEM',
                request_url=f'http://{site.host}/admin',
                action_taken='logged',
                details=f"WAF template '{instance.name}' updated for site {site.host}"
            )


@receiver(post_delete, sender=WafTemplate)
def waf_template_post_delete_handler(sender, instance, **kwargs):
    """
    Handle WAF template deletion
    - Log deletion
    """
    logger.info(f"WAF template deleted: {instance.name}")


# ============================================================================
# LOAD BALANCER SIGNALS
# ============================================================================

@receiver(post_save, sender=LoadBalancers)
def load_balancer_post_save_handler(sender, instance, created, **kwargs):
    """
    Handle load balancer post-save
    - Trigger Caddy sync
    - Log changes
    """
    if created:
        logger.info(f"Load balancer created for site: {instance.site.host}")
    else:
        logger.info(f"Load balancer updated for site: {instance.site.host}")
    
    # Fire Caddy sync signal
    caddy_sync_required.send(
        sender=sender,
        site=instance.site,
        action='update_load_balancer'
    )


@receiver(post_delete, sender=LoadBalancers)
def load_balancer_post_delete_handler(sender, instance, **kwargs):
    """
    Handle load balancer deletion
    - Trigger Caddy sync
    - Log deletion
    """
    logger.info(f"Load balancer deleted for site: {instance.site.host}")
    
    # Fire Caddy sync signal
    caddy_sync_required.send(
        sender=sender,
        site=instance.site,
        action='remove_load_balancer'
    )


# ============================================================================
# ADDRESS SIGNALS
# ============================================================================

@receiver(post_save, sender=Addresses)
def address_post_save_handler(sender, instance, created, **kwargs):
    """
    Handle address post-save
    - Trigger Caddy sync if site has load balancer
    - Log changes
    """
    if created:
        logger.info(f"Address added to site {instance.site.host}: {instance.ip_address}")
    
    # Check if site has load balancer
    if hasattr(instance.site, 'loadbalancers'):
        # Fire Caddy sync signal
        caddy_sync_required.send(
            sender=sender,
            site=instance.site,
            action='update_addresses'
        )


@receiver(post_delete, sender=Addresses)
def address_post_delete_handler(sender, instance, **kwargs):
    """
    Handle address deletion
    - Trigger Caddy sync if site has load balancer
    - Log deletion
    """
    logger.info(f"Address removed from site {instance.site.host}: {instance.ip_address}")
    
    # Check if site has load balancer
    if hasattr(instance.site, 'loadbalancers'):
        # Fire Caddy sync signal
        caddy_sync_required.send(
            sender=sender,
            site=instance.site,
            action='update_addresses'
        )


# ============================================================================
# THREAT ALERT SIGNALS
# ============================================================================

@receiver(post_save, sender=ThreatAlert)
def threat_alert_post_save_handler(sender, instance, created, **kwargs):
    """
    Handle threat alert post-save
    - Send notifications (email, webhook, etc.)
    - Update dashboard cache
    """
    if created:
        logger.warning(
            f"New threat alert: {instance.alert_type} - "
            f"{instance.severity} - IP: {instance.ip_address} - "
            f"Site: {instance.site.host}"
        )
        
        # Clear threat alerts cache
        cache.delete(f'threat_alerts_{instance.site.slug}')
        cache.delete('threat_alerts_all')
        
        # TODO: Send email notification if configured
        # TODO: Send webhook notification if configured


# ============================================================================
# CUSTOM SIGNAL HANDLERS
# ============================================================================

@receiver(threat_detected)
def handle_threat_detected(sender, alert, **kwargs):
    """
    Handle threat detected signal
    - Can be used for additional processing, notifications, etc.
    """
    logger.info(f"Threat detected signal received: {alert.alert_type} - {alert.severity}")
    
    # Example: Auto-block IP if multiple critical threats
    if alert.severity == 'critical':
        recent_critical = ThreatAlert.objects.filter(
            site=alert.site,
            ip_address=alert.ip_address,
            severity='critical',
            resolved=False,
            created_at__gte=timezone.now() - timedelta(hours=24)
        ).count()
        
        if recent_critical >= 3:
            logger.critical(
                f"IP {alert.ip_address} has {recent_critical} critical threats "
                f"in 24 hours. Consider auto-blocking."
            )
            # TODO: Implement auto-blocking logic


@receiver(site_config_changed)
def handle_site_config_changed(sender, instance, old_instance, **kwargs):
    """
    Handle site configuration change
    - Log the changes
    - Clear caches
    """
    changes = []
    
    if old_instance.status != instance.status:
        changes.append(f"Status: {old_instance.status} → {instance.status}")
    
    if old_instance.auto_ssl != instance.auto_ssl:
        changes.append(f"Auto SSL: {old_instance.auto_ssl} → {instance.auto_ssl}")
    
    if old_instance.protocol != instance.protocol:
        changes.append(f"Protocol: {old_instance.protocol} → {instance.protocol}")
    
    if old_instance.action_type != instance.action_type:
        changes.append(f"Action Type: {old_instance.action_type} → {instance.action_type}")
    
    if changes:
        Logs.objects.create(
            site=instance,
            ip_address='127.0.0.1',
            request_method='SYSTEM',
            request_url=f'http://{instance.host}/admin',
            action_taken='logged',
            details=f"Site configuration changed: {', '.join(changes)}"
        )


@receiver(caddy_sync_required)
def handle_caddy_sync_required(sender, site, action, **kwargs):
    """
    Handle Caddy sync signal
    - Can trigger automatic Caddy API calls
    - For now, just log the requirement
    """
    logger.info(f"Caddy sync required for site {site.host}: {action}")
    
    # TODO: Implement automatic Caddy sync
    # from .caddy_manager import CaddyManager
    # caddy = CaddyManager()
    # if action == 'update':
    #     caddy.sync_site(site)
    # elif action == 'delete':
    #     caddy.remove_site(site)


@receiver(ssl_certificate_uploaded)
def handle_ssl_certificate_uploaded(sender, site, **kwargs):
    """
    Handle SSL certificate upload
    - Validate certificate
    - Log upload
    - Trigger Caddy sync
    """
    logger.info(f"SSL certificate uploaded for site: {site.host}")
    
    Logs.objects.create(
        site=site,
        ip_address='127.0.0.1',
        request_method='SYSTEM',
        request_url=f'http://{site.host}/admin',
        action_taken='logged',
        details=f"SSL certificate uploaded for {site.host}"
    )
    
    # Trigger Caddy sync
    caddy_sync_required.send(
        sender=sender,
        site=site,
        action='update_ssl'
    )


@receiver(request_blocked)
def handle_request_blocked(sender, request, **kwargs):
    """
    Handle request blocked signal
    - Update statistics
    - Check for patterns
    """
    logger.debug(f"Request blocked: {request.ip_address} - {request.request_path}")
    
    # Check if this IP has been blocked frequently
    recent_blocks = RequestAnalytics.objects.filter(
        site=request.site,
        ip_address=request.ip_address,
        action_taken='blocked',
        timestamp__gte=timezone.now() - timedelta(hours=1)
    ).count()
    
    # If blocked more than 20 times in an hour, create threat alert
    if recent_blocks > 20:
        existing_alert = ThreatAlert.objects.filter(
            site=request.site,
            ip_address=request.ip_address,
            alert_type='repeated_blocks',
            resolved=False,
            created_at__gte=timezone.now() - timedelta(hours=1)
        ).exists()
        
        if not existing_alert:
            ThreatAlert.objects.create(
                site=request.site,
                ip_address=request.ip_address,
                alert_type='repeated_blocks',
                severity='high',
                description=f"IP blocked {recent_blocks} times in 1 hour",
                details={
                    'block_count': recent_blocks,
                    'time_window': '1 hour',
                    'latest_path': request.request_path
                }
            )

