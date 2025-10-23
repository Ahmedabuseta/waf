# Wildcard Certificate Generation Guide

This guide explains how to generate wildcard SSL certificates for your domains using the Base WAF system. Wildcard certificates cover both the base domain (e.g., `example.com`) and all its subdomains (e.g., `*.example.com`).

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Method 1: CLI Interactive Mode](#method-1-cli-interactive-mode)
- [Method 2: Web Interface](#method-2-web-interface)
- [How It Works](#how-it-works)
- [Troubleshooting](#troubleshooting)
- [Manual Caddyfile Update](#manual-caddyfile-update)

---

## Overview

The system supports two methods for generating wildcard certificates:

1. **CLI Interactive Mode**: Run a command that shows you the TXT records and waits for you to add them
2. **Web Interface**: Use the web UI to see TXT records, add them, and click verify

Both methods use `acme.sh` with DNS manual validation to obtain Let's Encrypt certificates.

---

## Prerequisites

### 1. Install acme.sh

```bash
curl https://get.acme.sh | sh
source ~/.bashrc  # or ~/.zshrc
```

### 2. Verify Installation

```bash
~/.acme.sh/acme.sh --version
```

### 3. DNS Access

You need access to your DNS provider to add TXT records.

---

## Method 1: CLI Interactive Mode

### Step 1: Run the Certificate Generation Command

From the project root directory:

```bash
python manage_certificates.py acme-wildcard example.com admin@example.com
```

**For testing (recommended for first try):**

```bash
python manage_certificates.py acme-wildcard example.com admin@example.com --staging
```

### Step 2: Follow acme.sh Instructions

The command will:

1. **Display TXT records** you need to add:
   ```
   Add the following TXT record to your domains:
   Domain: '_acme-challenge.example.com'
   TXT value: 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
   ```

2. **Wait for you** - The command pauses here

3. **You add the TXT record** to your DNS provider

4. **You press Enter** when ready

5. **Verify and generate** - acme.sh verifies the DNS and generates the certificate

### Step 3: Automatic Installation

Once acme.sh completes, the system automatically:

- ✅ Copies certificate to `/etc/caddy/certs/example.com/`
- ✅ Verifies the certificate covers `example.com` and `*.example.com`
- ✅ Updates Caddyfile configuration at `/etc/caddy/sites/example.com.caddy`
- ✅ Reloads Caddy to apply changes

### Example Output

```
🔐 Generating wildcard certificate for example.com
📧 Using email: admin@example.com

======================================================================
🔄 Starting acme.sh certificate generation process...
======================================================================

📝 acme.sh will now:
   1. Show you the TXT records to add to your DNS
   2. Wait for you to add them
   3. Ask you to press Enter when ready
   4. Verify the DNS records
   5. Generate the certificate

⏳ Please wait for acme.sh instructions...
======================================================================

[acme.sh output showing TXT records...]

✅ acme.sh completed successfully!
📦 Installing certificate to /etc/caddy/certs/example.com...
✅ Certificate verification passed!
📝 Updating Caddyfile configuration...
✅ Caddyfile updated: /etc/caddy/sites/example.com.caddy
✅ Caddy reloaded successfully

======================================================================
🎉 SUCCESS! Wildcard certificate generated and installed!
======================================================================
📄 Certificate: /etc/caddy/certs/example.com/cert.pem
🔑 Private Key: /etc/caddy/certs/example.com/key.pem
🌐 Covers: example.com and *.example.com
======================================================================
```

---

## Method 2: Web Interface

### Step 1: Configure Site for Wildcard Certificate

1. Go to **Sites** → **Add New Site** or edit existing site
2. Set:
   - **Protocol**: HTTPS
   - **Auto SSL**: ✓ Enabled
   - **Support Subdomains**: ✓ Enabled
3. Click **Save**

### Step 2: Access DNS Challenge Page

1. Go to site detail page
2. Click **DNS Challenge** button
3. System automatically generates TXT record values

### Step 3: View TXT Records

The page displays the TXT record you need to add:

```
DNS Record Name: _acme-challenge.example.com
DNS Record Type: TXT
DNS Record Value: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Step 4: Add TXT Record to Your DNS

Go to your DNS provider (Cloudflare, Route53, etc.) and add the TXT record:

- **Type**: TXT
- **Name**: `_acme-challenge` or `_acme-challenge.example.com`
- **Value**: (the value shown in the UI)
- **TTL**: 300 (5 minutes) or automatic

### Step 5: Wait for DNS Propagation

**Important**: Wait 5-10 minutes for DNS to propagate globally.

You can check propagation using the **Check Propagation** button or:

```bash
dig TXT _acme-challenge.example.com
```

### Step 6: Verify and Generate Certificate

1. Click **Verify DNS Record** button
2. System will:
   - ✅ Verify DNS TXT record exists and matches
   - ✅ Call acme.sh to generate certificate
   - ✅ Install certificate to domain directory
   - ✅ Update Caddyfile automatically
   - ✅ Reload Caddy
3. Success message appears with certificate details

### Step 7: Confirm Certificate is Active

Go to site detail page and verify:
- Certificate path is populated
- Certificate expiry date is shown
- Status shows "Active"

---

## How It Works

### DNS Manual Mode Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. User initiates certificate generation                   │
│    (CLI command or Web interface)                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. System generates DNS challenge value                    │
│    Example: _acme-challenge.example.com                    │
│    TXT Value: random_string_from_letsencrypt              │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. System shows TXT record to user                         │
│    CLI: Displays in terminal and waits                     │
│    Web: Shows on DNS challenge page                        │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. User adds TXT record to DNS provider                    │
│    (Cloudflare, Route53, etc.)                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. User confirms ready                                      │
│    CLI: Presses Enter                                       │
│    Web: Clicks "Verify DNS Record"                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. System verifies DNS TXT record                          │
│    - Checks record exists                                   │
│    - Validates value matches                                │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. acme.sh generates certificate                            │
│    - Contacts Let's Encrypt                                 │
│    - Proves domain ownership via DNS                        │
│    - Receives signed certificate                            │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 8. System installs certificate                              │
│    - Copies to /etc/caddy/certs/domain/                    │
│    - Verifies certificate validity                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 9. System updates Caddyfile                                 │
│    - Creates/updates /etc/caddy/sites/domain.caddy         │
│    - Adds TLS configuration with cert paths                │
│    - Ensures main Caddyfile imports site configs           │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 10. System reloads Caddy                                    │
│     - Runs: caddy reload                                    │
│     - Or uses Caddy API                                     │
│     - Certificate is now active                             │
└─────────────────────────────────────────────────────────────┘
```

### Certificate Storage Structure

```
/etc/caddy/
├── Caddyfile                          # Main config (imports sites/*.caddy)
├── certs/
│   └── example.com/
│       ├── cert.pem                   # Full certificate chain
│       ├── key.pem                    # Private key
│       └── chain.pem                  # CA chain
└── sites/
    └── example.com.caddy              # Site-specific config
```

### Generated Caddyfile Configuration

The system automatically creates `/etc/caddy/sites/example.com.caddy`:

```caddy
# Caddy configuration for example.com
# Generated on 2024-01-15 10:30:00

example.com, *.example.com {
    tls /etc/caddy/certs/example.com/cert.pem /etc/caddy/certs/example.com/key.pem

    # Reverse proxy to backend (customize as needed)
    reverse_proxy localhost:8000

    # Logging
    log {
        output file /var/log/caddy/example.com.log
        format json
    }

    # Security headers
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        X-XSS-Protection "1; mode=block"
    }
}
```

---

## Troubleshooting

### DNS Record Not Found

**Problem**: Verification fails with "DNS TXT record not found"

**Solutions**:
1. Wait longer for DNS propagation (can take up to 1 hour)
2. Verify record was added correctly in DNS provider
3. Check DNS propagation: `dig TXT _acme-challenge.example.com`
4. Ensure you used the exact value (no extra spaces)

### DNS Record Value Mismatch

**Problem**: "DNS TXT record exists but value doesn't match"

**Solutions**:
1. Double-check you copied the full value
2. Remove any extra quotes or spaces
3. Regenerate challenge if value is old (>24 hours)

### acme.sh Not Found

**Problem**: "acme.sh is not installed"

**Solution**:
```bash
curl https://get.acme.sh | sh
source ~/.bashrc
```

### Certificate Already Exists

**Problem**: acme.sh says "certificate already exists"

**Solutions**:
1. Use existing certificate from `~/.acme.sh/example.com/`
2. Force renewal: `~/.acme.sh/acme.sh --renew -d example.com --force`

### Caddy Reload Failed

**Problem**: Certificate generated but Caddy didn't reload

**Solutions**:
1. Manually reload: `caddy reload --config /etc/caddy/Caddyfile`
2. Check Caddy is running: `systemctl status caddy`
3. Check Caddyfile syntax: `caddy validate --config /etc/caddy/Caddyfile`

### Permission Denied

**Problem**: Cannot write to `/etc/caddy/`

**Solutions**:
1. Run with sudo: `sudo python manage_certificates.py acme-wildcard ...`
2. Or change ownership: `sudo chown -R $USER:$USER /etc/caddy/`

---

## Manual Caddyfile Update

If automatic Caddyfile update fails, you can manually update it:

### 1. Create Site Config File

Create `/etc/caddy/sites/example.com.caddy`:

```caddy
example.com, *.example.com {
    tls /etc/caddy/certs/example.com/cert.pem /etc/caddy/certs/example.com/key.pem
    
    reverse_proxy localhost:8000
    
    log {
        output file /var/log/caddy/example.com.log
    }
}
```

### 2. Update Main Caddyfile

Edit `/etc/caddy/Caddyfile` and add at the top:

```caddy
import /etc/caddy/sites/*.caddy

{
    admin localhost:2019
    auto_https off
}
```

### 3. Validate and Reload

```bash
caddy validate --config /etc/caddy/Caddyfile
caddy reload --config /etc/caddy/Caddyfile
```

---

## Certificate Renewal

Let's Encrypt certificates are valid for 90 days. To renew:

### Automatic Renewal (Recommended)

acme.sh automatically sets up a cron job for renewals:

```bash
crontab -l | grep acme.sh
```

### Manual Renewal

```bash
~/.acme.sh/acme.sh --renew -d example.com -d *.example.com
```

### Check Certificate Expiry

```bash
python manage_certificates.py check /etc/caddy/certs/example.com/cert.pem
```

---

## Additional Commands

### Check Certificate Details

```bash
python manage_certificates.py check /etc/caddy/certs/example.com/cert.pem --detailed
```

### Verify Domain Coverage

```bash
python manage_certificates.py domain example.com /etc/caddy/certs/example.com/cert.pem
python manage_certificates.py domain www.example.com /etc/caddy/certs/example.com/cert.pem
```

### Scan All Certificates

```bash
python manage_certificates.py scan --show-expired --days-warning 30
```

### Backup Certificates

```bash
python manage_certificates.py backup /path/to/backup
```

---

## Best Practices

1. **Test First**: Always use `--staging` flag for testing to avoid rate limits
2. **DNS TTL**: Set low TTL (300 seconds) before adding TXT records
3. **Wait for Propagation**: Give DNS 5-10 minutes to propagate
4. **Monitor Expiry**: Check certificates monthly, renew at 60 days
5. **Backup**: Backup certificates before renewal
6. **Verify Coverage**: Always verify wildcard covers your subdomains

---

## Support

For issues or questions:

1. Check logs: `/var/log/caddy/` and acme.sh logs
2. Verify DNS: `dig TXT _acme-challenge.example.com`
3. Check acme.sh logs: `~/.acme.sh/example.com/example.com.log`
4. Review this documentation
5. Contact system administrator

---

**Last Updated**: 2024-01-15
**Version**: 1.0