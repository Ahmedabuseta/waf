from django.urls import path
from site_mangement import views, views_sites, views_analtics, views_rules, views_caddy, views_auth, views_logs

urlpatterns = [
    # Home
    path('', views.index, name='index'),
    
    # CSRF Test (for debugging)
    path('csrf-test/', views.csrf_test, name='csrf_test'),
    path('csrf-test-page/', views.csrf_test_page, name='csrf_test_page'),

    # Authentication
    path('login/', views_auth.login_view, name='login'),
    path('signup/', views_auth.signup_view, name='signup'),
    path('logout/', views_auth.logout_view, name='logout'),

    # Analytics Dashboard
    path('analytics/', views_analtics.analytics_dashboard, name='analytics_dashboard'),
    path('analytics/<slug:site_slug>/', views_analtics.analytics_dashboard, name='analytics_dashboard_site'),

    # API Endpoints for Analytics Data
    path('api/analytics/<slug:site_slug>/geographic/', views_analtics.api_geographic_data, name='api_geographic_data'),
    path('api/analytics/<slug:site_slug>/table/', views_analtics.api_geographic_table, name='api_geographic_table'),
    path('api/analytics/<slug:site_slug>/timeline/', views_analtics.api_timeline_data, name='api_timeline_data'),
    path('api/analytics/<slug:site_slug>/top-ips/', views_analtics.api_top_ips, name='api_top_ips'),
    path('api/analytics/<slug:site_slug>/methods/', views_analtics.api_request_methods, name='api_request_methods'),

    # IP Blacklist Actions
    path('api/analytics/<slug:site_slug>/blacklist/', views_analtics.blacklist_ip, name='blacklist_ip'),
    path('api/analytics/<slug:site_slug>/unblacklist/', views_analtics.remove_from_blacklist, name='remove_from_blacklist'),

    # Export Functions
    path('analytics/<slug:site_slug>/export/csv/', views_analtics.export_analytics_csv, name='export_csv'),
    path('analytics/<slug:site_slug>/export/json/', views_analtics.export_analytics_json, name='export_json'),

    # Site Management
    path('sites/', views_sites.sites_list, name='sites_list'),
    path('sites/add/', views_sites.site_add, name='site_add'),
    path('sites/add/enhanced/', views_sites.site_add, name='site_add_enhanced'),
    # Caddy bulk sync must be BEFORE the catch-all site slug route to avoid conflicts
    path('sites/sync-all-caddy/', views_caddy.sync_all_sites, name='sync_all_sites'),
    path('sites/<slug:slug>/', views_sites.site_detail, name='site_detail'),
    path('sites/<slug:slug>/edit/', views_sites.site_edit, name='site_edit'),
    path('sites/<slug:slug>/delete/', views_sites.site_delete, name='site_delete'),

    # Address Management
    path('sites/<slug:site_slug>/addresses/add/', views_sites.address_add, name='address_add'),
    path('addresses/<int:address_id>/delete/', views_sites.address_delete, name='address_delete'),

    # Load Balancer Management
    path('sites/<slug:site_slug>/load-balancer/', views_sites.load_balancer_add, name='load_balancer_add'),
    path('sites/<slug:site_slug>/load-balancer/delete/', views_sites.load_balancer_delete, name='load_balancer_delete'),

    # WAF Template Management
    path('waf-templates/', views.waf_templates_list, name='waf_templates_list'),
    path('waf-templates/add/', views.waf_template_add, name='waf_template_add'),
    path('waf-templates/<int:template_id>/', views.waf_template_detail, name='waf_template_detail'),
    path('waf-templates/<int:template_id>/edit/', views.waf_template_edit, name='waf_template_edit'),
    path('waf-templates/<int:template_id>/delete/', views.waf_template_delete, name='waf_template_delete'),

    # Logs Management
    path('logs/', views_logs.logs_list, name='logs_list'),
    path('logs/<int:log_id>/', views_logs.log_detail, name='log_detail'),
    path('logs/<slug:site_slug>/clear/', views_logs.logs_clear, name='logs_clear'),

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
