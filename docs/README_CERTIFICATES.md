# Wildcard Certificate Documentation

## Quick Links

- **[Quick Start Guide](WILDCARD_CERTIFICATES.md)** - Comprehensive guide with examples
- **[Flow Summary](CERTIFICATE_FLOW_SUMMARY.md)** - Technical flow diagram and details

---

## Overview

This documentation covers the wildcard certificate generation system for Base WAF. The system allows you to generate Let's Encrypt wildcard certificates that cover both your base domain (e.g., `example.com`) and all subdomains (e.g., `*.example.com`).

---

## What You Get

✅ **Wildcard SSL/TLS Certificates**
- Covers `example.com` AND `*.example.com`
- Free from Let's Encrypt
- Valid for 90 days (renewable)

✅ **Two Generation Methods**
- **CLI Interactive Mode** - For terminal/SSH users
- **Web Interface** - For browser-based users

✅ **Automatic Configuration**
- Certificates installed to `/etc/caddy/certs/`
- Caddyfile automatically generated and updated
- Caddy automatically reloaded
- Site model updated with certificate paths

---

## Quick Start

### Method 1: CLI (Recommended for First-Time Users)

```bash
# Install acme.sh (one-time setup)
curl https://get.acme.sh | sh
source ~/.bashrc

# Generate wildcard certificate
python manage_certificates.py acme-wildcard example.com admin@example.com
```

**What happens:**
1. Command shows TXT records to add
2. You add them to your DNS provider
3. You press Enter when ready
4. Certificate is generated and installed
5. Caddyfile is updated automatically
6. Done! ✅

### Method 2: Web Interface

1. Navigate to your site in the web interface
2. Click **"DNS Challenge"** button
3. Click **"Get TXT Records from acme.sh"**
4. Copy the TXT record shown
5. Add it to your DNS provider
6. Wait 5-10 minutes for DNS propagation
7. Click **"Verify DNS & Generate Certificate"**
8. Done! ✅

---

## The Complete Flow

```
┌──────────────────────────────────────────────────────┐
│ 1. Click "Get TXT Records" (Web)                    │
│    OR run acme-wildcard command (CLI)               │
└──────────────────┬───────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│ 2. acme.sh extracts TXT record from Let's Encrypt   │
│    Example:                                          │
│    Name:  _acme-challenge.example.com                │
│    Value: XxXxXxXxXxXxXxXxXxXx                      │
└──────────────────┬───────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│ 3. You add TXT record to your DNS provider          │
│    (Cloudflare, Route53, etc.)                      │
└──────────────────┬───────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│ 4. You click "Verify" (Web)                         │
│    OR press Enter (CLI)                             │
└──────────────────┬───────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│ 5. System verifies DNS record                       │
│    System generates certificate                      │
│    System installs to /etc/caddy/certs/             │
│    System updates Caddyfile                         │
│    System reloads Caddy                             │
└──────────────────┬───────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│ ✅ SUCCESS! Certificate is live!                    │
└──────────────────────────────────────────────────────┘
```

---

## Key Features

### 1. TXT Record Extraction
The system **extracts TXT records directly from acme.sh** output, so you don't have to manually calculate or generate challenge values.

### 2. User-Friendly Display
- **CLI**: Clear terminal output with copy-paste ready values
- **Web**: Table format with copy buttons for easy copying

### 3. DNS Verification
Before generating the certificate, the system verifies:
- TXT record exists in DNS
- Value matches expected challenge
- Shows propagation status across multiple DNS servers

### 4. Automatic Installation
After successful generation:
- Certificates copied to `/etc/caddy/certs/domain/`
- Certificate validated (covers domain and wildcard)
- Private key verified to match certificate

### 5. Automatic Caddyfile Management
- Creates `/etc/caddy/sites/domain.caddy` with TLS config
- Updates main `/etc/caddy/Caddyfile` to import site configs
- Includes security headers (HSTS, etc.)
- Configures reverse proxy to backend

### 6. Automatic Caddy Reload
- Tries `caddy reload` command
- Falls back to Caddy API if needed
- Validates configuration before reload

---

## Prerequisites

### Required
- **acme.sh installed**: `curl https://get.acme.sh | sh`
- **DNS access**: Ability to add TXT records to your DNS provider
- **Caddy installed**: Running Caddy web server

### Optional
- **Sudo access**: For writing to `/etc/caddy/` (or change ownership)
- **Caddy API enabled**: For automatic reload via API

---

## File Structure After Generation

```
/etc/caddy/
├── Caddyfile                          # Main config
│   └── import /etc/caddy/sites/*.caddy
│
├── certs/
│   └── example.com/
│       ├── cert.pem                   # Full certificate chain
│       ├── key.pem                    # Private key
│       └── chain.pem                  # CA intermediate chain
│
└── sites/
    └── example.com.caddy              # Auto-generated site config

~/.acme.sh/
└── example.com/
    ├── fullchain.cer                  # Source cert from Let's Encrypt
    ├── example.com.key                # Source private key
    └── ca.cer                         # Source CA chain
```

---

## Common Use Cases

### Use Case 1: New Domain Setup
```bash
# First time certificate for new domain
python manage_certificates.py acme-wildcard newdomain.com admin@newdomain.com
```

### Use Case 2: Testing Before Production
```bash
# Use staging to avoid rate limits while testing
python manage_certificates.py acme-wildcard testdomain.com admin@test.com --staging
```

### Use Case 3: Web Interface User
1. Add new site in web interface with "Support Subdomains" enabled
2. Navigate to DNS Challenge page
3. Follow on-screen instructions
4. Certificate generated and installed automatically

---

## Verification Commands

### Check Certificate Details
```bash
python manage_certificates.py check /etc/caddy/certs/example.com/cert.pem --detailed
```

### Verify Domain Coverage
```bash
# Check base domain
python manage_certificates.py domain example.com /etc/caddy/certs/example.com/cert.pem

# Check wildcard coverage
python manage_certificates.py domain www.example.com /etc/caddy/certs/example.com/cert.pem
python manage_certificates.py domain api.example.com /etc/caddy/certs/example.com/cert.pem
```

### Check DNS Propagation Manually
```bash
dig TXT _acme-challenge.example.com
```

### Validate Caddyfile
```bash
caddy validate --config /etc/caddy/Caddyfile
```

---

## Troubleshooting Quick Reference

| Problem | Solution |
|---------|----------|
| acme.sh not found | Install: `curl https://get.acme.sh \| sh` |
| DNS record not found | Wait 5-10 minutes for propagation |
| DNS value mismatch | Copy exact value, check for spaces |
| Certificate generation fails | Check acme.sh logs: `~/.acme.sh/example.com/*.log` |
| Caddyfile not updating | Check permissions on `/etc/caddy/` |
| Caddy not reloading | Manually reload: `caddy reload --config /etc/caddy/Caddyfile` |
| Rate limit hit | Use `--staging` flag for testing |

---

## Important Notes

⚠️ **DNS Propagation Takes Time**
- Minimum: 5-10 minutes
- Maximum: Can take up to 1 hour
- Use "Check Propagation" to monitor status

⚠️ **Let's Encrypt Rate Limits**
- Production: 50 certificates per week per domain
- Use `--staging` flag when testing
- Staging certificates are NOT trusted by browsers

⚠️ **Certificate Validity**
- Certificates valid for 90 days
- Renewal recommended at 60 days
- acme.sh sets up automatic renewal via cron

⚠️ **Wildcard Certificates**
- Cover `*.example.com` (all subdomains)
- Also cover `example.com` (base domain)
- Do NOT cover `*.*.example.com` (nested subdomains)

---

## Support & Documentation

- **Main Guide**: [WILDCARD_CERTIFICATES.md](WILDCARD_CERTIFICATES.md) - Comprehensive guide with examples
- **Technical Flow**: [CERTIFICATE_FLOW_SUMMARY.md](CERTIFICATE_FLOW_SUMMARY.md) - Detailed flow diagrams
- **acme.sh Docs**: https://github.com/acmesh-official/acme.sh
- **Let's Encrypt Docs**: https://letsencrypt.org/docs/

---

## Example: Complete Workflow

```bash
# 1. Install acme.sh (one-time)
curl https://get.acme.sh | sh
source ~/.bashrc

# 2. Test with staging first
python manage_certificates.py acme-wildcard example.com admin@example.com --staging

# Output shows:
# Domain: '_acme-challenge.example.com'
# TXT value: 'XxXxXxXxXxXxXxXxXxXx'

# 3. Add TXT record to DNS provider
# - Log into Cloudflare/Route53/etc.
# - Add TXT record with above values
# - Wait 5-10 minutes

# 4. Press Enter when ready
# acme.sh verifies DNS and generates certificate

# 5. System automatically:
# - Installs certificate to /etc/caddy/certs/example.com/
# - Creates /etc/caddy/sites/example.com.caddy
# - Updates /etc/caddy/Caddyfile
# - Reloads Caddy

# 6. Verify it worked
python manage_certificates.py check /etc/caddy/certs/example.com/cert.pem

# 7. Test with browser
# Visit: https://example.com and https://www.example.com

# 8. If everything works, generate production cert
python manage_certificates.py acme-wildcard example.com admin@example.com
```

---

## Contributing

Found a bug or have a suggestion? Please:
1. Check existing documentation
2. Review troubleshooting guide
3. Check acme.sh logs
4. Create an issue with details

---

**Last Updated**: 2024-01-15  
**Version**: 1.0  
**Maintained By**: Base WAF Team