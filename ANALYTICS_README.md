# WAF Analytics System Documentation

## Overview



### ✅ Implemented Features

1. **Geographic Request Analytics**
   - 2D interactive world map showing request origins
   - Hover tooltips with detailed country/city statistics
   - Color-coded threat levels (green/orange/red)
   - Real-time geolocation using IP-API service

2. **Analytics Dashboard** (Dark Mode with Flowbite)
   - Key metrics cards (Total Requests, Blocked, Countries, IPs, Response Time)
   - Interactive 2D map with Leaflet.js
   - Geographic breakdown table
   - Requests timeline chart (Chart.js)
   - Top requesting IPs table
   - Request methods pie chart
   - Active threat alerts panel

3. **Data Export**
   - Export analytics as CSV
   - Export analytics as JSON
   - Customizable date ranges

4. **IP Blacklisting**
   - One-click IP blocking from dashboard
   - Automatic integration with Addresses model
   - Unblock functionality
   - Blacklist status indicators

5. **Threat Alerts**
   - Automatic threat detection
   - Severity levels: Low, Medium, High, Critical
   - Alert types: High Volume, Geographic Anomaly, Repeated Blocks, DDoS
   - Email notification tracking

6. **Email Reports**
   - Scheduled reports (Daily/Weekly/Monthly)
   - Configurable report sections
   - Geographic analytics
   - Threat summary
   - Top IPs
   - Management command for cron scheduling

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. Generate Demo Data (Optional)

```bash
python manage.py generate_demo_analytics --count 200
```

### 4. Run Development Server

```bash
python manage.py runserver
```

## Usage

### Accessing the Analytics Dashboard

Navigate to: `http://localhost:8000/analytics/`

Or for a specific site: `http://localhost:8000/analytics/<site-slug>/`

### Dashboard Features

#### Time Range Filters
- Last 24 Hours
- Last 7 Days (default)
- Last 30 Days
- Last 90 Days

#### Site Selector
Switch between different monitored sites.

#### Export Options
- **CSV**: Download detailed analytics as spreadsheet
- **JSON**: Get raw data for external processing

#### Interactive Map
- **Markers**: Circle size indicates request volume
- **Colors**:
  - 🟢 Green: Low/no threats
  - 🟠 Orange: High threats
  - 🔴 Red: Critical threats
- **Hover**: View detailed statistics per location

#### IP Management
- **Block IP**: Click "Block" button next to any IP
- **Unblock IP**: Click "Unblock" for blacklisted IPs

### API Endpoints

All API endpoints return JSON data:

```
GET /api/analytics/<site-slug>/geographic/?days=7
GET /api/analytics/<site-slug>/table/?days=7
GET /api/analytics/<site-slug>/timeline/?days=7
GET /api/analytics/<site-slug>/top-ips/?days=7
GET /api/analytics/<site-slug>/methods/?days=7
POST /api/analytics/<site-slug>/blacklist/
POST /api/analytics/<site-slug>/unblacklist/
```

### Email Reports Setup

1. **Configure Email in settings.py**:

```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
```

2. **Create Email Report via Admin**:
   - Go to `/admin/`
   - Navigate to "Email Reports"
   - Click "Add Email Report"
   - Configure:
     - Site
     - Recipient Email
     - Frequency (Daily/Weekly/Monthly)
     - Report sections to include
     - Next send date

3. **Schedule Cron Job**:

```bash
# Run every hour
0 * * * * cd /path/to/project && /path/to/venv/bin/python manage.py send_analytics_reports
```

## Models

### RequestAnalytics
Stores detailed analytics for each request:
- Geographic data (country, city, lat/lng)
- Request details (method, URL, user agent)
- Response details (status code, response time)
- Security info (action taken, threat level)
- Blacklist status

### GeographicStats
Daily aggregated statistics by location for performance.

### ThreatAlert
Security alerts with severity tracking and email notification status.

### EmailReport
Scheduled email report configurations.

## Middleware

### AnalyticsMiddleware

Automatically captures all incoming requests and:
1. Extracts client IP (handles proxies)
2. Geolocates IP address
3. Measures response time
4. Stores analytics record

**Note**: Currently tracks all requests. To disable for specific paths, modify `site_mangement/middleware.py`.

## Management Commands

### 1. Generate Demo Data

```bash
python manage.py generate_demo_analytics --count 500
```

Creates realistic test data with:
- Random geographic locations
- Various request methods
- Mix of allowed/blocked requests
- Threat alerts

### 2. Send Email Reports

```bash
python manage.py send_analytics_reports
```

Sends all scheduled email reports that are due.

## Customization

### Change Map Style

Edit `waf_app/templates/analytics/dashboard.html`, line ~224:

```javascript
// Light mode map
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

// Or satellite view
L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    attribution: 'Esri'
}).addTo(map);
```

### Add Custom Metrics

1. Add field to `RequestAnalytics` model
2. Update `site_mangement/views.py` to calculate metric
3. Add to dashboard template

### Integrate with WAF Logic

In your WAF decision logic, create analytics records:

```python
from site_mangement.models import RequestAnalytics

# After WAF analysis
RequestAnalytics.objects.create(
    site=site,
    ip_address=ip,
    action_taken='blocked',  # or 'allowed'
    threat_level='high',
    threat_type='SQL Injection',
    # ... other fields
)
```

## Performance Optimization

### 1. IP Geolocation Caching
IPs are cached for 24 hours to reduce API calls.

### 2. Database Indexes
Optimized indexes on:
- site + timestamp
- site + country_code
- ip_address + timestamp
- action_taken

### 3. Aggregated Statistics
Use `GeographicStats` for pre-aggregated daily data.

### 4. Async Processing (Future Enhancement)
For high-traffic sites, consider:
- Celery for background analytics processing
- Redis for caching
- PostgreSQL for better performance

## Troubleshooting

### No Map Markers Showing
- Ensure analytics records have latitude/longitude values
- Check browser console for JavaScript errors
- Verify API endpoint returns data: `/api/analytics/<site-slug>/geographic/`

### Geolocation Not Working
- IP-API has a rate limit (45 requests/minute for free tier)
- Local IPs (127.0.0.1, 192.168.x.x) are marked as "Local"
- Check internet connection for API access

### Email Reports Not Sending
- Verify email configuration in settings.py
- Check `last_sent` and `next_send` dates in EmailReport model
- Run command manually to see errors: `python manage.py send_analytics_reports`

## Admin Interface

Access `/admin/` to manage:
- Sites
- Request Analytics (view, filter, search)
- Geographic Statistics
- Threat Alerts
- Email Reports
- IP Addresses (blocklist/allowlist)

## Security Notes

1. **CSRF Protection**: All POST endpoints require CSRF token
2. **IP Privacy**: Consider anonymizing IPs for GDPR compliance
3. **Data Retention**: Implement cleanup policy for old analytics
4. **Email Credentials**: Use environment variables, not hardcoded

## Future Enhancements

- [ ] Real-time updates with WebSockets
- [ ] Machine learning threat detection
- [ ] GeoIP2 database for offline geolocation
- [ ] Grafana/Prometheus integration
- [ ] Rate limiting analytics
- [ ] Custom alert rules
- [ ] Multi-tenancy support
- [ ] API authentication for external access

## Tech Stack

- **Backend**: Django 5.2.7
- **Frontend**: Tailwind CSS, Flowbite (dark mode)
- **Map**: Leaflet.js (2D interactive map)
- **Charts**: Chart.js
- **Geolocation**: IP-API (free tier)
- **Database**: SQLite (development), PostgreSQL (production recommended)

## License

This analytics system is part of your WAF application.

## Support

For issues or questions:
1. Check this documentation
2. Review code comments in `site_mangement/`
3. Inspect browser console for frontend issues
4. Check Django logs for backend errors

---

**Version**: 1.0.0
**Last Updated**: 2025-10-08
