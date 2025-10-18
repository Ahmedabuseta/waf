# SSL Certificate Chain Validation Guide

Complete guide for validating SSL certificate chains in the WAF system using the certificate manager utility.

---

## Table of Contents

1. [Overview](#overview)
2. [What is a Certificate Chain?](#what-is-a-certificate-chain)
3. [Why Chain Validation Matters](#why-chain-validation-matters)
4. [Prerequisites](#prerequisites)
5. [Basic Chain Validation](#basic-chain-validation)
6. [Advanced Chain Validation](#advanced-chain-validation)
7. [Common Scenarios](#common-scenarios)
8. [Troubleshooting](#troubleshooting)
9. [Integration with WAF](#integration-with-waf)

---

## Overview

The certificate manager provides comprehensive SSL certificate chain validation to ensure your certificates are properly configured and trusted by clients. The `check-chain` command validates:

- Certificate validity and expiration
- Chain completeness (end-entity → intermediate → root)
- Certificate relationships (proper signing)
- Trust path to known Certificate Authorities

---

## What is a Certificate Chain?

An SSL certificate chain is a hierarchical sequence of certificates:

```
┌─────────────────────────┐
│   End-Entity Cert       │  ← Your website certificate
│   (example.com)         │
└───────────┬─────────────┘
            │ signed by
┌───────────▼─────────────┐
│   Intermediate CA Cert  │  ← Intermediate Certificate Authority
│   (Let's Encrypt, etc)  │
└───────────┬─────────────┘
            │ signed by
┌───────────▼─────────────┐
│   Root CA Cert          │  ← Root Certificate Authority
│   (Trusted by browsers) │
└─────────────────────────┘
```

**Components:**
- **End-Entity Certificate**: Your domain certificate
- **Intermediate Certificate(s)**: Bridge between your cert and root CA
- **Root Certificate**: Trusted by operating systems and browsers

---

## Why Chain Validation Matters

### Security
- Ensures certificates are properly signed
- Verifies trust path to known CAs
- Detects forged or tampered certificates

### Client Compatibility
- Incomplete chains cause browser errors
- Missing intermediates = untrusted connections
- Proper chains ensure wide compatibility

### Compliance
- PCI DSS and other standards require valid chains
- Auditing and logging requirements
- Proof of proper SSL/TLS configuration

---

## Prerequisites

### System Requirements
- OpenSSL installed and available in PATH
- Python 3.8+ with dependencies installed
- Certificate files accessible on filesystem

### File Formats
Certificates must be in PEM format:
```
-----BEGIN CERTIFICATE-----
MIIDXTCCAkWgAwIBAgIJAKZ...
...certificate data...
-----END CERTIFICATE-----
```

### Check OpenSSL Availability
```bash
openssl version
# Expected: OpenSSL 1.1.1 or higher
```

---

## Basic Chain Validation

### 1. Validate Certificate Only

Check if a certificate is valid without chain:

```bash
python site_mangement/utils/certificate_manager.py check-chain /path/to/cert.pem
```

**Output:**
```
🔗 Checking SSL certificate chain: /path/to/cert.pem
✅ Certificate chain is valid

🔗 Certificate Chain Analysis:
   Chain Length: 1
   Self-Signed: No
   Has Intermediate: No
   Certificates:
     1. END_ENTITY: CN=example.com
        Issuer: CN=Let's Encrypt Authority X3

📋 Verification Output:
   /path/to/cert.pem: OK
```

### 2. Validate with Intermediate Chain

Check certificate with intermediate CA certificate:

```bash
python site_mangement/utils/certificate_manager.py check-chain \
  /path/to/cert.pem \
  --chain /path/to/chain.pem
```

**Output:**
```
🔗 Checking SSL certificate chain: /path/to/cert.pem
✅ Certificate chain is valid

🔗 Certificate Chain Analysis:
   Chain Length: 3
   Self-Signed: No
   Has Intermediate: Yes
   Certificates:
     1. END_ENTITY: CN=example.com
        Issuer: CN=Let's Encrypt Authority X3
     2. INTERMEDIATE: CN=Let's Encrypt Authority X3
        Issuer: CN=DST Root CA X3
     3. ROOT: CN=DST Root CA X3
        Issuer: CN=DST Root CA X3

📋 Verification Output:
   /path/to/cert.pem: OK
```

---

## Advanced Chain Validation

### 3. Validate Against Custom CA Bundle

Verify certificate against specific trusted CAs:

```bash
python site_mangement/utils/certificate_manager.py check-chain \
  /path/to/cert.pem \
  --chain /path/to/chain.pem \
  --ca-bundle /etc/ssl/certs/ca-bundle.crt
```

**Use Cases:**
- Corporate/internal CAs
- Custom trust stores
- Offline validation
- Security auditing

### 4. Validate Self-Signed Certificates

For development or internal use:

```bash
python site_mangement/utils/certificate_manager.py check-chain \
  /path/to/self-signed.pem
```

**Output:**
```
🔗 Certificate Chain Analysis:
   Chain Length: 1
   Self-Signed: Yes
   Has Intermediate: No
```

---

## Common Scenarios

### Scenario 1: Let's Encrypt Certificate

**Files:**
- `fullchain.pem` - Certificate + chain combined
- `cert.pem` - Certificate only
- `chain.pem` - Intermediate certificates

**Validation:**
```bash
# Option A: Validate fullchain (includes intermediates)
python site_mangement/utils/certificate_manager.py check-chain fullchain.pem

# Option B: Validate cert with separate chain
python site_mangement/utils/certificate_manager.py check-chain cert.pem --chain chain.pem
```

### Scenario 2: Commercial CA (DigiCert, GlobalSign, etc.)

**Files from CA:**
- `example_com.crt` - Your certificate
- `intermediate.crt` - CA intermediate
- `root.crt` - CA root (optional)

**Validation:**
```bash
python site_mangement/utils/certificate_manager.py check-chain \
  example_com.crt \
  --chain intermediate.crt
```

### Scenario 3: Wildcard Certificate

**Certificate covers:**
- `example.com`
- `*.example.com` (all subdomains)

**Validation:**
```bash
# Validate chain
python site_mangement/utils/certificate_manager.py check-chain wildcard.pem --chain chain.pem

# Check domain coverage
python site_mangement/utils/certificate_manager.py domain api.example.com wildcard.pem
python site_mangement/utils/certificate_manager.py domain www.example.com wildcard.pem
```

### Scenario 4: Multi-Domain (SAN) Certificate

**Certificate covers multiple domains:**
- `example.com`
- `www.example.com`
- `api.example.com`

**Validation:**
```bash
# Validate chain
python site_mangement/utils/certificate_manager.py check-chain san-cert.pem --chain chain.pem

# Verify each domain is covered
python site_mangement/utils/certificate_manager.py domain example.com san-cert.pem
python site_mangement/utils/certificate_manager.py domain www.example.com san-cert.pem
python site_mangement/utils/certificate_manager.py domain api.example.com san-cert.pem
```

### Scenario 5: Certificate Renewal Validation

**Before deploying renewed certificate:**

```bash
# 1. Check new certificate chain
python site_mangement/utils/certificate_manager.py check-chain new-cert.pem --chain new-chain.pem

# 2. Verify domain coverage
python site_mangement/utils/certificate_manager.py domain example.com new-cert.pem

# 3. Validate key match
python site_mangement/utils/certificate_manager.py validate new-cert.pem private-key.pem

# 4. Compare with old certificate
python site_mangement/utils/certificate_manager.py check old-cert.pem --detailed
python site_mangement/utils/certificate_manager.py check new-cert.pem --detailed
```

---

## Troubleshooting

### Error: "Certificate chain validation failed"

**Possible Causes:**
1. Incomplete chain (missing intermediate)
2. Wrong order of certificates
3. Expired certificate
4. Untrusted CA

**Solutions:**

```bash
# 1. Check certificate details
python site_mangement/utils/certificate_manager.py check cert.pem --detailed

# 2. Verify chain file contains intermediates
openssl crl2pkcs7 -nocrl -certfile chain.pem | \
  openssl pkcs7 -print_certs -text -noout

# 3. Download missing intermediates from CA
wget https://letsencrypt.org/certs/lets-encrypt-x3-cross-signed.pem -O chain.pem

# 4. Combine certificate and chain
cat cert.pem chain.pem > fullchain.pem
```

### Error: "Unable to get local issuer certificate"

**Cause:** System CA bundle missing or outdated

**Solutions:**

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install ca-certificates
sudo update-ca-certificates

# CentOS/RHEL
sudo yum install ca-certificates
sudo update-ca-trust

# Specify custom CA bundle
python site_mangement/utils/certificate_manager.py check-chain \
  cert.pem \
  --ca-bundle /etc/ssl/certs/ca-bundle.crt
```

### Error: "Certificate has expired"

**Check expiration:**

```bash
python site_mangement/utils/certificate_manager.py check cert.pem
```

**Output shows:**
```
Status: ❌ EXPIRED
Days since expiry: 15
```

**Solution:** Renew certificate immediately

### Error: "Self-signed certificate in chain"

**For Production:** Not acceptable - get proper CA-signed certificate

**For Development/Testing:** Expected behavior

**To bypass (DEV ONLY):**
```bash
# Add self-signed CA to custom bundle
cat self-signed-ca.pem >> custom-ca-bundle.pem
python site_mangement/utils/certificate_manager.py check-chain \
  cert.pem \
  --ca-bundle custom-ca-bundle.pem
```

### Warning: "Certificate expiring in X days"

**Scan all certificates:**
```bash
python site_mangement/utils/certificate_manager.py scan --days-warning 30
```

**Output:**
```
⚠️  Expiring Soon:
   - /etc/caddy/certs/example.com/cert.pem: example.com (23 days)
   - /etc/caddy/certs/api.example.com/cert.pem: api.example.com (15 days)
```

**Action:** Schedule renewal before expiration

---

## Integration with WAF

### 1. Install Certificate with Chain Validation

```bash
# Validate before installing
python site_mangement/utils/certificate_manager.py check-chain \
  cert.pem \
  --chain chain.pem

# Install to WAF certificate directory
python site_mangement/utils/certificate_manager.py install \
  example.com \
  cert.pem \
  key.pem \
  --chain chain.pem
```

**Result:**
- Installs to: `/etc/caddy/certs/example.com/`
- Files: `cert.pem`, `key.pem`, `chain.pem`

### 2. Automated Validation in Django Views

```python
from site_mangement.utils.certificate_manager import CertificateManager

def upload_certificate_view(request, site_slug):
    site = get_object_or_404(Site, slug=site_slug)
    
    if request.method == 'POST':
        cert_file = request.FILES.get('certificate')
        key_file = request.FILES.get('private_key')
        chain_file = request.FILES.get('chain')
        
        # Save files temporarily
        cert_path = save_upload(cert_file)
        key_path = save_upload(key_file)
        chain_path = save_upload(chain_file) if chain_file else None
        
        # Validate chain
        cert_manager = CertificateManager()
        
        # Check chain validity
        if not cert_manager.check_chain(cert_path, chain_path):
            messages.error(request, 'Certificate chain validation failed')
            return redirect('ssl_upload', site_slug=site.slug)
        
        # Validate key match
        if not cert_manager.validate_certificate_chain(cert_path, key_path):
            messages.error(request, 'Certificate and key do not match')
            return redirect('ssl_upload', site_slug=site.slug)
        
        # Install certificate
        if cert_manager.install_certificate(
            site.host, cert_path, key_path, chain_path
        ):
            messages.success(request, 'Certificate installed successfully')
            # Sync with Caddy
            sync_site_to_caddy(site)
        
        return redirect('site_detail', slug=site.slug)
```

### 3. Periodic Chain Health Checks

**Cron job for monitoring:**

```bash
#!/bin/bash
# /etc/cron.daily/check-ssl-chains

MANAGER="/path/to/certificate_manager.py"
EMAIL="admin@example.com"

# Scan all certificates
RESULT=$(python $MANAGER scan --days-warning 30)

# Check for issues
if echo "$RESULT" | grep -q "❌\|⚠️"; then
    echo "$RESULT" | mail -s "SSL Certificate Alert" $EMAIL
fi
```

### 4. Pre-Deployment Validation Script

```bash
#!/bin/bash
# validate-ssl-deployment.sh

set -e

CERT_FILE=$1
KEY_FILE=$2
CHAIN_FILE=$3
DOMAIN=$4

echo "=== SSL Deployment Validation ==="

# 1. Validate certificate chain
echo "Checking certificate chain..."
python certificate_manager.py check-chain "$CERT_FILE" --chain "$CHAIN_FILE"

# 2. Validate key match
echo "Validating certificate-key match..."
python certificate_manager.py validate "$CERT_FILE" "$KEY_FILE"

# 3. Check domain coverage
echo "Checking domain coverage for $DOMAIN..."
python certificate_manager.py domain "$DOMAIN" "$CERT_FILE"

# 4. Check remote certificate (if already deployed)
echo "Checking currently deployed certificate..."
python certificate_manager.py remote "$DOMAIN" || true

echo "=== Validation Complete ==="
echo "✅ Certificate is ready for deployment"
```

**Usage:**
```bash
./validate-ssl-deployment.sh \
  /path/to/cert.pem \
  /path/to/key.pem \
  /path/to/chain.pem \
  example.com
```

---

## Best Practices

### 1. Always Include Intermediate Certificates

❌ **Don't:**
```bash
# Only end-entity certificate
python certificate_manager.py check-chain cert.pem
```

✅ **Do:**
```bash
# Certificate + chain
python certificate_manager.py check-chain cert.pem --chain chain.pem
```

### 2. Validate Before Deployment

**Pre-deployment checklist:**
- [ ] Certificate chain valid
- [ ] Certificate-key match confirmed
- [ ] Domain coverage verified
- [ ] Not expired or expiring soon
- [ ] Proper file permissions set

### 3. Monitor Certificate Health

**Set up automated monitoring:**
```bash
# Daily scan with 30-day warning
0 0 * * * /path/to/certificate_manager.py scan --days-warning 30 | mail -s "SSL Report" admin@example.com
```

### 4. Keep CA Bundle Updated

```bash
# Ubuntu/Debian
sudo apt-get update && sudo apt-get upgrade ca-certificates

# CentOS/RHEL
sudo yum update ca-certificates
```

### 5. Document Certificate Sources

**Maintain a certificate inventory:**
```
example.com:
  - CA: Let's Encrypt
  - Type: RSA 2048
  - Expiry: 2024-03-15
  - Renewal: Auto (acme.sh)
  - Chain: 3 certificates
  - Intermediates: Let's Encrypt R3
```

---

## Quick Reference

### Common Commands

```bash
# Basic chain check
python certificate_manager.py check-chain cert.pem

# With intermediate chain
python certificate_manager.py check-chain cert.pem --chain chain.pem

# With custom CA bundle
python certificate_manager.py check-chain cert.pem --chain chain.pem --ca-bundle ca.crt

# Scan all certificates
python certificate_manager.py scan --days-warning 30

# Check remote certificate
python certificate_manager.py remote example.com

# Validate cert + key + chain
python certificate_manager.py validate cert.pem key.pem
python certificate_manager.py check-chain cert.pem --chain chain.pem
```

### Exit Codes

- `0` - Success (chain valid)
- `1` - Failure (chain invalid or error)

### Log Locations

- Certificate operations: Logged via `caddy_logger`
- System logs: Check `/var/log/caddy/` or application logs
- OpenSSL errors: Shown in command output

---

## Additional Resources

- [OpenSSL Certificate Commands](https://www.openssl.org/docs/man1.1.1/man1/openssl-x509.html)
- [Let's Encrypt Chain of Trust](https://letsencrypt.org/certificates/)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)
- [SSL Labs Server Test](https://www.ssllabs.com/ssltest/)

---

## Support

For issues or questions:
1. Check certificate with `--detailed` flag
2. Review OpenSSL error messages
3. Verify file permissions and paths
4. Check system CA bundle is up-to-date
5. Consult logs for detailed error information

---

**Last Updated:** 2024
**Version:** 1.0