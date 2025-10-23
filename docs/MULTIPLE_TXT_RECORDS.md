# Multiple TXT Records for Wildcard Certificates

## Why Two TXT Records?

When generating a wildcard certificate for a domain (e.g., `p2s.tech`), Let's Encrypt requires **TWO separate TXT records** to prove you control both:

1. **Base domain**: `p2s.tech`
2. **Wildcard subdomains**: `*.p2s.tech`

Each domain requires its own DNS challenge, resulting in **two TXT records with the SAME NAME but DIFFERENT VALUES**.

---

## Example for p2s.tech

When you click "Get TXT Records from acme.sh", you'll see:

### Record #1
```
Name:  _acme-challenge.p2s.tech
Type:  TXT
Value: XxXxXxXxXxXxXxXxXxXxXxXx  (random string from Let's Encrypt)
TTL:   300
```

### Record #2
```
Name:  _acme-challenge.p2s.tech
Type:  TXT
Value: YyYyYyYyYyYyYyYyYyYyYyYy  (different random string)
TTL:   300
```

**IMPORTANT**: Both records have the **SAME NAME** but **DIFFERENT VALUES**!

---

## How to Add Multiple TXT Records

Most DNS providers support multiple TXT records with the same name. Here's how to add them:

### Cloudflare

1. Go to DNS settings
2. Click **"Add record"**
3. Fill in:
   - Type: `TXT`
   - Name: `_acme-challenge`
   - Content: `[First value from Record #1]`
   - TTL: `Auto` or `300`
4. Click **"Save"**
5. Click **"Add record"** AGAIN
6. Fill in:
   - Type: `TXT`
   - Name: `_acme-challenge` (same as before)
   - Content: `[Second value from Record #2]`
   - TTL: `Auto` or `300`
7. Click **"Save"**

You should now have **TWO** separate TXT records with the same name.

---

### AWS Route53

Route53 allows multiple values in ONE record set:

1. Go to Route53 → Hosted Zones → Your domain
2. Click **"Create record"**
3. Fill in:
   - Record name: `_acme-challenge`
   - Record type: `TXT`
   - Value: Enter BOTH values, **one per line**:
     ```
     "XxXxXxXxXxXxXxXxXxXxXxXx"
     "YyYyYyYyYyYyYyYyYyYyYyYy"
     ```
   - TTL: `300`
4. Click **"Create records"**

---

### Google Cloud DNS

1. Go to Cloud DNS → Your zone
2. Click **"Add record set"**
3. Fill in:
   - DNS name: `_acme-challenge`
   - Resource record type: `TXT`
   - TXT data: Enter BOTH values, **one per line**:
     ```
     XxXxXxXxXxXxXxXxXxXxXxXx
     YyYyYyYyYyYyYyYyYyYyYyYy
     ```
   - TTL: `300`
4. Click **"Create"**

---

### GoDaddy

1. Go to DNS Management
2. Click **"Add"** under Records
3. Fill in:
   - Type: `TXT`
   - Host: `_acme-challenge`
   - TXT Value: `[First value]`
   - TTL: `1/2 hour` or `Custom: 300`
4. Click **"Save"**
5. Click **"Add"** AGAIN
6. Fill in:
   - Type: `TXT`
   - Host: `_acme-challenge`
   - TXT Value: `[Second value]`
   - TTL: `1/2 hour` or `Custom: 300`
7. Click **"Save"**

---

### Namecheap

1. Go to Advanced DNS
2. Click **"Add New Record"**
3. Fill in:
   - Type: `TXT Record`
   - Host: `_acme-challenge`
   - Value: `[First value]`
   - TTL: `Automatic` or `5 min`
4. Click **"✓"** (checkmark to save)
5. Click **"Add New Record"** AGAIN
6. Fill in:
   - Type: `TXT Record`
   - Host: `_acme-challenge`
   - Value: `[Second value]`
   - TTL: `Automatic` or `5 min`
7. Click **"✓"**

---

### DigitalOcean

1. Go to Networking → Domains → Your domain
2. In the "Add a record" section:
   - Type: `TXT`
   - Hostname: `_acme-challenge`
   - Value: `[First value]`
   - TTL: `300`
3. Click **"Create Record"**
4. Repeat with:
   - Type: `TXT`
   - Hostname: `_acme-challenge`
   - Value: `[Second value]`
   - TTL: `300`
5. Click **"Create Record"**

---

## Common Mistakes to Avoid

### ❌ WRONG: Combining values into one record
```
Name:  _acme-challenge.p2s.tech
Value: XxXxXxXxXxXxXxXxXxXxXxXx YyYyYyYyYyYyYyYyYyYyYyYy
```
**Don't do this!** The values should be in **separate records** (unless your provider specifically supports multi-value TXT records like Route53).

### ❌ WRONG: Using different names
```
Record 1: _acme-challenge.p2s.tech = XxXxXxXx...
Record 2: _acme-challenge-2.p2s.tech = YyYyYyYy...
```
**Don't do this!** Both records must have the **SAME NAME**.

### ✅ CORRECT: Two separate records, same name, different values
```
Record 1: _acme-challenge.p2s.tech = XxXxXxXxXxXxXxXxXxXxXxXx
Record 2: _acme-challenge.p2s.tech = YyYyYyYyYyYyYyYyYyYyYyYy
```

---

## Verification

### Check with dig command

After adding both records, verify with:

```bash
dig TXT _acme-challenge.p2s.tech
```

You should see **BOTH** values in the response:

```
;; ANSWER SECTION:
_acme-challenge.p2s.tech. 300 IN TXT "XxXxXxXxXxXxXxXxXxXxXxXx"
_acme-challenge.p2s.tech. 300 IN TXT "YyYyYyYyYyYyYyYyYyYyYyYy"
```

### Check with nslookup

```bash
nslookup -type=TXT _acme-challenge.p2s.tech
```

Expected output:
```
_acme-challenge.p2s.tech	text = "XxXxXxXxXxXxXxXxXxXxXxXx"
_acme-challenge.p2s.tech	text = "YyYyYyYyYyYyYyYyYyYyYyYy"
```

### Check with online tools

- https://dnschecker.org - Check global propagation
- https://toolbox.googleapps.com/apps/dig/ - Google's dig tool
- https://mxtoolbox.com/TXTLookup.aspx - TXT record lookup

Search for: `_acme-challenge.p2s.tech`

---

## Troubleshooting

### Problem: Only one TXT record appears in DNS

**Solution**: Make sure you added both records as **separate entries**. Some DNS providers require clicking "Add Record" twice.

### Problem: DNS verification fails with "value mismatch"

**Possible causes**:
1. You only added one of the two records
2. You added the records but with wrong values
3. DNS hasn't propagated yet (wait 5-10 minutes)

**Solution**:
1. Verify BOTH records exist: `dig TXT _acme-challenge.p2s.tech`
2. Check values match exactly (case-sensitive)
3. Wait for DNS propagation
4. Use "Check DNS Propagation" button to monitor status

### Problem: DNS provider doesn't support multiple TXT records with same name

**Rare, but if this happens**:
1. Check your DNS provider's documentation
2. Some providers use a different format (like Route53's multi-line values)
3. Consider switching to a modern DNS provider (Cloudflare, Route53, etc.)

---

## Complete Workflow with Multiple Records

### Step 1: Get TXT Records
Click "Get TXT Records from acme.sh" button

### Step 2: See Two Records
System displays:
- TXT Record #1 (1 of 2)
- TXT Record #2 (2 of 2)

### Step 3: Copy Values
Use copy buttons to copy:
1. Record #1 value
2. Record #2 value

### Step 4: Add to DNS Provider
Add **TWO separate TXT records**:
- Both with name: `_acme-challenge.p2s.tech`
- Each with its own unique value

### Step 5: Wait for Propagation
Wait 5-10 minutes for DNS to propagate globally

### Step 6: Verify
Click "Check DNS Propagation" to monitor status

### Step 7: Generate Certificate
When propagation is complete (100%), click "Verify DNS & Generate Certificate"

### Step 8: Success!
System will:
- ✅ Verify both TXT records
- ✅ Generate wildcard certificate
- ✅ Install to `/etc/caddy/certs/p2s.tech/`
- ✅ Update Caddyfile
- ✅ Reload Caddy
- ✅ Certificate is LIVE for both `p2s.tech` and `*.p2s.tech`

---

## Why This Matters

The wildcard certificate will cover:
- ✅ `p2s.tech` (base domain)
- ✅ `www.p2s.tech` (www subdomain)
- ✅ `api.p2s.tech` (api subdomain)
- ✅ `app.p2s.tech` (app subdomain)
- ✅ `*.p2s.tech` (ANY subdomain)

All with **ONE certificate**!

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────┐
│ Multiple TXT Records Quick Reference                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ Record #1:                                               │
│   Name:  _acme-challenge.p2s.tech                       │
│   Type:  TXT                                             │
│   Value: [Copy from UI - Record #1]                     │
│   TTL:   300                                             │
│                                                          │
│ Record #2:                                               │
│   Name:  _acme-challenge.p2s.tech  ← SAME NAME!         │
│   Type:  TXT                                             │
│   Value: [Copy from UI - Record #2]  ← DIFFERENT VALUE! │
│   TTL:   300                                             │
│                                                          │
│ ⚠️  BOTH records must exist for verification to pass!   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## Support

If you're still having trouble:
1. Check your DNS provider's documentation
2. Use "Check DNS Propagation" to see which servers have the records
3. Verify both values are copied exactly (no extra spaces or quotes)
4. Wait longer for DNS propagation (can take up to 1 hour in rare cases)
5. Try "Regenerate TXT Records" to get fresh values

---

**Last Updated**: 2024-01-15  
**Applies To**: Wildcard certificate generation for all domains  
**Required**: 2 TXT records for base domain + wildcard coverage