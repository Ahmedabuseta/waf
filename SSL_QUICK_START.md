# SSL/TLS Quick Start Guide

## 🚀 Quick Start - 5 Minutes to SSL Validation

This guide gets you up and running with SSL/TLS validation in 5 minutes.

## 📋 Prerequisites

- Django project running
- Python 3.8+
- OpenSSL installed
- `dnspython` package installed

```bash
pip install dnspython
```

## 🎯 Common Use Cases

### Use Case 1: HTTP Site (No SSL)

```python
from site_mangement.models import Site

# Create an HTTP site - simplest configuration
site = Site.objects.create(
    host='example.com',
    slug='example-com',
    protocol='http',
    auto_ssl=False,
    support_subdomains=False,
    status='active'
)
```

**Rules:**
- ✅ `protocol='http'`
- ✅ `auto_ssl=False`
- ❌ Cannot upload certificates

---

### Use Case 2: HTTPS with Auto SSL (Recommended)

```python
# Let's Encrypt will automatically manage certificates
site = Site.objects.create(
    host='secure.example.com',
    slug='secure-example-com',
    protocol='https',
    auto_ssl=True,
    support_subdomains=False,
    status='active'
)
```

**What happens:**
- ✅ Certificate automatically obtained from Let's Encrypt
- ✅ Auto-renewal every 90 days
- ✅ Zero configuration needed
- ✅ Uses HTTP-01 challenge

---

### Use Case 3: HTTPS with Wildcard (*.example.com)

```python
# Covers example.com and all subdomains (*.example.com)
site = Site.objects.create(
    host='example.com',
    slug='example-com',
    protocol='https',
    auto_ssl=True,
    support_subdomains=True,  # Wildcard certificate
    status='active'
)

# Check if DNS challenge is needed
if site.requires_dns_challenge():
    print("⚠️ DNS TXT record required!")
    # See "DNS Challenge Setup" below
```

**What happens:**
- ⚠️ Requires DNS-01 challenge
- ⚠️ You must create a TXT record in DNS
- ⚠️ DNS propagation takes 5-60 minutes

---

### Use Case 4: Upload Your Own Certificate

```python
from django.core.files import File

# Upload your own certificates
with open('cert.pem', 'rb') as cert, \
     open('key.pem', 'rb') as key:
    
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

**Validation checks:**
- ✅ Certificate format (PEM)
- ✅ Not expired
- ✅ Certificate and key match
- ✅ Covers your domain
- ✅ Key strength (min 2048 bits)

---

## 🌐 DNS Challenge Setup (Wildcard Certificates)

### Step 1: Get Instructions

```python
from site_mangement.utils import ACMEDNSManager

dns_manager = ACMEDNSManager()
instructions = dns_manager.generate_challenge_instructions(
    domain='example.com',
    support_subdomains=True
)

print(f"Create this DNS record:")
print(f"  Type: TXT")
print(f"  Name: {instructions['challenge_record']}")
print(f"  Value: <ACME_CHALLENGE_VALUE>")
```

### Step 2: Create DNS Record

Go to your DNS provider (Cloudflare, Route53, GoDaddy, etc.) and create:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| TXT | `_acme-challenge.example.com` | `<CHALLENGE_VALUE>` | 300 |

### Step 3: Verify DNS Record

```python
# Verify the record exists
verification = dns_manager.verify_dns_challenge_record(
    domain='example.com',
    expected_value='<CHALLENGE_VALUE>'
)

if verification['exists']:
    print("✅ DNS record found!")
else:
    print(f"⚠️ {verification['message']}")
```

### Step 4: Check Propagation

```python
# Check propagation across multiple DNS servers
propagation = dns_manager.check_dns_propagation(
    domain='example.com',
    expected_value='<CHALLENGE_VALUE>'
)

print(f"Propagated: {propagation['propagation_percentage']}%")

if propagation['fully_propagated']:
    print("✅ Ready to proceed!")
```

---

## 📝 Using Forms (Web Interface)

```python
from site_mangement.forms import SiteForm

# Handle form submission
if request.method == 'POST':
    form = SiteForm(request.POST, request.FILES)
    
    if form.is_valid():
        site = form.save()
        
        # Check if DNS challenge is needed
        dns_info = form.get_dns_challenge_info()
        if dns_info and dns_info['required']:
            # Show DNS instructions to user
            return render(request, 'dns_challenge.html', {
                'dns_info': dns_info
            })
        
        return redirect('site_detail', site.id)
    else:
        # Show validation errors
        return render(request, 'site_form.html', {
            'form': form,
            'errors': form.errors
        })
```

---

## ⚠️ Common Errors & Solutions

### Error: "HTTP protocol cannot have auto_ssl enabled"

```python
# ❌ Wrong
site.protocol = 'http'
site.auto_ssl = True  # ERROR!

# ✅ Fix: Change to HTTPS
site.protocol = 'https'
site.auto_ssl = True
```

### Error: "HTTPS requires SSL configuration"

```python
# ❌ Wrong
site.protocol = 'https'
site.auto_ssl = False
# No certificate uploaded - ERROR!

# ✅ Fix Option 1: Enable auto SSL
site.auto_ssl = True

# ✅ Fix Option 2: Upload certificate
site.ssl_certificate = cert_file
site.ssl_key = key_file
```

### Error: "Certificate and key do not match"

```bash
# Verify they match
openssl x509 -noout -modulus -in cert.pem | openssl md5
openssl rsa -noout -modulus -in key.pem | openssl md5
# Both outputs should be identical
```

### Error: "Certificate does not cover domain"

```bash
# Check what domains the certificate covers
openssl x509 -noout -text -in cert.pem | grep -A1 "Subject Alternative Name"
```

---

## 🔍 Check SSL Status

```python
from site_mangement.ssl_helpers import SSLHelper

helper = SSLHelper()
site = Site.objects.get(host='example.com')

# Get SSL info
ssl_info = helper.get_site_ssl_info(site)
print(f"SSL Enabled: {ssl_info['ssl_enabled']}")
print(f"SSL Type: {ssl_info['ssl_type']}")

# Check for warnings
warnings = helper.get_ssl_configuration_warnings(site)
for warning in warnings:
    print(f"{warning['level']}: {warning['message']}")

# Check certificate expiration
renewal = helper.get_certificate_renewal_status(site)
if renewal:
    print(f"Expires in: {renewal['days_until_expiry']} days")
```

---

## 🧪 Test Your Setup

```bash
# Run the test suite
python test_ssl_validation.py
```

Expected output:
```
✅ All test suites completed successfully!
```

---

## 📊 Quick Reference Table

| Scenario | protocol | auto_ssl | ssl_certificate | support_subdomains | DNS Challenge |
|----------|----------|----------|-----------------|-------------------|---------------|
| HTTP | `http` | `False` | None | `False` | No |
| HTTPS Auto | `https` | `True` | None | `False` | No |
| HTTPS Auto Wildcard | `https` | `True` | None | `True` | **Yes** |
| HTTPS Manual | `https` | `False` | Required | `False` | No |
| HTTPS Manual Wildcard | `https` | `False` | Required* | `True` | No |

\* Certificate must include `*.example.com`

---

## 🎓 Learn More

- **Full Guide**: See `SSL_CONFIGURATION_GUIDE.md` for comprehensive documentation
- **Implementation Details**: See `SSL_IMPLEMENTATION_SUMMARY.md` for technical details
- **Troubleshooting**: See the troubleshooting section in the full guide

---

## 🔗 Useful Commands

```bash
# Check Django configuration
python manage.py check

# Run migrations
python manage.py migrate

# Test SSL validation
python test_ssl_validation.py

# Verify DNS record (Linux/Mac)
dig TXT _acme-challenge.example.com +short

# Check certificate details
openssl x509 -in cert.pem -text -noout

# Check certificate expiration
openssl x509 -in cert.pem -noout -dates
```

---

## 💡 Best Practices

1. **Use Auto SSL** - Let Let's Encrypt handle certificates automatically
2. **Include Certificate Chain** - Always upload the full chain when using manual certificates
3. **Monitor Expiration** - Check certificates regularly, renew before 7 days
4. **Test First** - Use staging/development environment before production
5. **DNS Propagation** - Wait for full DNS propagation (up to 60 minutes) for wildcards

---

## 🚨 Security Reminders

- ✅ Never commit private keys to version control
- ✅ Use strong passwords for encrypted keys
- ✅ Store keys securely (environment variables or secrets manager)
- ✅ Rotate certificates and keys periodically
- ✅ Monitor certificate transparency logs

---

## ✅ Checklist for Production

- [ ] Protocol correctly set (`http` or `https`)
- [ ] SSL configuration validated
- [ ] Certificates not expired (if manual)
- [ ] DNS challenge completed (if wildcard)
- [ ] Certificate chain included (if manual)
- [ ] Django migrations applied
- [ ] Test suite passing
- [ ] Monitoring configured for expiration
- [ ] Backup of certificates and keys

---

**Need Help?** Check `SSL_CONFIGURATION_GUIDE.md` for detailed troubleshooting!