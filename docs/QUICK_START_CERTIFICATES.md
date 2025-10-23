# Quick Start: Wildcard Certificate Generation

Generate wildcard SSL certificates in 3 simple steps!

## Prerequisites

```bash
# Install acme.sh
curl https://get.acme.sh | sh
source ~/.bashrc
```

---

## CLI Method (Recommended)

### Step 1: Run Command

```bash
# Production
python manage_certificates.py acme-wildcard example.com admin@example.com

# Testing (recommended first)
python manage_certificates.py acme-wildcard example.com admin@example.com --staging
```

### Step 2: Add TXT Record

The command will show you:
```
Add the following TXT record:
Domain: '_acme-challenge.example.com'
TXT value: 'abc123...'
```

Go to your DNS provider and add this TXT record.

### Step 3: Press Enter

After adding the record, press Enter in the terminal. Done! ✅

---

## Web Interface Method

### Step 1: Configure Site
1. Go to **Sites** → **Add/Edit Site**
2. Enable: **HTTPS** +
