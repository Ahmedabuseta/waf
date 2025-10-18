# SSL/TLS Certificate Management System

## 🎯 Overview

A comprehensive SSL/TLS certificate validation and management system for the Base-WAF project. This system ensures secure certificate handling, automatic validation, protocol consistency, and supports both manual certificates and Let's Encrypt automatic SSL with wildcard domain support.

## ✨ Features

### Core Validation
- ✅ **Protocol-Based Validation** - HTTP sites cannot have SSL, HTTPS sites must have SSL
- ✅ **Certificate Format Validation** - Ensures PEM format for certificates and keys
- ✅ **Expiration Checking** - Warns when certificates expire in < 7 days
- ✅ **Key Strength Enforcement** - Minimum 2048-bit RSA keys required
- ✅ **Certificate-Key Matching** - Validates certificate and private key match
- ✅ **Chain Validation** - Validates certificate chain integrity
- ✅ **Domain Coverage** - Ensures certificate covers the site's hostname

### Wildcard Certificate Support
- ✅ **Subdomain Detection** - Automatically detects when wildcard certificate is needed
- ✅ **DNS-01 Challenge** - Full support for DNS-based ACME challenges
- ✅ **DNS Propagation Checking** - Verify DNS records across multiple servers
- ✅ **Multi-Provider Support** - Cloudflare, Route53, GoDaddy, Namecheap, etc.
- ✅ **Step-by-Step Instructions** - Detailed DNS challenge setup guides

### Automation
- ✅ **Auto SSL with Let's Encrypt** - Automatic certificate issuance and renewal
- ✅ **Model-Level Validation** - Enforced at Django ORM level
- ✅ **Form-Level Validation** - Comprehensive validation in forms
- ✅ **Real-Time Validation** - Immediate feedback on certificate uploads

## 📁 Project Structure

```
base-waf/
├── site_mangement/
│   ├── models.py                    # Enhanced Site model with SSL validation
│   ├── forms.py                     # Enhanced SiteForm with certificate validation
│   ├── validators.py                # SiteSSLValidator - core validation logic
│   ├── ssl_helpers.py               # SSLHelper - view-level utilities
│   └── utils/
│       ├── acme_dns_manager.py      # ACMEDNSManager - DNS challenge handling
│       ├── certificate_checker.py   # CertificateChecker - certificate utilities
│       ├── certificate_operations.py # Core certificate operations
│       ├── certificate_validation.py # Certificate validation logic
│       └── certificate_formatter.py  # Certificate info formatting
├── SSL_CONFIGURATION_GUIDE.md       # Complete user documentation (666 lines)
├── SSL_IMPLEMENTATION_SUMMARY.md    # Technical implementation details (541 lines)
├── SSL_QUICK_START.md               # 5-minute quick start guide (378 lines)
├── SSL_README.md                    # This file
└── test_ssl_validation.py           # Comprehensive test suite (341 lines)
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install dnspython
```

### 2. Run Migrations

```bash
python manage.py migrate
```

### 3. Test the System

```bash
python test_ssl_validation.py
```

### 4. Create Your First Site

#### Option A: HTTP Site (No SSL)
```python
from site_mangement.models import Site

site = Site.objects.create(
    host='example.com',
    slug='example-com',
    protocol='http',
    auto_ssl=False,
    support_subdomains=False,
    status='active'
)
```

#### Option B: HTTPS with Auto SSL
```python
site = Site.objects.create(
    host='example.com',
    slug='example-com',
    protocol='https',
    auto_ssl=True,
    support_subdomains=False,
    status='active'
)
# Certificate automatically managed by Let's Encrypt
```

#### Option C: HTTPS with Manual Certificate
```python
from django.core.files import File

with open('cert.pem', 'rb') as cert, open('key.pem', 'rb') as key:
    site = Site.objects.create(
        host='example.com',
        slug='example-com',
        protocol='https',
        auto_ssl=False,
        ssl_certificate=File(cert),
        ssl_key=File(key),
        status='active'
    )
```

#### Option D: Wildcard Certificate (*.example.com)
```python
site = Site.objects.create(
    host='example.com',
    slug='example-com',
    protocol='https',
    auto_ssl=True,
    support_subdomains=True,  # Requires DNS-01 challenge
    status='active'
)

if site.requires_dns_challenge():
    print("DNS Challenge Required - See documentation")
```

## 📚 Documentation

### For End Users
- **[SSL_QUICK_START.md](SSL_QUICK_START.md)** - Get started in 5 minutes
- **[SSL_CONFIGURATION_GUIDE.md](SSL_CONFIGURATION_GUIDE.md)** - Complete configuration guide with examples

### For Developers
- **[SSL_IMPLEMENTATION_SUMMARY.md](SSL_IMPLEMENTATION_SUMMARY.md)** - Technical architecture and API documentation
- **Code Documentation** - All classes and methods have comprehensive docstrings

## 🔐 Validation Rules

### Rule Matrix

| Protocol | auto_ssl | ssl_certificate | Valid? | Notes |
|----------|----------|-----------------|--------|-------|
| HTTP | False | None | ✅ | Basic HTTP |
| HTTP | True | None | ❌ | Cannot enable SSL on HTTP |
| HTTP | False | Uploaded | ❌ | Cannot upload cert on HTTP |
| HTTPS | True | None | ✅ | Auto SSL (Let's Encrypt) |
| HTTPS | False | Uploaded | ✅ | Manual certificate |
| HTTPS | False | None | ❌ | HTTPS requires SSL config |

### Certificate Requirements

When uploading manual certificates:
- ✅ Certificate file is **required**
- ✅ Private key file is **required**
- ⚠️ Certificate chain is **recommended** (optional)
- ✅ Must be in PEM format
- ✅ Minimum 2048-bit key strength
- ✅ Certificate must not be expired
- ✅ Certificate and key must match
- ✅ Certificate must cover the site's hostname

### Wildcard Requirements

When `support_subdomains=True`:
- ✅ Protocol must be `https`
- ✅ If manual cert: Must include `*.example.com` in SAN
- ✅ If auto_ssl: Requires DNS-01 challenge

## 🌐 DNS Challenge Workflow

For wildcard certificates with auto SSL:

### Step 1: Create Site
```python
site = Site.objects.create(
    host='example.com',
    protocol='https',
    auto_ssl=True,
    support_subdomains=True
)
```

### Step 2: Get DNS Instructions
```python
from site_mangement.utils import ACMEDNSManager

dns_manager = ACMEDNSManager()
instructions = dns_manager.generate_challenge_instructions(
    domain='example.com',
    support_subdomains=True
)

print(f"Create TXT record: {instructions['challenge_record']}")
```

### Step 3: Create DNS Record

In your DNS provider, create:
- **Type:** TXT
- **Name:** `_acme-challenge.example.com`
- **Value:** `<ACME_CHALLENGE_VALUE>`
- **TTL:** 300

### Step 4: Verify DNS
```python
verification = dns_manager.verify_dns_challenge_record(
    domain='example.com',
    expected_value='<CHALLENGE_VALUE>'
)

if verification['exists']:
    print("✅ DNS record verified!")
```

### Step 5: Check Propagation
```python
propagation = dns_manager.check_dns_propagation(
    domain='example.com',
    expected_value='<CHALLENGE_VALUE>'
)

print(f"Propagated: {propagation['propagation_percentage']}%")
```

## 🔧 API Examples

### Using Forms (Recommended)
```python
from site_mangement.forms import SiteForm

form = SiteForm(request.POST, request.FILES)
if form.is_valid():
    site = form.save()
    
    # Check for DNS challenge
    dns_info = form.get_dns_challenge_info()
    if dns_info and dns_info['required']:
        # Show DNS instructions to user
        pass
else:
    # Show validation errors
    for error in form.errors:
        print(error)
```

### Using Validators Directly
```python
from site_mangement.validators import SiteSSLValidator

validator = SiteSSLValidator()
is_valid, errors = validator.validate_site_ssl_configuration(
    protocol='https',
    auto_ssl=False,
    support_subdomains=True,
    host='example.com',
    ssl_certificate=cert_file,
    ssl_key=key_file
)

if not is_valid:
    for error in errors:
        print(f"❌ {error}")
```

### Using SSL Helper (Views)
```python
from site_mangement.ssl_helpers import SSLHelper

helper = SSLHelper()
site = Site.objects.get(host='example.com')

# Get SSL info
ssl_info = helper.get_site_ssl_info(site)

# Check warnings
warnings = helper.get_ssl_configuration_warnings(site)

# Check renewal status
renewal = helper.get_certificate_renewal_status(site)
```

## 🧪 Testing

### Run Test Suite
```bash
python test_ssl_validation.py
```

### Expected Output
```
✅ All test suites completed successfully!

The SSL validation system is working correctly:
  • SSL configuration validation
  • DNS challenge generation for wildcard certificates
  • Site model validation
  • Helper functions for views
  • Certificate checker utilities
```

### Test Coverage
- ✅ Protocol validation rules
- ✅ Auto SSL configuration
- ✅ Manual certificate validation
- ✅ Domain coverage checking
- ✅ Wildcard certificate validation
- ✅ DNS challenge generation
- ✅ DNS record verification
- ✅ Model-level validation
- ✅ Form-level validation

## ⚠️ Common Issues

### Issue: "HTTP protocol cannot have auto_ssl enabled"
**Solution:** Change protocol to HTTPS or disable auto_ssl

### Issue: "HTTPS requires SSL configuration"
**Solution:** Either enable auto_ssl or upload certificates

### Issue: "Certificate and key do not match"
**Solution:** Verify with OpenSSL:
```bash
openssl x509 -noout -modulus -in cert.pem | openssl md5
openssl rsa -noout -modulus -in key.pem | openssl md5
```

### Issue: "Certificate does not cover domain"
**Solution:** Check certificate SANs:
```bash
openssl x509 -noout -text -in cert.pem | grep -A1 "Subject Alternative Name"
```

### Issue: DNS Challenge Not Propagating
**Checklist:**
1. Verify TXT record: `dig TXT _acme-challenge.example.com +short`
2. Wait 5-60 minutes for propagation
3. Check multiple DNS servers
4. Verify no typos in record name/value

## 🎓 Best Practices

### Security
- ✅ Never commit private keys to version control
- ✅ Use environment variables for sensitive configuration
- ✅ Rotate certificates and keys periodically
- ✅ Monitor certificate transparency logs
- ✅ Enable HTTPS for admin interface

### Operations
- ✅ Use Auto SSL when possible (easier maintenance)
- ✅ Always include certificate chain for manual certs
- ✅ Monitor certificate expiration (renew before 7 days)
- ✅ Test in staging before production
- ✅ Set up alerts for expiring certificates

### Performance
- ✅ Cache certificate information after validation
- ✅ Use background tasks for DNS propagation monitoring
- ✅ Batch certificate renewals
- ✅ Clean up temporary files promptly

## 📊 System Architecture

### Validation Flow
```
User Input → SiteForm → SiteSSLValidator → Site Model → Database
                ↓              ↓              ↓
         Certificate    Domain Coverage   Model
          Validation      Validation      Validation
                ↓              ↓              ↓
           CertChecker    ACMEManager    full_clean()
```

### Component Layers
```
┌─────────────────────────────────────────────┐
│           Presentation Layer                 │
│  (Forms, Views, Templates, API)              │
└───────────────┬─────────────────────────────┘
                │
┌───────────────┴─────────────────────────────┐
│           Business Logic Layer               │
│  (Validators, SSLHelper, ACMEManager)        │
└───────────────┬─────────────────────────────┘
                │
┌───────────────┴─────────────────────────────┐
│            Data Layer                        │
│  (Models, CertificateChecker)                │
└──────────────────────────────────────────────┘
```

## 📦 Dependencies

### Required
- Django 4.0+
- dnspython 2.8.0+
- OpenSSL (system package)

### Optional
- python-decouple (for environment variables)
- celery (for background tasks)
- redis (for caching)

## 🔄 Migration Guide

### From Existing System

1. **Backup existing data**
```bash
python manage.py dumpdata site_mangement.site > backup.json
```

2. **Run migrations**
```bash
python manage.py migrate
```

3. **Update existing sites**
```python
from site_mangement.models import Site

for site in Site.objects.filter(protocol='http'):
    site.auto_ssl = False
    site.support_subdomains = False
    site.save()
```

4. **Validate configuration**
```bash
python test_ssl_validation.py
```

## 📈 Performance

### Benchmarks
- Certificate validation: ~50ms per certificate
- DNS query: ~100-500ms per query
- DNS propagation check: ~2-5s (6 servers)
- Form validation: ~100-200ms

### Optimization Tips
1. Cache DNS query results
2. Use async for DNS propagation checks
3. Validate certificates only on upload/change
4. Pre-validate before database save

## 🐛 Troubleshooting

### Debug Mode
Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check System Status
```bash
python manage.py check
python test_ssl_validation.py
```

### Verify OpenSSL
```bash
openssl version
which openssl
```

### Test DNS Resolution
```bash
dig TXT _acme-challenge.example.com
nslookup -type=TXT _acme-challenge.example.com
```

## 📞 Support & Resources

### Documentation
- [Quick Start Guide](SSL_QUICK_START.md)
- [Configuration Guide](SSL_CONFIGURATION_GUIDE.md)
- [Implementation Summary](SSL_IMPLEMENTATION_SUMMARY.md)

### External Resources
- [Let's Encrypt Docs](https://letsencrypt.org/docs/)
- [ACME Protocol RFC](https://tools.ietf.org/html/rfc8555)
- [OpenSSL Docs](https://www.openssl.org/docs/)

### Testing Tools
- [SSL Labs](https://www.ssllabs.com/ssltest/)
- [DNS Checker](https://dnschecker.org/)
- [Certificate Decoder](https://certlogik.com/decoder/)

## 📝 License

This SSL validation system is part of the Base-WAF project.

## 🙏 Contributing

When contributing SSL-related features:
1. Follow existing validation patterns
2. Add comprehensive tests
3. Update documentation
4. Test with real certificates
5. Consider security implications

## 📅 Version History

- **v1.0** (2024) - Initial release
  - Protocol-based validation
  - Certificate validation
  - Wildcard certificate support
  - DNS-01 challenge support
  - Comprehensive documentation

---

**Status:** Production Ready ✅  
**Maintainer:** Base-WAF Team  
**Last Updated:** 2024

## 🚀 Next Steps

After setup:
1. ✅ Review [SSL_QUICK_START.md](SSL_QUICK_START.md)
2. ✅ Run test suite: `python test_ssl_validation.py`
3. ✅ Create test site with different configurations
4. ✅ Test DNS challenge workflow (if using wildcards)
5. ✅ Integrate with your frontend/UI
6. ✅ Set up monitoring for certificate expiration

**Need help?** Check the [Configuration Guide](SSL_CONFIGURATION_GUIDE.md) for detailed instructions!