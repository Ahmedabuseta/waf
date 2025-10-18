# Server Startup & Verification Guide

## 🚀 Quick Start

### 1. Start the Development Server

```bash
cd base-waf
python manage.py runserver 0.0.0.0:8000
```

**Expected Output:**
```
Watching for file changes with StatReloader
Performing system checks...

System check identified no issues (0 silenced).
October 16, 2025 - 11:31:44
Django version 5.2.7, using settings 'waf_app.settings'
Starting development server at http://0.0.0.0:8000/
Quit the server with CONTROL-C.
```

### 2. Access the Application

Open your browser and navigate to:
- **Main Application:** http://localhost:8000/
- **Admin Interface:** http://localhost:8000/admin/
- **Sites List:** http://localhost:8000/sites/
- **Caddy Status:** http://localhost:8000/caddy/status/

---

## ✅ System Verification Checklist

### Pre-Flight Checks

Before starting, verify all components:

```bash
# 1. Check Python version (3.8+)
python --version

# 2. Verify virtual environment is activated
which python  # Should point to env/bin/python

# 3. Check Django installation
python -c "import django; print(django.get_version())"

# 4. Verify all dependencies
pip list | grep -E "django|dnspython|requests"

# 5. Run system checks
python manage.py check

# 6. Verify migrations
python manage.py showmigrations

# 7. Test SSL validation system
python test_ssl_validation.py
```

### Post-Startup Verification

After starting the server, verify functionality:

#### 1. Test Homepage
```bash
curl -I http://localhost:8000/
# Expected: HTTP 200 or 302 (redirect)
```

#### 2. Test Admin Access
```bash
curl -I http://localhost:8000/admin/
# Expected: HTTP 200 or 302 (login)
```

#### 3. Test API Endpoints
```bash
# Check Caddy status endpoint
curl http://localhost:8000/caddy/status/

# Check sites list
curl http://localhost:8000/sites/
```

---

## 🔧 Common Startup Issues & Solutions

### Issue 1: Port Already in Use

**Error:**
```
Error: That port is already in use.
```

**Solutions:**

**Option A: Use Different Port**
```bash
python manage.py runserver 0.0.0.0:8001
```

**Option B: Kill Existing Process**
```bash
# Find process using port 8000
lsof -ti:8000

# Kill the process
kill -9 $(lsof -ti:8000)

# Or use fuser (Linux)
fuser -k 8000/tcp
```

### Issue 2: Import Errors

**Error:**
```
ImportError: cannot import name 'XXX' from 'YYY'
```

**Solutions:**

```bash
# 1. Ensure all dependencies are installed
pip install -r requirements.txt

# 2. Install dnspython (required for DNS challenges)
pip install dnspython

# 3. Check Python path
echo $PYTHONPATH

# 4. Reinstall problematic packages
pip install --force-reinstall django
```

### Issue 3: Database Errors

**Error:**
```
django.db.utils.OperationalError: no such table: XXX
```

**Solutions:**

```bash
# 1. Run migrations
python manage.py migrate

# 2. If issues persist, reset database
rm db.sqlite3
python manage.py migrate
python manage.py createsuperuser

# 3. Load initial data (if available)
python manage.py loaddata initial_data.json
```

### Issue 4: Static Files Not Loading

**Error:**
```
404 errors for CSS/JS files
```

**Solutions:**

```bash
# 1. Collect static files
python manage.py collectstatic --noinput

# 2. Check static files settings
python manage.py diffsettings | grep STATIC

# 3. In development, ensure DEBUG=True
# In settings.py: DEBUG = True
```

### Issue 5: Module Not Found

**Error:**
```
ModuleNotFoundError: No module named 'site_mangement'
```

**Solutions:**

```bash
# 1. Check current directory
pwd  # Should be in base-waf directory

# 2. Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# 3. Ensure you're in the right environment
which python

# 4. Reinstall in development mode
pip install -e .
```

---

## 🌐 Production Deployment

### Using Gunicorn (Recommended)

```bash
# Install Gunicorn
pip install gunicorn

# Start with Gunicorn
gunicorn waf_app.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
```

### Using uWSGI

```bash
# Install uWSGI
pip install uwsgi

# Start with uWSGI
uwsgi --http :8000 \
    --module waf_app.wsgi:application \
    --master \
    --processes 4 \
    --threads 2
```

### Using Systemd Service

Create `/etc/systemd/system/base-waf.service`:

```ini
[Unit]
Description=Base WAF Django Application
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/path/to/base-waf
Environment="PATH=/path/to/base-waf/env/bin"
ExecStart=/path/to/base-waf/env/bin/gunicorn \
    --workers 4 \
    --bind 0.0.0.0:8000 \
    waf_app.wsgi:application

[Install]
WantedBy=multi-user.target
```

Start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl start base-waf
sudo systemctl enable base-waf
sudo systemctl status base-waf
```

---

## 🔍 Health Checks

### Basic Health Check Script

Create `health_check.sh`:

```bash
#!/bin/bash

echo "=== Base-WAF Health Check ==="

# Check if server is running
if curl -f -s http://localhost:8000/ > /dev/null; then
    echo "✅ Server is responding"
else
    echo "❌ Server is not responding"
    exit 1
fi

# Check database connectivity
python manage.py check --database default
if [ $? -eq 0 ]; then
    echo "✅ Database connection OK"
else
    echo "❌ Database connection failed"
    exit 1
fi

# Check Caddy connectivity (if configured)
if curl -f -s http://localhost:2019/config/ > /dev/null 2>&1; then
    echo "✅ Caddy API accessible"
else
    echo "⚠️  Caddy API not accessible (optional)"
fi

echo "=== Health Check Complete ==="
```

Make it executable:
```bash
chmod +x health_check.sh
./health_check.sh
```

---

## 📊 Monitoring & Logs

### View Django Logs

```bash
# Development server logs (console output)
python manage.py runserver

# Gunicorn logs
tail -f /var/log/gunicorn/access.log
tail -f /var/log/gunicorn/error.log

# Application logs (if configured)
tail -f logs/django.log
```

### View Caddy Logs

```bash
# Caddy manager logs
tail -f logs/caddy-manager/operations/caddy_operations.log

# Site-specific logs
tail -f logs/caddy-manager/sites/example.com.log

# Certificate operations
tail -f logs/caddy-manager/certificates/certificate_operations.log
```

### Monitor Server Performance

```bash
# CPU and Memory usage
top -p $(pgrep -f "manage.py runserver")

# Or use htop (if installed)
htop -p $(pgrep -f "manage.py runserver")

# Detailed process information
ps aux | grep python
```

---

## 🛠️ Development Workflow

### Daily Development Routine

```bash
# 1. Activate virtual environment
source env/bin/activate

# 2. Pull latest changes
git pull

# 3. Install/update dependencies
pip install -r requirements.txt

# 4. Run migrations
python manage.py migrate

# 5. Start development server
python manage.py runserver

# 6. Run tests (in another terminal)
python test_ssl_validation.py
python manage.py test
```

### Before Committing Changes

```bash
# 1. Run all checks
python manage.py check

# 2. Run tests
python test_ssl_validation.py
python manage.py test

# 3. Check code quality (if configured)
flake8 .
black --check .

# 4. Check migrations
python manage.py makemigrations --check --dry-run

# 5. Update requirements if needed
pip freeze > requirements.txt
```

---

## 🎯 Quick Commands Reference

### Server Management
```bash
# Start server
python manage.py runserver

# Start on specific port
python manage.py runserver 0.0.0.0:8001

# Start with different settings
python manage.py runserver --settings=waf_app.settings_production

# Run in background
nohup python manage.py runserver > server.log 2>&1 &
```

### Database Commands
```bash
# Run migrations
python manage.py migrate

# Create migrations
python manage.py makemigrations

# Show migrations status
python manage.py showmigrations

# Create superuser
python manage.py createsuperuser

# Django shell
python manage.py shell
```

### Utility Commands
```bash
# Collect static files
python manage.py collectstatic

# Clear cache
python manage.py clear_cache

# Check deployment readiness
python manage.py check --deploy

# Run tests
python manage.py test

# Load data
python manage.py loaddata fixture.json

# Dump data
python manage.py dumpdata app.model > fixture.json
```

---

## 🔐 Security Checklist

Before deploying to production:

- [ ] Change `SECRET_KEY` in settings.py
- [ ] Set `DEBUG = False`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Set up HTTPS/SSL
- [ ] Configure secure session cookies
- [ ] Enable CSRF protection
- [ ] Set up security headers
- [ ] Configure firewall rules
- [ ] Set up database backups
- [ ] Enable logging
- [ ] Configure rate limiting
- [ ] Review file permissions
- [ ] Set up monitoring/alerts

---

## 📞 Getting Help

### Check Documentation
- [SSL Configuration Guide](SSL_CONFIGURATION_GUIDE.md)
- [SSL Quick Start](SSL_QUICK_START.md)
- [Caddy Integration Summary](CADDY_INTEGRATION_SUMMARY.md)
- [Frontend Templates Guide](FRONTEND_TEMPLATES_GUIDE.md)

### Debug Mode
```python
# In settings.py, enable debug mode
DEBUG = True
DEBUG_PROPAGATE_EXCEPTIONS = True

# Enable verbose logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}
```

### Common Debug Commands
```bash
# Test specific URL
python manage.py runserver --noreload

# Django shell for debugging
python manage.py shell

# Show all URLs
python manage.py show_urls  # (if django-extensions installed)

# Check specific setting
python manage.py diffsettings | grep SETTING_NAME
```

---

## ✅ Success Indicators

Your server is running correctly if:

1. ✅ No errors in console output
2. ✅ Homepage loads at http://localhost:8000/
3. ✅ Admin interface accessible
4. ✅ Static files load correctly (CSS/JS)
5. ✅ Database queries work
6. ✅ No 404 errors for main URLs
7. ✅ Logs show normal activity
8. ✅ Health check script passes

---

## 🎉 Ready to Use!

Your Base-WAF server is now running and ready for:

- ✅ SSL/TLS certificate management
- ✅ Caddy integration and configuration
- ✅ Site creation and management
- ✅ DNS challenge workflows
- ✅ Certificate monitoring
- ✅ WAF rule management
- ✅ Analytics and logging

**Next Steps:**
1. Create your first site
2. Configure SSL certificates
3. Set up Caddy integration
4. Review the documentation
5. Explore the admin interface

**Enjoy your WAF! 🛡️**