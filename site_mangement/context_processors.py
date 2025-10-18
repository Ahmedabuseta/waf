"""
Context processors for adding common data to all templates
"""
from .models import Site, WafTemplate, Logs


def dashboard_stats(request):
    """Add dashboard statistics to all templates"""
    return {
        'sites_count': Site.objects.count(),
        'templates_count': WafTemplate.objects.count(),
        'logs_count': Logs.objects.count(),
    }

#
