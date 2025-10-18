# SSL/TLS Configuration Guide for Base-WAF

## Overview

This guide explains how to configure SSL/TLS certificates for your sites in the Base-WAF system. The system provides comprehensive SSL validation, automatic certificate management, and wildcard certificate support.

## Table of Contents

1. [SSL Configuration Options](#ssl-configuration-options)
2. [Protocol Selection: HTTP vs HTTPS](#protocol-selection-http-vs-https)
3. [Automatic SSL with Let's Encrypt](#automatic-ssl-with-lets-encrypt)
4. [Manual Certificate Upload](#manual-certificate-upload)
5. [Wildcard Certificates and Subdomain Support](#wildcard-certificates-and-subdomain-support)
6. [DNS Challenge for Wildcard Certificates](#dns-challenge-for-wildcard-certificates)
7. [Certificate Validation Rules](#certificate-validation-rules)
8. [Troubleshooting](#troubleshooting)
9. [API Examples](#api-examples)

---

## SSL Configuration Options

The Base-WAF system supports three SSL configuration modes:

1. **HTTP Only** - No SSL/TLS encryption
2. **HTTPS with Auto SSL** - Automatic certificate management via Let's Encrypt
3. **HTTPS with Manual Certificates** - Upload your own certificates

---

## Protocol Selection: HTTP vs HTTPS

### HTTP Configuration

When using HTTP protocol:
- ✅ No SSL configuration required
- ❌ Cannot enable `auto_ssl`
- ❌ Cannot upload SSL certificates
- ❌ Cannot enable `support_subdomains`

**Example:**
```python
site = Site.objects.create(
    host='example.com',
    protocol='http',
    auto_ssl=False,  # Must be False
    support_subdomains=False,
    status='active'
)
```

### HTTPS Configuration

When using HTTPS protocol:
- ✅ Must have either `auto_ssl=True` OR upload certificates
- ✅ Supports subdomain wildcard certificates
- ✅ Automatic certificate validation

**Example with Auto SSL:**
```python
site = Site.objects.create(
    host='example.com',
    protocol='https',
    auto_ssl=True,
    support_subdomains=False,
    status='active'
)
```

---

## Automatic SSL with Let's Encrypt

### Single Domain (example.com)

For a single domain without wildcard support:

```python
from site_mangement.models import Site

site = Site.objects.create(
    host='example.com',
    protocol='https',
    auto_ssl=True,
    support_subdomains=False,  # No wildcard needed
    status='active'
)
```

**Features:**
- ✅ Automatic certificate issuance
- ✅ Automatic renewal (90-day certificates)
- ✅ Uses HTTP-01 challenge (no DNS required)
- ✅ Zero configuration needed

### Wildcard Domain (*.example.com)

For wildcard certificate covering all subdomains:

```python
from site_mangement.models import Site

site = Site.objects.create(
    host='example.com',
    protocol='https',
    auto_ssl=True,
    support_subdomains=True,  # Enable wildcard
    status='active'
)

# Check if DNS challenge is required
if site.requires_dns_challenge():
    print("DNS-01 challenge required for wildcard certificate")
```

**Important:**
- ⚠️ Requires DNS-01 challenge (see section below)
- ⚠️ Requires DNS configuration access
- ⚠️ DNS propagation can take 5-60 minutes

---

## Manual Certificate Upload

### Standard Certificate (Single Domain)

Upload your own certificate for a single domain:

```python
from django.core.files import File
from site_mangement.models import Site

# Open certificate files
with open('cert.pem', 'rb') as cert_file, \
     open('key.pem', 'rb') as key_file, \
     open('chain.pem', 'rb') as chain_file:
    
    site = Site.objects.create(
        host='example.com',
        protocol='https',
        auto_ssl=False,
        support_subdomains=False,
        ssl_certificate=File(cert_file),
        ssl_key=File(key_file),
        ssl_chain=File(chain_file),  # Optional but recommended
        status='active'
    )
```

### Wildcard Certificate (Multiple Subdomains)

Upload a wildcard certificate:

```python
# Certificate MUST include *.example.com in SAN
with open('wildcard-cert.pem', 'rb') as cert_file, \
     open('wildcard-key.pem', 'rb') as key_file:
    
    site = Site.objects.create(
        host='example.com',
        protocol='https',
        auto_ssl=False,
        support_subdomains=True,  # Requires wildcard cert
        ssl_certificate=File(cert_file),
        ssl_key=File(key_file),
        status='active'
    )
```

**Validation Checks:**
- ✅ Certificate format (PEM)
- ✅ Certificate expiration (warns if < 7 days)
- ✅ Private key format and strength (min 2048 bits)
- ✅ Certificate and key match
- ✅ Domain coverage (cert must cover the hostname)
- ✅ Wildcard coverage (if `support_subdomains=True`)
- ✅ Certificate chain validity

---

## Wildcard Certificates and Subdomain Support

### What is Subdomain Support?

When `support_subdomains=True`, the site will accept requests for:
- `example.com`
- `www.example.com`
- `api.example.com`
- `*.example.com` (any subdomain)

### Certificate Requirements

**For Manual Certificates:**
The certificate MUST include `*.example.com` in the Subject Alternative Names (SAN).

**For Auto SSL:**
A wildcard certificate will be automatically requested via Let's Encrypt.

### Checking Certificate Coverage

```python
from site_mangement.utils import CertificateChecker

checker = CertificateChecker()

# Check what domains a certificate covers
cert_info = checker.check_certificate_domains('path/to/cert.pem')
print(f"Domains covered: {cert_info['all_domains']}")
print(f"Has wildcard: {cert_info['has_wildcard']}")
print(f"Wildcard domains: {cert_info['wildcard_domains']}")

# Check if specific domain is covered
coverage = checker.check_domain_coverage('api.example.com', 'path/to/cert.pem')
print(f"Domain covered: {coverage['matches']}")
```

---

## DNS Challenge for Wildcard Certificates

### Why DNS Challenge?

Let's Encrypt requires DNS-01 challenge for wildcard certificates. This proves you control the domain by creating a TXT record in your DNS.

### Getting DNS Challenge Instructions

```python
from site_mangement.utils import ACMEDNSManager

dns_manager = ACMEDNSManager()

# Get instructions for your domain
instructions = dns_manager.generate_challenge_instructions(
    domain='example.com',
    support_subdomains=True
)

print(instructions['challenge_record'])  # _acme-challenge.example.com
print(instructions['instructions'])      # Step-by-step guide
```

### DNS Record Configuration

You need to create a TXT record in your DNS provider:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| TXT | `_acme-challenge.example.com` | `<ACME_CHALLENGE_VALUE>` | 300 |

**Common DNS Providers:**

#### Cloudflare
1. Log in to Cloudflare dashboard
2. Select your domain
3. Go to DNS > Records
4. Add TXT record: `_acme-challenge` with challenge value
5. Set TTL to 300 seconds (Auto is fine)

#### AWS Route53
1. Open Route53 console
2. Select hosted zone
3. Create record set:
   - Name: `_acme-challenge.example.com`
   - Type: TXT
   - Value: `"<CHALLENGE_VALUE>"`
   - TTL: 300

#### GoDaddy
1. Log in to GoDaddy
2. Domain settings > DNS Management
3. Add TXT record
4. Host: `_acme-challenge`
5. TXT Value: `<CHALLENGE_VALUE>`
6. TTL: 1 Hour

### Verifying DNS Propagation

```python
from site_mangement.utils import ACMEDNSManager

dns_manager = ACMEDNSManager()

# Verify DNS record exists
verification = dns_manager.verify_dns_challenge_record(
    domain='example.com',
    expected_value='<CHALLENGE_VALUE>'
)

if verification['exists'] and verification['matched']:
    print("✅ DNS record verified and ready!")
else:
    print(f"⚠️ Status: {verification['status']}")
    print(f"Message: {verification['message']}")

# Check propagation across multiple DNS servers
propagation = dns_manager.check_dns_propagation(
    domain='example.com',
    expected_value='<CHALLENGE_VALUE>'
)

print(f"Propagation: {propagation['propagation_percentage']}%")
print(f"Servers verified: {propagation['propagated_servers']}/{propagation['total_servers_checked']}")

if propagation['fully_propagated']:
    print("✅ DNS fully propagated!")
```

### Command-Line Verification

```bash
# Check if DNS record exists (Linux/Mac)
dig TXT _acme-challenge.example.com +short

# Or use nslookup (Windows/Linux/Mac)
nslookup -type=TXT _acme-challenge.example.com

# Expected output:
# "_acme-challenge.example.com. 300 IN TXT "<CHALLENGE_VALUE>""
```

---

## Certificate Validation Rules

### Rule 1: Protocol Consistency

| Protocol | auto_ssl | ssl_certificate | Valid? |
|----------|----------|-----------------|--------|
| HTTP | False | None | ✅ |
| HTTP | True | None | ❌ |
| HTTP | False | Uploaded | ❌ |
| HTTPS | True | None | ✅ |
| HTTPS | False | Uploaded | ✅ |
| HTTPS | False | None | ❌ |

### Rule 2: Certificate Requirements

When uploading manual certificates:
- ✅ Certificate file is **required**
- ✅ Private key file is **required**
- ⚠️ Certificate chain is **recommended** but optional
- ✅ Certificate must be in PEM format
- ✅ Private key must be in PEM format
- ✅ Certificate and key must match
- ✅ Certificate must not be expired
- ⚠️ Certificate expiring in < 7 days triggers warning

### Rule 3: Domain Coverage

- ✅ Certificate must cover the site's hostname
- ✅ If `support_subdomains=True`, certificate must include wildcard
- ✅ Wildcard format: `*.example.com`
- ⚠️ Wildcard certificates require DNS-01 challenge with auto_ssl

### Rule 4: Key Strength

- ✅ Minimum key size: 2048 bits
- ✅ Recommended: 2048-4096 bits RSA
- ⚠️ 1024 bits or less is rejected

---

## Troubleshooting

### Error: "HTTP protocol cannot have auto_ssl enabled"

**Solution:** Change protocol to HTTPS or disable auto_ssl:
```python
site.protocol = 'https'
site.save()
```

### Error: "HTTPS requires either auto_ssl=True or SSL certificate"

**Solution:** Either enable auto_ssl or upload certificates:
```python
# Option 1: Enable auto SSL
site.auto_ssl = True
site.save()

# Option 2: Upload certificates
site.auto_ssl = False
site.ssl_certificate = cert_file
site.ssl_key = key_file
site.save()
```

### Error: "Certificate and private key do not match"

**Solution:** Ensure you're uploading the correct certificate-key pair:
```bash
# Verify certificate and key match
openssl x509 -noout -modulus -in cert.pem | openssl md5
openssl rsa -noout -modulus -in key.pem | openssl md5
# Both outputs should be identical
```

### Error: "Certificate does not cover domain"

**Solution:** Check certificate SANs:
```bash
openssl x509 -noout -text -in cert.pem | grep -A1 "Subject Alternative Name"
```

Ensure the certificate includes your domain or `*.yourdomain.com`.

### Error: "Subdomain support enabled but certificate doesn't include wildcard"

**Solution:** 
1. Get a wildcard certificate that includes `*.example.com`
2. Or disable subdomain support:
```python
site.support_subdomains = False
site.save()
```

### DNS Challenge Not Working

**Checklist:**
1. ✅ Verify TXT record exists: `dig TXT _acme-challenge.example.com +short`
2. ✅ Check TTL - lower values propagate faster (300 seconds recommended)
3. ✅ Wait for DNS propagation (5-60 minutes)
4. ✅ Verify with multiple DNS servers
5. ✅ Check DNS provider documentation
6. ✅ Ensure no typos in record name or value

---

## API Examples

### Using Forms with SSL Validation

```python
from site_mangement.forms import SiteForm
from django.core.files.uploadedfile import SimpleUploadedFile

# Create form with data
form = SiteForm(data={
    'host': 'example.com',
    'protocol': 'https',
    'auto_ssl': False,
    'support_subdomains': True,
    'status': 'active',
    'action_type': 'log',
    'sensitivity_level': 'medium'
})

# Add certificate files
with open('wildcard-cert.pem', 'rb') as cert, \
     open('wildcard-key.pem', 'rb') as key:
    
    form.files['ssl_certificate'] = SimpleUploadedFile('cert.pem', cert.read())
    form.files['ssl_key'] = SimpleUploadedFile('key.pem', key.read())

# Validate
if form.is_valid():
    site = form.save()
    
    # Check if DNS challenge is needed
    dns_info = form.get_dns_challenge_info()
    if dns_info and dns_info['required']:
        print("DNS Challenge Required:")
        print(dns_info['instructions'])
else:
    print("Validation errors:", form.errors)
```

### Using Validators Directly

```python
from site_mangement.validators import SiteSSLValidator

validator = SiteSSLValidator()

# Validate complete configuration
is_valid, errors = validator.validate_site_ssl_configuration(
    protocol='https',
    auto_ssl=False,
    support_subdomains=True,
    host='example.com',
    ssl_certificate=cert_file,
    ssl_key=key_file,
    ssl_chain=chain_file
)

if not is_valid:
    for error in errors:
        print(f"❌ {error}")
else:
    print("✅ SSL configuration valid!")
```

### Using SSL Helper in Views

```python
from site_mangement.ssl_helpers import SSLHelper
from site_mangement.models import Site

helper = SSLHelper()

# Get comprehensive SSL info
site = Site.objects.get(host='example.com')
ssl_info = helper.get_site_ssl_info(site)

print(f"SSL Enabled: {ssl_info['ssl_enabled']}")
print(f"SSL Type: {ssl_info['ssl_type']}")
print(f"Requires DNS Challenge: {ssl_info['requires_dns_challenge']}")

if ssl_info['requires_dns_challenge']:
    dns_challenge = ssl_info['dns_challenge']
    print(f"Challenge Record: {dns_challenge['challenge_record']}")

# Check for warnings
warnings = helper.get_ssl_configuration_warnings(site)
for warning in warnings:
    print(f"{warning['level'].upper()}: {warning['message']}")

# Check renewal status
renewal_status = helper.get_certificate_renewal_status(site)
if renewal_status:
    print(f"Certificate expires in {renewal_status['days_until_expiry']} days")
    print(f"Renewal action: {renewal_status['action_required']}")
    print(f"Recommendation: {renewal_status['recommendation']}")
```

### Validating Uploaded Certificates

```python
from site_mangement.ssl_helpers import SSLHelper

helper = SSLHelper()

# Validate uploaded files
is_valid, errors, cert_info = helper.validate_uploaded_certificate(
    cert_file=request.FILES['certificate'],
    key_file=request.FILES['private_key'],
    chain_file=request.FILES.get('chain'),
    host='example.com',
    support_subdomains=True
)

if is_valid:
    print("✅ Certificate validated successfully!")
    print(f"Common Name: {cert_info['common_name']}")
    print(f"Valid Until: {cert_info['valid_until']}")
    print(f"Domains: {', '.join(cert_info['all_domains'])}")
    print(f"Has Wildcard: {cert_info['has_wildcard']}")
else:
    print("❌ Certificate validation failed:")
    for error in errors:
        print(f"  - {error}")
```

---

## Best Practices

### 1. Use Auto SSL When Possible
- ✅ Automatic renewal
- ✅ No manual certificate management
- ✅ Always up-to-date certificates

### 2. Certificate Chain
- ✅ Always include certificate chain when uploading
- ✅ Improves browser compatibility
- ✅ Prevents trust warnings

### 3. Monitor Expiration
- ✅ Check certificate expiration regularly
- ✅ Renew at least 7 days before expiration
- ✅ Set up alerts for expiring certificates

### 4. Key Security
- ✅ Never commit private keys to version control
- ✅ Use strong passwords for encrypted keys
- ✅ Rotate keys periodically
- ✅ Store keys securely (use environment variables or secrets manager)

### 5. DNS Challenge
- ✅ Lower TTL before challenge (300 seconds)
- ✅ Use DNS provider with API support for automation
- ✅ Verify propagation before requesting certificate
- ✅ Remove TXT record after successful validation

### 6. Testing
- ✅ Test certificates in staging environment first
- ✅ Verify certificate coverage with tools
- ✅ Check certificate chain completeness
- ✅ Test from multiple locations

---

## Quick Reference

### File Formats

```bash
# Certificate (PEM format)
-----BEGIN CERTIFICATE-----
MIIDXTCCAkWgAwIBAgIJAKJ...
-----END CERTIFICATE-----

# Private Key (PEM format)
-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0B...
-----END PRIVATE KEY-----

# Certificate Chain (PEM format)
-----BEGIN CERTIFICATE-----
(Intermediate Certificate 1)
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
(Intermediate Certificate 2)
-----END CERTIFICATE-----
```

### Conversion Commands

```bash
# Convert DER to PEM
openssl x509 -inform der -in cert.der -out cert.pem

# Convert PFX/P12 to PEM
openssl pkcs12 -in cert.pfx -out cert.pem -nodes

# Extract certificate from PFX
openssl pkcs12 -in cert.pfx -clcerts -nokeys -out cert.pem

# Extract private key from PFX
openssl pkcs12 -in cert.pfx -nocerts -nodes -out key.pem

# View certificate details
openssl x509 -in cert.pem -text -noout

# Check certificate expiration
openssl x509 -in cert.pem -noout -enddate

# Verify certificate and key match
openssl x509 -noout -modulus -in cert.pem | openssl md5
openssl rsa -noout -modulus -in key.pem | openssl md5
```

---

## Support

For issues or questions:
1. Check this guide first
2. Review error messages carefully
3. Use validation tools to diagnose issues
4. Check DNS propagation for wildcard certificates
5. Consult the troubleshooting section

**Common Tools:**
- SSL Labs Test: https://www.ssllabs.com/ssltest/
- DNS Checker: https://dnschecker.org/
- Certificate Decoder: https://certlogik.com/decoder/
- OpenSSL Documentation: https://www.openssl.org/docs/

---

## Version History

- **v1.0** - Initial SSL validation system with auto SSL and manual certificate support
- **v1.1** - Added wildcard certificate support and DNS-01 challenge
- **v1.2** - Enhanced validation and comprehensive error messages