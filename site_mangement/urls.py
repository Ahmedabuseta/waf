from django.urls import path
from site_mangement import views, views_rules, views_caddy, views_auth

urlpatterns = [
    # Home
    path('', views.index, name='index'),

    # Authentication
    path('login/', views_auth.login_view, name='login'),
    path('signup/', views_auth.signup_view, name='signup'),
    path('logout/', views_auth.logout_view, name='logout'),

    # Analytics Dashboard
    path('analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    path('analytics/<slug:site_slug>/', views.analytics_dashboard, name='analytics_dashboard_site'),

    # API Endpoints for Analytics Data
    path('api/analytics/<slug:site_slug>/geographic/', views.api_geographic_data, name='api_geographic_data'),
    path('api/analytics/<slug:site_slug>/table/', views.api_geographic_table, name='api_geographic_table'),
    path('api/analytics/<slug:site_slug>/timeline/', views.api_timeline_data, name='api_timeline_data'),
    path('api/analytics/<slug:site_slug>/top-ips/', views.api_top_ips, name='api_top_ips'),
    path('api/analytics/<slug:site_slug>/methods/', views.api_request_methods, name='api_request_methods'),

    # IP Blacklist Actions
    path('api/analytics/<slug:site_slug>/blacklist/', views.blacklist_ip, name='blacklist_ip'),
    path('api/analytics/<slug:site_slug>/unblacklist/', views.remove_from_blacklist, name='remove_from_blacklist'),

    # Export Functions
    path('analytics/<slug:site_slug>/export/csv/', views.export_analytics_csv, name='export_csv'),
    path('analytics/<slug:site_slug>/export/json/', views.export_analytics_json, name='export_json'),

    # Site Management
    path('sites/', views.sites_list, name='sites_list'),
    path('sites/add/', views.site_add, name='site_add'),
    path('sites/add/enhanced/', views.site_add, name='site_add_enhanced'),
    # Caddy bulk sync must be BEFORE the catch-all site slug route to avoid conflicts
    path('sites/sync-all-caddy/', views_caddy.sync_all_sites, name='sync_all_sites'),
    path('sites/<slug:slug>/', views.site_detail, name='site_detail'),
    path('sites/<slug:slug>/edit/', views.site_edit, name='site_edit'),
    path('sites/<slug:slug>/delete/', views.site_delete, name='site_delete'),

    # Address Management
    path('sites/<slug:site_slug>/addresses/add/', views.address_add, name='address_add'),
    path('addresses/<int:address_id>/delete/', views.address_delete, name='address_delete'),

    # Load Balancer Management
    path('sites/<slug:site_slug>/load-balancer/', views.load_balancer_add, name='load_balancer_add'),
    path('sites/<slug:site_slug>/load-balancer/delete/', views.load_balancer_delete, name='load_balancer_delete'),

    # WAF Template Management
    path('waf-templates/', views.waf_templates_list, name='waf_templates_list'),
    path('waf-templates/add/', views.waf_template_add, name='waf_template_add'),
    path('waf-templates/<int:template_id>/', views.waf_template_detail, name='waf_template_detail'),
    path('waf-templates/<int:template_id>/edit/', views.waf_template_edit, name='waf_template_edit'),
    path('waf-templates/<int:template_id>/delete/', views.waf_template_delete, name='waf_template_delete'),

    # Logs Management
    path('logs/', views.logs_list, name='logs_list'),
    path('logs/<int:log_id>/', views.log_detail, name='log_detail'),
    path('logs/<slug:site_slug>/clear/', views.logs_clear, name='logs_clear'),

    # WAF Rules Management
    path('sites/<slug:site_slug>/rules/test/', views_rules.rule_test_page, name='rule_test'),
    path('sites/<slug:site_slug>/rules/test-api/', views_rules.test_rule_api, name='test_rule_api'),
    path('sites/<slug:site_slug>/rules/', views_rules.rule_list, name='rule_list'),
    path('templates/comparison/', views_rules.template_comparison, name='template_comparison'),

    # Caddy Management
    path('caddy/status/', views_caddy.caddy_status, name='caddy_status'),
    path('sites/<slug:site_slug>/sync-caddy/', views_caddy.sync_site_to_caddy, name='sync_site_to_caddy'),
    path('sites/<slug:site_slug>/caddy-config/', views_caddy.caddy_config_view, name='caddy_config'),

    # SSL Management
    path('sites/<slug:site_slug>/ssl/upload/', views_caddy.ssl_upload_page, name='ssl_upload'),
    path('sites/<slug:site_slug>/ssl/status/', views_caddy.site_ssl_status, name='site_ssl_status'),
    path('sites/<slug:site_slug>/ssl/toggle-auto/', views_caddy.toggle_auto_ssl, name='toggle_auto_ssl'),

    # DNS Challenge Management
    path('sites/<slug:site_slug>/dns-challenge/', views_caddy.dns_challenge_page, name='dns_challenge'),

    # API Endpoints
    path('api/ssl/validate/', views_caddy.validate_ssl_api, name='validate_ssl_api'),
    path('api/dns/verify/', views_caddy.verify_dns_record_api, name='verify_dns_api'),
    path('api/dns/propagation/', views_caddy.check_dns_propagation_api, name='check_dns_propagation_api'),

    # Certificate Management
    path('certificates/validate-all/', views_caddy.validate_all_certificates, name='validate_all_certificates'),
    path('sites/<slug:site_slug>/logs/export/', views_caddy.export_caddy_logs, name='export_caddy_logs'),
    path('caddy/logs/cleanup/', views_caddy.caddy_cleanup_logs, name='caddy_cleanup_logs'),
]
