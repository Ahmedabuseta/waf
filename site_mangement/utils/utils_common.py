"""
Common utility functions for DRY code
"""
from django.utils import timezone
from django.utils.text import slugify
from datetime import timedelta


def get_time_range(days=7):
    """Get start and end date for a time range"""
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    return start_date, end_date


def calculate_percentage(part, total):
    """Calculate percentage safely"""
    return (part / total * 100) if total > 0 else 0


def generate_slug(text):
    """Generate slug from text, handling URLs"""
    # Remove common URL protocols
    text = text.replace('http://', '').replace('https://', '')
    text = text.replace('/', '-').rstrip('-')
    return slugify(text)


def format_response_time(milliseconds):
    """Format response time for display"""
    return round(milliseconds, 2)


def get_days_from_request(request, default=7):
    """Extract days parameter from request"""
    try:
        return int(request.GET.get('days', default))
    except (ValueError, TypeError):
        return default


def prepare_export_filename(site_slug, extension='csv'):
    """Generate export filename"""
    timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
    return f"analytics_{site_slug}_{timestamp}.{extension}"







