# SSL Certificate Chain Validation - Quick Start

## Overview

This feature adds comprehensive SSL certificate chain validation to the WAF system. It ensures certificates are properly configured with complete trust chains before deployment.

---

## ✨ What's New

### New Command: `check-chain`

Validates SSL certificate chains and analyzes their structure:

```bash
python manage_certificates.py check-chain cert.pem --chain chain.pem
```

**What it validates:**
- ✅ Certificate validity and expiration
- ✅ Complete chain (end-entity → intermediate → root)
- ✅ Proper signing relationships
- ✅ Trust path to known CAs
- ✅ Self-signed detection
- ✅ Chain structure analysis

---

## 🚀 Quick Start

### 1. Basic Usage

**Validate a certificate with its chain:**
```bash
python manage_certificates.py check-chain /path/to/cert.pem --chain /path/to/chain.pem
```

**Output:**
```
🔗 Checking SSL certificate chain: cert.pem
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
```

### 2. Common Scenarios

**Let's Encrypt:**
```bash
# Fullchain includes everything
python manage_certificates.py check-chain fullchain.pem

# Or separate files
python manage_certificates.py check-chain cert.pem --chain chain.pem
```

**Commercial CA (DigiCert, GlobalSign, etc.):**
```bash
python manage_certificates.py check-chain example_com.crt --chain intermediate.crt
```

**Wildcard Certificate:**
```bash
python manage_certificates.py check-chain wildcard.pem --chain chain.pem
```

**Corporate/Internal CA:**
```bash
python manage_certificates.py check-chain cert.pem --chain chain.pem --ca-bundle internal-ca.crt
```

### 3. Complete Pre-Deployment Validation

Use the provided script for comprehensive validation:

```bash
./examples/validate_ssl_chain.sh cert.pem key.pem chain.pem example.com
```

**This script checks:**
- ✅ Certificate chain validity
- ✅ Certificate-key match
- ✅ Domain coverage
- ✅ Expiration dates
- ✅ Key size and strength
- ✅ Signature algorithms
- ✅ File permissions
- ✅ Remote certificate comparison

---

## 📖 Command Options

```bash
# Basic chain check
python manage_certificates.py check-chain <cert.pem>

# With intermediate chain
python manage_certificates.py check-chain <cert.pem> --chain <chain.pem>

# With custom CA bundle (for corporate CAs)
python manage_certificates.py check-chain <cert.pem> --chain <chain.pem> --ca-bundle <ca-bundle.crt>
```

**Exit codes:**
- `0` - Success (chain is valid)
- `1` - Failure (chain is invalid or error occurred)

---

## 🔧 Integration Examples

### Django View

```python
from site_mangement.utils.certificate_manager import CertificateManager

def upload_ssl_certificate(request, site_slug):
    cert_manager = CertificateManager()
    
    # Validate chain before installing
    if not cert_manager.check_chain(cert_path, chain_path):
        messages.error(request, 'Invalid certificate chain')
        return redirect('ssl_upload')
    
    # Install certificate
    if cert_manager.install_certificate(domain, cert_path, key_path, chain_path):
        messages.success(request, 'Certificate installed successfully')
        # Sync with Caddy
        sync_site_to_caddy(site)
```

### Bash Script

```bash
#!/bin/bash
# Pre-deployment validation

python manage_certificates.py check-chain cert.pem --chain chain.pem
if [ $? -ne 0 ]; then
    echo "❌ Certificate chain validation failed"
    exit 1
fi

echo "✅ Certificate is ready for deployment"
```

### CI/CD Pipeline

```yaml
# .gitlab-ci.yml
validate-certificates:
  script:
    - python manage_certificates.py check-chain $CERT_FILE --chain $CHAIN_FILE
    - python manage_certificates.py validate $CERT_FILE $KEY_FILE
    - python manage_certificates.py domain $DOMAIN $CERT_FILE
```

### Cron Job (Monitoring)

```bash
# Daily certificate health check
0 0 * * * python manage_certificates.py scan --days-warning 30 | \
  grep -q "❌\|⚠️" && mail -s "SSL Alert" admin@example.com
```

---

## 🎯 Use Cases

### 1. Pre-Deployment Validation
Catch SSL configuration errors before going live:
```bash
python manage_certificates.py check-chain new-cert.pem --chain new-chain.pem
```

### 2. Certificate Renewal
Verify renewed certificates are valid:
```bash
# Check new certificate
python manage_certificates.py check-chain renewed-cert.pem --chain chain.pem

# Compare with old certificate
python manage_certificates.py check old-cert.pem --detailed
python manage_certificates.py check renewed-cert.pem --detailed
```

### 3. Troubleshooting
Diagnose SSL connection issues:
```bash
# Check local certificate
python manage_certificates.py check-chain cert.pem --chain chain.pem

# Check remote certificate
python manage_certificates.py remote example.com
```

### 4. Compliance Auditing
Document and verify certificate configurations:
```bash
# Scan all certificates
python manage_certificates.py scan --show-expired --days-warning 30

# Validate specific certificate setup
python manage_certificates.py check-chain cert.pem --chain chain.pem --detailed
```

---

## 🛠️ Troubleshooting

### Error: "Certificate chain validation failed"

**Possible causes:**
- Missing intermediate certificates
- Expired certificate
- Wrong chain order
- Untrusted CA

**Solution:**
```bash
# Check certificate details
python manage_certificates.py check cert.pem --detailed

# Ensure chain file contains intermediates
openssl crl2pkcs7 -nocrl -certfile chain.pem | openssl pkcs7 -print_certs -text -noout

# Combine certificate and chain if needed
cat cert.pem chain.pem > fullchain.pem
```

### Error: "Unable to get local issuer certificate"

**Cause:** System CA bundle missing or outdated

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get install ca-certificates
sudo update-ca-certificates

# CentOS/RHEL
sudo yum install ca-certificates
sudo update-ca-trust

# Or specify custom CA bundle
python manage_certificates.py check-chain cert.pem --ca-bundle /etc/ssl/certs/ca-bundle.crt
```

### Warning: "Certificate expiring soon"

**Solution:**
```bash
# Scan for expiring certificates
python manage_certificates.py scan --days-warning 30

# Renew certificate before expiration
```

---

## 📚 Documentation

**Comprehensive guides:**
- 📖 **Full Guide:** `docs/SSL_CHAIN_VALIDATION_GUIDE.md` (600+ lines)
  - Detailed explanations
  - Step-by-step examples
  - Troubleshooting section
  - Integration guides
  - Best practices

- 📋 **Feature Summary:** `SSL_CHAIN_CHECK_SUMMARY.md`
  - Technical implementation details
  - API documentation
  - Future enhancements

- 🛠️ **Example Script:** `examples/validate_ssl_chain.sh`
  - Production-ready validation workflow
  - Color-coded output
  - Complete security checks

---

## 🔍 Related Commands

```bash
# Check certificate details
python manage_certificates.py check cert.pem --detailed

# Validate certificate + key match
python manage_certificates.py validate cert.pem key.pem

# Check domain coverage
python manage_certificates.py domain example.com cert.pem

# Check remote certificate
python manage_certificates.py remote example.com --port 443

# Scan all certificates
python manage_certificates.py scan --days-warning 30

# Install certificate (after validation)
python manage_certificates.py install example.com cert.pem key.pem --chain chain.pem
```

---

## ✅ Best Practices

1. **Always validate before deployment:**
   ```bash
   ./examples/validate_ssl_chain.sh cert.pem key.pem chain.pem domain.com
   ```

2. **Include intermediate certificates:**
   ```bash
   # ✅ Good - with chain
   python manage_certificates.py check-chain cert.pem --chain chain.pem
   
   # ❌ Bad - without chain (may fail in browsers)
   python manage_certificates.py check-chain cert.pem
   ```

3. **Monitor certificate health:**
   ```bash
   # Set up daily monitoring
   0 0 * * * python manage_certificates.py scan --days-warning 30
   ```

4. **Document certificate sources:**
   - Keep inventory of certificate CAs
   - Track expiration dates
   - Document renewal procedures

5. **Test in staging first:**
   - Validate new certificates in staging environment
   - Verify chain completeness
   - Check compatibility with target browsers

---

## 🎉 Summary

**What you get:**
- ✅ Comprehensive SSL chain validation
- ✅ Detailed chain analysis and visualization
- ✅ Multiple integration methods (CLI, Python, Bash)
- ✅ Production-ready example scripts
- ✅ Extensive documentation
- ✅ Automated monitoring capabilities

**Quick Start:**
```bash
# 1. Check the help
python manage_certificates.py check-chain --help

# 2. Validate your certificate
python manage_certificates.py check-chain cert.pem --chain chain.pem

# 3. Use the comprehensive script
./examples/validate_ssl_chain.sh cert.pem key.pem chain.pem example.com
```

---

**Status:** ✅ Ready for production use

**Version:** 1.0

**Support:** See `docs/SSL_CHAIN_VALIDATION_GUIDE.md` for detailed documentation