# Wildcard Certificate Generation Flow

## Overview

This document describes the web-based wildcard certificate generation flow for the WAF system. The flow allows users to generate Let's Encrypt wildcard certificates through a guided web interface with manual DNS verification.

## Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  Step 1: User Creates/Edits Site with Wildcard SSL             │
│  - Protocol: HTTPS                                              │
│  - Auto SSL: Enabled                                            │
│  - Support Subdomains: Enabled                                  │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 2: System Generates DNS Challenge                         │
│  - CertificateManager.generate_dns_challenge_for_web()          │
│  - Creates TXT record name and value                            │
│  - Stores challenge in Site model                               │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 3: Display DNS Challenge to User                          │
│  - Show TXT record name (_acme-challenge.example.com)           │
│  - Show TXT record value (random string)                        │
│  - Provide copy-to-clipboard functionality                      │
│  - Show provider-specific instructions                          │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 4: User Adds TXT Record to DNS Provider                   │
│  - User manually adds DNS TXT record                            │
│  - Waits for DNS propagation (1-15 minutes typically)           │
│  - Can check propagation status via "Check Propagation" button  │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 5: User Clicks "Verify" Button                            │
│  - System checks DNS TXT record exists                          │
│  - Verifies TXT record value matches challenge                  │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 6: System Generates Certificate                           │
│  - CertificateManager.verify_dns_challenge_and_generate_cert()  │
│  - Calls acme.sh with manual DNS mode                           │
│  - Generates certificate for domain and *.domain                │
│  - Saves cert.pem and key.pem to /etc/caddy/certs/domain/       │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 7: System Updates Caddyfile                               │
│  - Creates site-specific config file: /etc/caddy/sites/         │
│  - Adds TLS directive with cert and key paths                   │
│  - Updates main Caddyfile to import site configs                │
│  - Reloads Caddy configuration                                  │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  Step 8: Certificate Active                                     │
│  - Wildcard certificate covers domain and all subdomains        │
│  - Certificate automatically trusted by browsers                │
│  - User can proceed with site configuration                     │
└─────────────────────────────────────────────────────────────────┘
```

## Technical Implementation

### Backend Components

#### 1. CertificateManager (site_management/utils/certificate_manager.py)

**Key Methods:**

- `generate_dns_challenge_for_web(domain, support_subdomains)`: Generates DNS challenge for web display
- `verify_dns_challenge_and_generate_cert(domain, email, challenge_value, staging)`: Verifies DNS and generates certificate
- `_update_caddyfile_with_certificate(domain, cert_path, key_path)`: Updates Caddy configuration
- `_generate_caddyfile_config(domain, cert_path, key_path)`: Generates site-specific Caddyfile
- `_reload_caddy_config()`: Reloads Caddy to apply new configuration

#### 2. ACMEDNSManager (site_management/utils/acme_dns_manager.py)

**Key Methods:**

- `generate_challenge_value(domain)`: Creates ACME challenge key/value pair
- `verify_dns_challenge_record(domain, expected_value)`: Checks if DNS TXT record exists
- `check_dns_propagation(domain, expected_value)`: Checks DNS propagation across multiple servers
- `generate_challenge_instructions(domain, support_subdomains, challenge_value)`: Creates user-friendly instructions

#### 3. Views (site_management/views_caddy.py)

**dns_challenge_page(request, site_slug):**
- Handles GET: Displays DNS challenge instructions
- Handles POST with action='generate_challenge': Creates new challenge
- Handles POST with action='verify': Verifies DNS and generates certificate
- Handles POST with action='check_propagation': Checks DNS propagation status

### Frontend Components

#### Template: dns_challenge.html

**Key Features:**
- Step-by-step instructions with visual indicators
- Copy-to-clipboard buttons for TXT record values
- Real-time verification status
- Propagation checker
- Provider-specific instructions (Cloudflare, Route53, etc.)

### Data Flow

#### Site Model Fields
```python
dns_challenge_key = CharField()        # e.g., "_acme-challenge.example.com"
dns_challenge_value = CharField()      # e.g., "xYz123AbC..."
dns_challenge_created_at = DateTimeField()
ssl_cert_path = CharField()            # Path to cert.pem
ssl_key_path = CharField()             # Path to key.pem
```

#### Request Flow
```
User Action → View → CertificateManager → acme.sh → Certificate Files
                ↓                              ↓
           Site Model ← Update ← Verify ← DNS TXT Record
                ↓
        Caddyfile Update → Caddy Reload
```

## File Structure

```
/etc/caddy/
├── Caddyfile                          # Main config (imports sites/*.caddy)
├── certs/
│   └── example.com/
│       ├── cert.pem                   # Certificate (covers *.example.com)
│       ├── key.pem                    # Private key
│       └── chain.pem                  # Certificate chain (optional)
└── sites/
    └── example.com.caddy              # Site-specific configuration

~/.acme.sh/
└── example.com/                       # acme.sh certificate storage
    ├── fullchain.cer
    ├── domain.key
    └── ca.cer
```

## Generated Caddyfile Configuration

For a domain `example.com`, the system generates:

```caddyfile
# /etc/caddy/sites/example.com.caddy
# Generated on
