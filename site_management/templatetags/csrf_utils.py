from django import template
from django.middleware.csrf import get_token

register = template.Library()


@register.simple_tag(takes_context=True)
def csrf_token_value(context):
    """Get the CSRF token value for use in JavaScript"""
    request = context['request']
    return get_token(request)


@register.simple_tag(takes_context=True)
def csrf_token_meta(context):
    """Generate a meta tag with CSRF token for JavaScript"""
    request = context['request']
    token = get_token(request)
    return f'<meta name="csrf-token" content="{token}">'