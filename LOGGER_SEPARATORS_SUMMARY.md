# Logger Separators Summary

## Overview

Added visual separator lines (`######`) to logging output for Caddy operations and Django signals to improve log readability and make it easier to identify important operations in log files.

---

## Changes Made

### 1. Enhanced Caddy Manager (`site_management/utils/enhanced_caddy_manager.py`)

Added logger separators with `######` to the following operations:

#### **Add Site Operation**

- ✅ **Success Case:**
  ```
  ##############################
  # CADDY ADD SITE COMPLETE: example.com
  ##############################
  ```

- ❌ **Failed Case:**
  ```
  ##############################
  # CADDY ADD SITE FAILED: example.com
  ##############################
  ```

- ❌ **Error Case:**
  ```
  ##############################
  # CADDY ADD SITE ERROR: example.com
  # ERROR: Connection refused
  ##############################
  ```

#### **Update Site Operation**

- 🔄 **Start:**
  ```
  ##############################
  # CADDY UPDATE SITE START: example.com
  ##############################
  ```

#### **Remove Site Operation**

- ✅ **Success Case:**
  ```
  ##############################
  # CADDY REMOVE SITE COMPLETE: example.com
  ##############################
  ```

- ❌ **Failed Case:**
  ```
  ##############################
  # CADDY REMOVE SITE FAILED: example.com
  ##############################
  ```

- ❌ **Error Case:**
  ```
  ##############################
  # CADDY REMOVE SITE ERROR: example.com
  # ERROR: File not found
  ##############################
  ```

---

### 2. Django Signals (`site_management/signals.py`)

Added logger separators to signal handlers:

#### **Site Creation Signal**
```python
@receiver(post_save, sender=Site)
def site_post_save_handler(sender, instance, created, **kwargs):
    if created:
        logger.info("##############################")
        logger.info(f"# SITE CREATED: {instance.host}")
        logger.info("##############################")
```

**Log Output:**
```
##############################
# SITE CREATED: example.com
##############################
```

#### **Site Deletion Signal**
```python
@receiver(post_delete, sender=Site)
def site_post_delete_handler(sender, instance, **kwargs):
    logger.info("##############################")
    logger.info(f"# SITE DELETED: {instance.host}")
    logger.info("##############################")
```

**Log Output:**
```
##############################
# SITE DELETED: example.com
##############################
...
##############################
# CADDY DELETE SYNC TRIGGERED: example.com
##############################
```

#### **Caddy Sync Required Signal**
```python
@receiver(caddy_sync_required)
def handle_caddy_sync_required(sender, site, action, **kwargs):
    logger.info("##############################")
    logger.info(f"# CADDY SYNC REQUIRED: {site.host}")
    logger.info(f"# ACTION: {action}")
    logger.info("##############################")
    
    # Automatic Caddy sync is now implemented!
    # - Creates CaddyConfig from site settings
    # - Calls EnhancedCaddyManager.add_site() for 'update' action
    # - Calls EnhancedCaddyManager.remove_site() for 'delete' action
    # - Logs success/failure with separators
```

**Log Output:**
```
##############################
# CADDY SYNC REQUIRED: example.com
# ACTION: update
##############################
2024-01-15 14:40:23 - caddy_manager - INFO - Caddy sync required for site example.com: update
##############################
# CADDY AUTO-SYNC SUCCESS: example.com
##############################
```

#### **SSL Certificate Upload Signal**
```python
@receiver(ssl_certificate_uploaded)
def handle_ssl_certificate_uploaded(sender, site, **kwargs):
    logger.info("##############################")
    logger.info(f"# SSL CERTIFICATE UPLOADED: {site.host}")
    logger.info("##############################")
    ...
    logger.info("##############################")
    logger.info(f"# SSL SYNC TRIGGERED: {site.host}")
    logger.info("##############################")
```

**Log Output:**
```
##############################
# SSL CERTIFICATE UPLOADED: example.com
##############################
...
##############################
# SSL SYNC TRIGGERED: example.com
##############################
```

---

## 🚀 Automatic Caddy Sync (NEW!)

### Overview

The TODO has been implemented! Sites now **automatically sync to Caddy** when you:
- ✅ Create a site in Django Admin
- ✅ Update site configuration (protocol, SSL, etc.)
- ✅ Delete a site
- ✅ Upload SSL certificates

No manual Caddy sync required anymore!

### How It Works

```python
# When you create/update a site in Django...
site = Site.objects.create(host="example.com", protocol="https", ...)

# Signal fires automatically
site_post_save_handler() → caddy_sync_required.send()

# Signal handler automatically syncs to Caddy
handle_caddy_sync_required() → EnhancedCaddyManager.add_site()

# Result: Site is live in Caddy automatically!
```

### Supported Actions

1. **Create/Update** (`action='update'`)
   - Retrieves site addresses
   - Creates CaddyConfig
   - Calls `caddy.add_site(config)`
   - Logs success/failure with separators

2. **Delete** (`action='delete'`)
   - Calls `caddy.remove_site(domain)`
   - Removes Caddy configuration
   - Logs success/failure with separators

3. **SSL Update** (`action='update_ssl'`)
   - Updates SSL certificates
   - Calls `caddy.update_site(config)`
   - Logs success/failure with separators

### Example Log Flow

```
# User creates site in Django Admin
##############################
# SITE CREATED: myapp.com
##############################

# Automatic sync triggered
##############################
# CADDY SYNC REQUIRED: myapp.com
# ACTION: update
##############################

# Caddy manager processes request
2024-01-15 15:30:12 - caddy_manager - INFO - Validating configuration...
2024-01-15 15:30:12 - caddy_manager - INFO - Generating Caddy config...

# Success!
##############################
# CADDY AUTO-SYNC SUCCESS: myapp.com
##############################
```

---

## Benefits

### 1. **Improved Log Readability**
- Clear visual separation between different operations
- Easy to scan large log files
- Quickly identify start and end of operations

### 2. **Better Debugging**
- Instantly spot where operations begin and end
- Identify failures at a glance
- Trace operation flow through the system

### 3. **Monitoring & Alerting**
- Easy to grep for specific operations: `grep "######" logs/caddy_operations.log`
- Pattern matching for automated monitoring
- Quick identification of errors

### 4. **Production Support**
- Operations teams can quickly find relevant log entries
- Reduced time to diagnose issues
- Clear audit trail of Caddy operations

---

## Example Log Output

### Successful Site Addition (Automatic Sync)
```
##############################
# SITE CREATED: example.com
##############################
2024-01-15 14:23:45 - django.signals - INFO - New site created: example.com
##############################
# CADDY SYNC REQUIRED: example.com
# ACTION: update
##############################
2024-01-15 14:23:45 - caddy_manager - INFO - [example.com] ADD_SITE_START - SUCCESS
2024-01-15 14:23:45 - caddy_manager - INFO - [example.com] Validating configuration...
2024-01-15 14:23:45 - caddy_manager - INFO - [example.com] Generating Caddy config...
2024-01-15 14:23:45 - caddy_manager - INFO - [example.com] Reloading Caddy...
##############################
# CADDY ADD SITE COMPLETE: example.com
##############################
##############################
# CADDY AUTO-SYNC SUCCESS: example.com
##############################
```

### Failed Site Removal
```
2024-01-15 14:30:12 - caddy_manager - INFO - [old-site.com] REMOVE_SITE_START
2024-01-15 14:30:12 - caddy_manager - ERROR - [old-site.com] Caddy API connection failed
##############################
# CADDY REMOVE SITE FAILED: old-site.com
##############################
2024-01-15 14:30:12 - caddy_manager - ERROR - [old-site.com] REMOVE_SITE_FAILED
```

### Site Configuration Update
```
##############################
# SITE CREATED: new-site.com
##############################
2024-01-15 14:35:20 - django.signals - INFO - New site created: new-site.com
##############################
# CADDY SYNC REQUIRED: new-site.com
# ACTION: update
##############################
2024-01-15 14:35:20 - django.signals - INFO - Caddy sync required for site new-site.com: update
```

---

## Log File Locations

### Caddy Manager Logs
```
logs/caddy-manager/
├── operations/
│   └── caddy_operations.log        # Main operations log (has separators)
├── sites/
│   ├── example.com.log              # Per-site logs
│   └── test.example.com.log
└── certificates/
    └── certificate_operations.log   # Certificate-specific logs
```

### Django Application Logs
- Default Django logging (console and file)
- Signal operations appear in main Django log
- Also duplicated in Caddy operations log when relevant

---

## Viewing Logs with Separators

### Command Line (with color highlighting)
```bash
# View recent operations with separators highlighted
tail -f logs/caddy-manager/operations/caddy_operations.log | grep --color -E "######|ERROR|COMPLETE"

# Find all site additions
grep "CADDY ADD SITE" logs/caddy-manager/operations/caddy_operations.log

# Find all failures
grep -A 2 "FAILED" logs/caddy-manager/operations/caddy_operations.log

# Count operations today
grep "######" logs/caddy-manager/operations/caddy_operations.log | grep "$(date +%Y-%m-%d)" | wc -l
```

### Using Test Script
```bash
# Run test to see separators in action
python test_caddy_logger.py

# View existing logs only
python test_caddy_logger.py view
```

---

## Integration Points

### Where Separators Appear

1. **Direct Caddy Operations**
   - When `EnhancedCaddyManager.add_site()` is called
   - When `EnhancedCaddyManager.remove_site()` is called
   - When `EnhancedCaddyManager.update_site()` is called

2. **Django Admin Actions**
   - Creating a new site → triggers `site_post_save_handler` → **automatic Caddy sync**
   - Updating a site → triggers `site_post_save_handler` → **automatic Caddy sync**
   - Deleting a site → triggers `site_post_delete_handler` → **automatic Caddy sync**
   - Uploading SSL certificates → triggers `handle_ssl_certificate_uploaded` → **automatic Caddy sync**

3. **Automatic Sync (NEW!)**
   - ✅ Site creation automatically syncs to Caddy
   - ✅ Site updates automatically sync to Caddy
   - ✅ Site deletion automatically removes from Caddy
   - ✅ SSL certificate changes automatically update Caddy
   - All automatic syncs include separator logging

4. **API Endpoints**
   - Any API call that modifies site configuration
   - Triggers automatic Caddy sync via signals

5. **Management Commands**
   - `python manage.py sync_caddy`
   - `python manage.py setup_ssl`

---

## Configuration

### Logger Settings (already configured)

```python
# waf_app/settings.py

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/caddy-manager/operations/caddy_operations.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'caddy_manager': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

### Caddy Logger Directory
```python
CADDY_LOG_DIR = os.path.join(BASE_DIR, 'logs', 'caddy-manager')
```

---

## Testing

### Manual Test - Logger Separators
```bash
# Run the logger test script
python test_caddy_logger.py

# Expected output:
# - Console shows test progress
# - Logs show separator lines
# - Both success and error cases demonstrated
```

### Manual Test - Automatic Caddy Sync
```bash
# Run the automatic sync test script
python test_auto_caddy_sync.py

# Expected output:
# - Tests site creation, update, deletion
# - Shows automatic Caddy sync in action
# - Displays all separator lines
# - Tests signal handlers
```

### Check Logs
```bash
# View operations log
cat logs/caddy-manager/operations/caddy_operations.log

# Should see entries like:
# ##############################
# # CADDY ADD SITE COMPLETE: test-logger.example.com
# ##############################
```

### Production Verification
```bash
# After deploying a site, check logs
tail -n 50 logs/caddy-manager/operations/caddy_operations.log

# Look for separator lines around your operation
```

---

## Troubleshooting

### Separators Not Appearing

**Problem:** Logger separators are not showing up in logs

**Solutions:**
1. Verify logging is enabled:
   ```python
   caddy = EnhancedCaddyManager(enable_logging=True)
   ```

2. Check log file exists:
   ```bash
   ls -la logs/caddy-manager/operations/caddy_operations.log
   ```

3. Verify logger initialization:
   ```python
   # In enhanced_caddy_manager.py
   if self.logger:
       self.logger.main_logger.info("Test message")
   ```

### Log File Not Created

**Problem:** Log directory or file doesn't exist

**Solution:**
```bash
# Create log directories
mkdir -p logs/caddy-manager/{operations,sites,certificates}

# Set permissions
chmod -R 755 logs/
```

### Too Many Log Entries

**Problem:** Logs getting too large

**Solution:**
1. Implement log rotation:
   ```bash
   # /etc/logrotate.d/waf-caddy
   /path/to/base-waf/logs/caddy-manager/**/*.log {
       daily
       rotate 7
       compress
       delaycompress
       missingok
       notifempty
   }
   ```

2. Or use Python's RotatingFileHandler (configure in settings.py)

---

## Summary of Files Modified

| File | Changes | Lines Added |
|------|---------|-------------|
| `site_management/utils/enhanced_caddy_manager.py` | Added separators to add/remove/update operations | ~30 lines |
| `site_management/signals.py` | Added separators to signal handlers | ~40 lines |
| `test_caddy_logger.py` | New test script | 232 lines (new) |

---

## Future Enhancements

### Possible Improvements

1. **Configurable Separator Style**
   ```python
   CADDY_LOG_SEPARATOR = "=" * 50  # Customizable
   ```

2. **Log Levels for Separators**
   ```python
   # Different separators for different levels
   INFO: "##############################"
   WARNING: "!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
   ERROR: "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
   ```

3. **Structured Logging**
   - JSON format for machine parsing
   - Keep separators for human-readable logs

4. **Metrics Collection**
   - Count operations per day
   - Track success/failure rates
   - Generate reports from separator-delimited sections

---

## Related Documentation

- [CADDY_INTEGRATION_SUMMARY.md](./CADDY_INTEGRATION_SUMMARY.md) - Caddy integration overview
- [DATABASE_MANAGEMENT.md](./DATABASE_MANAGEMENT.md) - Database backup and restore
- [ANALYTICS_README.md](./ANALYTICS_README.md) - Analytics system

## Test Scripts

- `test_caddy_logger.py` - Test logger separators
- `test_auto_caddy_sync.py` - Test automatic Caddy sync via signals

---

**Last Updated:** 2024-01-15  
**Version:** 2.0 (Added automatic Caddy sync implementation)  
**Author:** WAF Development Team