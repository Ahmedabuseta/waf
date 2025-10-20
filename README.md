# WAF Management System

## 🛡️ Web Application Firewall with Django

A comprehensive Web Application Firewall (WAF) management system built with Django, featuring real-time threat detection, geographic analytics, and automatic Caddy server integration.

---

## ✨ Key Features

### 🔒 Security
- **Advanced WAF Rule Engine** - Basic and advanced threat detection templates
- **Real-time Request Analysis** - Monitor and block malicious requests
- **IP Allowlist/Blocklist** - Granular access control
- **Threat Alerts** - Automatic detection and notification
- **Rate Limiting** - Automatic anomaly detection

### 📊 Analytics
- **Geographic Visualization** - Interactive world map with country highlighting
- **Request Timeline** - Historical request analysis
- **Threat Level Indicators** - Color-coded threat visualization
- **Data Export** - CSV and JSON export capabilities
- **Real-time Dashboard** - Live statistics and metrics

### ⚙️ Management
- **Site Management** - CRUD operations for protected sites
- **SSL Management** - Auto-SSL or custom certificate upload
- **Load Balancing** - Multiple IPs with various algorithms (Round Robin, Least Connections, IP Hash)
- **WAF Templates** - Reusable security configurations
- **Comprehensive Logging** - Complete audit trail

### 🎨 User Interface
- **Dark Mode Support** - Toggle between light and dark themes
- **Responsive Design** - Works on all devices
- **Modern UI** - Built with Tailwind CSS and Flowbite
- **Interactive Maps** - Leaflet.js integration
- **Dynamic Charts** - Chart.js visualizations

### 🔌 Integration
- **Caddy Server** - Automatic reverse proxy configuration
- **HTTPX Proxy** - Request forwarding middleware
- **Django Signals** - Event-driven architecture for clean code
- **Caching** - Performance optimization
- **Geolocation** - IP-API integration

---

## 🏗️ Architecture

### Event-Driven with Django Signals

The system uses **Django Signals** to maintain clean, decoupled code:

- ✅ Automatic slug generation
- ✅ Automatic cache management
- ✅ Automatic audit logging
- ✅ Automatic threat detection
- ✅ Automatic Caddy synchronization
- ✅ Automatic geographic statistics updates

**See `SIGNALS_DOCUMENTATION.md` for details**

### Tech Stack

- **Backend**: Django 5.0+
- **Frontend**: Tailwind CSS, Flowbite, Alpine.js
- **Database**: PostgreSQL / SQLite
- **Caching**: Django Cache Framework
- **Maps**: Leaflet.js with GeoJSON
- **Charts**: Chart.js
- **HTTP Client**: HTTPX
- **Reverse Proxy**: Caddy Server

---

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone <repository-url>
cd base-waf

# Create virtual environment
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### First Steps

1. **Access Admin Panel**: http://localhost:8000/admin
2. **Create a Site**: Add your first protected website
3. **Configure WAF**: Choose or create a WAF template
4. **View Analytics**: Check the dashboard at http://localhost:8000/analytics/

---

## 📖 Documentation

### Quick References
- **`QUICKSTART.md`** - Getting started guide
- **`SIGNALS_QUICK_REFERENCE.md`** - Signals quick lookup
- **`GEOGRAPHIC_VISUALIZATION.md`** - Map features guide
- **`DARK_MODE_GUIDE.md`** - Theme customization

### Detailed Documentation
- **`IMPLEMENTATION_SUMMARY.md`** - Complete feature overview
- **`SIGNALS_DOCUMENTATION.md`** - Signal system deep dive
- **`SIGNALS_ARCHITECTURE.md`** - Architecture diagrams
- **`TEST_SYSTEM.md`** - Testing guide

---

## 🎯 Core Components

### 1. WAF Rule Engine (`rules_engine.py`)
- Pattern-based threat detection
- SQL injection, XSS, path traversal detection
- Custom rule templates (basic/advanced)
- Configurable sensitivity levels

### 2. WAF Middleware (`waf_middleware.py`)
- Intercepts all requests
- Applies security rules
- Logs and blocks threats
- Integrates with geolocation

### 3. Proxy Middleware (`proxy_middleware.py`)
- Request forwarding using HTTPX
- Load balancing algorithms
- Automatic failover
- HTTP/2 support

### 4. Caddy Manager (`caddy_manager.py`)
- Automatic server configuration
- SSL certificate management
- Load balancer setup
- Dynamic site updates

### 5. Signals System (`signals.py`)
- 12 built-in signal handlers
- 5 custom signals
- Automatic operations
- Event-driven architecture

---

## 🌍 Geographic Dashboard Features

### Country Highlighting
- **Color-coded threats** - Red (critical), Orange (high), Yellow (blocked), Blue (high traffic), Green (normal)
- **Opacity by volume** - Darker = more requests
- **Interactive tooltips** - Detailed statistics on hover
- **Click for details** - Country-specific information
- **Legend** - Visual reference guide

### Analytics
- Request timeline charts
- Top source countries
- Request method distribution
- Threat level indicators
- Export capabilities

---

## 🔔 Signals & Events

The system fires signals for key events:

| Signal | When | Example Use |
|--------|------|-------------|
| `threat_detected` | Security threat found | Send email/SMS alert |
| `site_config_changed` | Site settings updated | Log configuration changes |
| `caddy_sync_required` | Caddy needs update | Trigger reconfiguration |
| `ssl_certificate_uploaded` | SSL files uploaded | Validate and deploy |
| `request_blocked` | Request blocked by WAF | Update statistics |

**Custom handlers are easy to add!**

```python
from django.dispatch import receiver
from site_mangement.signals import threat_detected

@receiver(threat_detected)
def my_handler(sender, alert, **kwargs):
    # Your custom logic
    send_slack_notification(alert)
```

---

## 🧪 Testing

```bash
# Run Django checks
python manage.py check

# Test signal system
python manage.py shell
>>> from site_mangement.models import Site
>>> Site.objects.create(host='test.com', protocol='http')
# Signals automatically: generate slug, create log, clear cache

# Sync all sites to Caddy
python manage.py sync_all_to_caddy --dry-run

# Run tests
python manage.py test
```

---

## 📊 Database Models

### Core Models
- **Site** - Protected websites
- **Addresses** - Backend server IPs
- **LoadBalancers** - Load balancing configuration
- **WafTemplate** - Reusable WAF rules
- **RequestAnalytics** - Request logs and analysis
- **Logs** - Security event logs
- **ThreatAlert** - Threat notifications
- **GeographicStats** - Geographic aggregations
- **EmailReport** - Scheduled reports

---

## 🎨 UI Features

### Dark Mode
- **Toggle button** - Switch themes instantly
- **Persistent preference** - Saved in localStorage
- **System detection** - Respects OS preference
- **Full coverage** - All components adapt

### Responsive Design
- Mobile-friendly navigation
- Adaptive layouts
- Touch-optimized controls
- Progressive enhancement

---

## 🔧 Configuration

### Settings
```python
# Enable WAF Middleware
MIDDLEWARE = [
    ...
    'site_mangement.waf_middleware.WAFMiddleware',
]

# Enable Proxy Middleware (optional)
MIDDLEWARE = [
    ...
    # 'site_mangement.proxy_middleware.ProxyMiddleware',
]
```

### Caddy Integration
```python
# Configure Caddy API endpoint
CADDY_API_URL = 'http://localhost:2019'
```

---

## 📦 Dependencies

### Python Packages
- Django >= 5.0
- requests >= 2.31.0
- httpx >= 0.27.0
- h2 >= 4.1.0
- django-compressor (for static assets)

### Frontend Libraries
- Tailwind CSS (CDN)
- Flowbite (CDN)
- Leaflet.js (CDN)
- Chart.js (CDN)

---

## 🚀 Deployment

### Production Checklist
- [ ] Set `DEBUG = False`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Set strong `SECRET_KEY`
- [ ] Enable HTTPS redirects
- [ ] Configure SSL certificates
- [ ] Set up database backups
- [ ] Configure email settings
- [ ] Review security settings

See Django's deployment checklist: `python manage.py check --deploy`

---

## 📝 License

[Your License Here]

---

## 🤝 Contributing

Contributions are welcome! The signal-based architecture makes it easy to add new features:

1. Fork the repository
2. Create a feature branch
3. Add your signal receiver
4. Submit a pull request

---

## 📧 Support

For questions or issues:
- Check documentation files
- Review signal handlers in `signals.py`
- Examine example implementations
- Open an issue on GitHub

---

## 🏆 Features at a Glance

✅ Advanced WAF with customizable rules  
✅ Real-time geographic threat visualization  
✅ Automatic Caddy server integration  
✅ Event-driven architecture with signals  
✅ Dark mode support  
✅ Load balancing with multiple algorithms  
✅ SSL certificate management  
✅ Comprehensive logging and analytics  
✅ Threat detection and alerting  
✅ Data export (CSV/JSON)  
✅ IP allowlist/blocklist  
✅ Responsive modern UI  
✅ Production-ready code  

---

**Built with ❤️ using Django and modern web technologies**

🛡️ **Protect your applications with confidence!**







