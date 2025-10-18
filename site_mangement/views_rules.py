"""
Views for WAF Rule Management and Testing
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json

from .models import Site, WafTemplate
from .rules_engine import create_rule_engine, RuleAction


def rule_test_page(request, site_slug):
    """Page to test WAF rules"""
    site = get_object_or_404(Site, slug=site_slug)
    rule_engine = create_rule_engine(site.WafTemplate)
    
    context = {
        'site': site,
        'rule_summary': rule_engine.get_rule_summary(),
        'template_type': site.WafTemplate.template_type if site.WafTemplate else 'basic',
    }
    return render(request, 'site_management/rule_test.html', context)


@require_http_methods(["POST"])
@csrf_exempt  # For testing purposes
def test_rule_api(request, site_slug):
    """API endpoint to test a request against WAF rules"""
    site = get_object_or_404(Site, slug=site_slug)
    
    try:
        data = json.loads(request.body)
        
        # Prepare test request data
        request_data = {
            'url': data.get('url', ''),
            'path': data.get('path', '/'),
            'method': data.get('method', 'GET'),
            'headers': data.get('headers', {}),
            'params': data.get('params', {}),
            'body': data.get('body', ''),
        }
        
        # Create rule engine and evaluate
        rule_engine = create_rule_engine(site.WafTemplate)
        action, match = rule_engine.evaluate(request_data)
        
        # Prepare response
        result = {
            'action': action.value,
            'blocked': action == RuleAction.BLOCK and site.action_type == 'block',
            'match': None,
        }
        
        if match:
            result['match'] = {
                'rule_name': match.rule_name,
                'threat_type': match.threat_type,
                'threat_level': match.threat_level.value,
                'details': match.details,
            }
        
        return JsonResponse(result)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


def rule_list(request, site_slug):
    """List all rules for a site"""
    site = get_object_or_404(Site, slug=site_slug)
    rule_engine = create_rule_engine(site.WafTemplate)
    
    # Get all rules with details
    rules_data = []
    for rule in rule_engine.rules:
        rules_data.append({
            'name': rule.name,
            'threat_type': rule.threat_type,
            'threat_level': rule.threat_level.value,
            'description': rule.description,
            'pattern_count': len(rule.patterns),
        })
    
    context = {
        'site': site,
        'rules': rules_data,
        'rule_summary': rule_engine.get_rule_summary(),
    }
    return render(request, 'site_management/rule_list.html', context)


def template_comparison(request):
    """Compare basic vs advanced templates"""
    basic_engine = create_rule_engine(None)  # Defaults to basic
    
    # Create a mock advanced template
    class MockTemplate:
        template_type = 'advanced'
    
    advanced_engine = create_rule_engine(MockTemplate())
    
    context = {
        'basic_summary': basic_engine.get_rule_summary(),
        'advanced_summary': advanced_engine.get_rule_summary(),
        'basic_rules': [{
            'name': rule.name,
            'threat_type': rule.threat_type,
            'threat_level': rule.threat_level.value,
        } for rule in basic_engine.rules],
        'advanced_rules': [{
            'name': rule.name,
            'threat_type': rule.threat_type,
            'threat_level': rule.threat_level.value,
        } for rule in advanced_engine.rules],
    }
    return render(request, 'site_management/template_comparison.html', context)






