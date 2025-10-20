"""
Custom model managers for common query patterns
"""
from django.db import models
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta


class SiteManager(models.Manager):
    """Custom manager for Site model"""
    
    def with_stats(self):
        """Annotate sites with related stats"""
        return self.annotate(
            addresses_count=Count('addresses'),
            logs_count=Count('logs')
        )
    
    def active(self):
        """Get only active sites"""
        return self.filter(status='active')


class RequestAnalyticsManager(models.Manager):
    """Custom manager for RequestAnalytics model"""
    
    def for_site(self, site):
        """Get analytics for a specific site"""
        return self.filter(site=site)
    
    def recent(self, days=7):
        """Get analytics from the last N days"""
        start_date = timezone.now() - timedelta(days=days)
        return self.filter(timestamp__gte=start_date)
    
    def blocked(self):
        """Get only blocked requests"""
        return self.filter(action_taken='blocked')
    
    def allowed(self):
        """Get only allowed requests"""
        return self.filter(action_taken='allowed')
    
    def get_metrics(self, site=None, days=7):
        """Calculate common metrics"""
        qs = self.recent(days)
        if site:
            qs = qs.filter(site=site)
        
        total = qs.count()
        blocked = qs.filter(action_taken='blocked').count()
        
        return {
            'total_requests': total,
            'blocked_requests': blocked,
            'allowed_requests': total - blocked,
            'blocked_percentage': (blocked / total * 100) if total > 0 else 0,
            'unique_countries': qs.values('country_code').distinct().count(),
            'unique_ips': qs.values('ip_address').distinct().count(),
            'avg_response_time': qs.aggregate(avg=Avg('response_time'))['avg'] or 0,
        }


class LogsManager(models.Manager):
    """Custom manager for Logs model"""
    
    def for_site(self, site):
        """Get logs for a specific site"""
        return self.filter(site=site)
    
    def blocked(self):
        """Get only blocked logs"""
        return self.filter(action_taken='blocked')
    
    def recent(self, limit=100):
        """Get recent logs"""
        return self.order_by('-timestamp')[:limit]







