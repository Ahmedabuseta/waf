from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('<slug:site_slug>/', views.DashboardView.as_view(), name='dashboard_site'),
    
    # API Endpoints
    path('api/<slug:site_slug>/geographic/', views.GeographicDataAPIView.as_view(), name='api_geographic'),
    path('api/<slug:site_slug>/table/', views.GeographicTableAPIView.as_view(), name='api_table'),
    path('api/<slug:site_slug>/timeline/', views.TimelineAPIView.as_view(), name='api_timeline'),
    path('api/<slug:site_slug>/top-ips/', views.TopIPsAPIView.as_view(), name='api_top_ips'),
    path('api/<slug:site_slug>/methods/', views.RequestMethodsAPIView.as_view(), name='api_methods'),
    
    # Actions
    path('api/<slug:site_slug>/blacklist/', views.BlacklistIPView.as_view(), name='blacklist_ip'),
    path('api/<slug:site_slug>/unblacklist/', views.UnblacklistIPView.as_view(), name='unblacklist_ip'),
    
    # Export
    path('export/<slug:site_slug>/csv/', views.ExportCSVView.as_view(), name='export_csv'),
    path('export/<slug:site_slug>/json/', views.ExportJSONView.as_view(), name='export_json'),
]
