# Wildcard Certificate Generation - Testing Checklist

## Pre-Testing Setup

### Prerequisites
- [ ] acme.sh installed: `~/.acme.sh/acme.sh --version`
- [ ] Caddy installed and running: `systemctl status caddy`
- [ ] Access to DNS provider (Cloudflare, Route53, etc.)
- [ ] Test domain available
- [ ] Permissions to write to `/etc/caddy/`

---

## Feature Testing Checklist

### ✅ 1. Display TXT Records to User with Copy Buttons

#### Web Interface Test
- [ ] Navigate to site with "Support Subdomains" enabled
- [ ] Click "DNS Challenge" button
- [ ] Click "Get TXT Records from acme.sh" button
- [ ] Verify TXT records are displayed in table format
- [ ] Verify "Name/Host" field shows `_acme-challenge.domain.com`
- [ ] Verify "Value" field shows random challenge string
- [ ] Verify "Type" shows "TXT"
- [ ] Verify "TTL" shows "300"
- [ ] Click copy button next to "Name/Host"
  - [ ] Button changes to "✅ Copied!" for 2 seconds
  - [ ] Text is copied to clipboard
- [ ] Click copy button next to "Value"
  - [ ] Button changes to "✅ Copied!" for 2 seconds
  - [ ] Text is copied to clipboard
- [ ] Verify records are highlighted with green badge "Extracted from acme.sh"

#### CLI Test
```bash
python manage_certificates.py acme-wildcard test.example.com admin@example.com --staging
```
- [ ] Command displays TXT record name
- [ ] Command displays TXT record value
- [ ] Command displays instructions
- [ ] Output is formatted and readable

**Expected Output:**
```
Domain: '_acme-challenge.test.example.com'
TXT value: 'xxxxxxxxxxxxxxxxxxxxxxxx'
```

---

### ✅ 2. Wait for User to Add DNS Records

#### Web Interface Test
- [ ] After getting TXT records, "Verify DNS & Generate Certificate" button is enabled
- [ ] Instruction box shows: "After adding DNS records, wait at least 5-10 minutes"
- [ ] Step-by-step workflow is displayed (5 steps)
- [ ] No automatic verification happens (waits for user click)

#### CLI Test
- [ ] Command shows instructions and waits
- [ ] Message says "Please wait for acme.sh instructions..."
- [ ] acme.sh displays TXT records
- [ ] Command pauses and waits for Enter key
- [ ] No verification until user presses Enter

**Manual Step:**
- [ ] Add TXT record to actual DNS provider
- [ ] Verify record is added: `dig TXT _acme-challenge.test.example.com`

---

### ✅ 3. Verify DNS Records Before Generating Certificate

#### Web Interface Test
- [ ] Click "Check DNS Propagation" button
- [ ] Propagation status shows percentage (e.g., "75%")
- [ ] Shows number of servers checked (e.g., "6/8 servers")
- [ ] Progress bar displays visually
- [ ] Shows status:
  - [ ] "Fully propagated" (green) if 100%
  - [ ] "Mostly propagated" (yellow) if >60%
  - [ ] "In progress" (orange) if <60%
- [ ] Detailed server results can be expanded
- [ ] Each server shows ✓ Propagated or ✗ Not found

#### Click "Verify DNS & Generate Certificate"
- [ ] System checks DNS TXT record exists
- [ ] System verifies value matches expected
- [ ] Shows error if not found or mismatch
- [ ] Only proceeds to cert generation if verified

#### CLI Test
- [ ] After pressing Enter, acme.sh verifies DNS
- [ ] If DNS not ready, error shown: "DNS record not found"
- [ ] If DNS ready, proceeds to certificate generation

**Test Cases:**
- [ ] Test with no DNS record added → Shows error
- [ ] Test with wrong DNS value → Shows mismatch error
- [ ] Test with correct DNS record → Proceeds successfully

---

### ✅ 4. Generate Wildcard Certificate Using Let's Encrypt

#### Web Interface Test
After DNS verification passes:
- [ ] System shows "DNS verification successful! Generating wildcard certificate..."
- [ ] Loading/progress indicator appears
- [ ] acme.sh runs in background
- [ ] No errors from acme.sh
- [ ] Certificate files are generated in `~/.acme.sh/domain/`
  - [ ] `fullchain.cer` exists
  - [ ] `domain.key` exists
  - [ ] `ca.cer` exists

#### CLI Test
After pressing Enter with valid DNS:
- [ ] acme.sh output shows verification progress
- [ ] Shows "Verify finished, start to sign"
- [ ] Shows "Cert success"
- [ ] Certificate saved to `~/.acme.sh/domain/`

**Verify Certificate:**
```bash
openssl x509 -in ~/.acme.sh/test.example.com/fullchain.cer -text -noout
```
- [ ] Subject shows domain name
- [ ] Issuer shows Let's Encrypt
- [ ] DNS names include both `test.example.com` AND `*.test.example.com`

---

### ✅ 5. Install Certificate to Domain Directory

#### Web Interface Test
After certificate generation:
- [ ] Files copied to `/etc/caddy/certs/test.example.com/`
- [ ] `cert.pem` exists and is valid
- [ ] `key.pem` exists
- [ ] `chain.pem` exists
- [ ] File permissions are secure (readable by caddy)

#### CLI Test
- [ ] Console shows "Installing certificate to /etc/caddy/certs/test.example.com..."
- [ ] Shows "✅ Certificate verification passed!"
- [ ] All three files (cert.pem, key.pem, chain.pem) copied

**Verify Installation:**
```bash
ls -la /etc/caddy/certs/test.example.com/
python manage_certificates.py check /etc/caddy/certs/test.example.com/cert.pem
```
- [ ] cert.pem shows valid
- [ ] Covers test.example.com
- [ ] Covers *.test.example.com
- [ ] Not expired
- [ ] Issued by Let's Encrypt

---

### ✅ 6. Update Caddyfile with New Certificate Configuration

#### Web Interface Test
- [ ] File `/etc/caddy/sites/test.example.com.caddy` is created
- [ ] Contains `tls /etc/caddy/certs/test.example.com/cert.pem /etc/caddy/certs/test.example.com/key.pem`
- [ ] Contains domain: `test.example.com, *.test.example.com {`
- [ ] Contains reverse_proxy configuration
- [ ] Contains security headers (HSTS, etc.)
- [ ] Contains log configuration

#### Main Caddyfile Updated
- [ ] `/etc/caddy/Caddyfile` contains `import /etc/caddy/sites/*.caddy`
- [ ] Import line is at the top of file
- [ ] Caddyfile is valid: `caddy validate --config /etc/caddy/Caddyfile`

#### CLI Test
- [ ] Console shows "Updating Caddyfile configuration..."
- [ ] Shows "✅ Caddyfile updated: /etc/caddy/sites/test.example.com.caddy"

**Verify Caddyfile:**
```bash
cat /etc/caddy/sites/test.example.com.caddy
cat /etc/caddy/Caddyfile
caddy validate --config /etc/caddy/Caddyfile
```
- [ ] Site config contains correct TLS paths
- [ ] Main Caddyfile imports site configs
- [ ] No syntax errors

---

### ✅ 7. Reload Caddy Automatically

#### Web Interface Test
- [ ] System attempts to reload Caddy
- [ ] Shows "✅ Caddyfile has been updated and reloaded" in success message
- [ ] OR shows "Warning: Caddyfile may need manual update" if reload failed

#### CLI Test
- [ ] Console shows "✅ Caddy reloaded successfully"
- [ ] OR shows warning if reload failed

**Verify Reload:**
```bash
systemctl status caddy
journalctl -u caddy -n 20 --no-pager
curl -H "Host: test.example.com" http://localhost:2019/config/
```
- [ ] Caddy is running (active)
- [ ] No errors in logs
- [ ] New configuration is loaded
- [ ] Can access Caddy API

**Test Certificate is Active:**
```bash
curl -I https://test.example.com
openssl s_client -connect test.example.com:443 -servername test.example.com < /dev/null
```
- [ ] HTTPS connection works
- [ ] Certificate is served
- [ ] Certificate matches the one we generated
- [ ] Valid for test.example.com
- [ ] Valid for *.test.example.com

---

### ✅ 8. Complete End-to-End Automation

#### Full Web Flow Test
1. [ ] Start: Navigate to site detail page
2. [ ] Click "DNS Challenge" button
3. [ ] Click "Get TXT Records from acme.sh"
4. [ ] System displays TXT records with copy buttons
5. [ ] Copy and add TXT record to DNS provider
6. [ ] Wait 5-10 minutes
7. [ ] Click "Check DNS Propagation" → Shows progress
8. [ ] Click "Verify DNS & Generate Certificate"
9. [ ] System verifies DNS → Success
10. [ ] System generates certificate → Success
11. [ ] System installs certificate → `/etc/caddy/certs/domain/`
12. [ ] System updates Caddyfile → `/etc/caddy/sites/domain.caddy`
13. [ ] System reloads Caddy → Active
14. [ ] Site model updated with cert paths
15. [ ] DNS challenge cleared from database
16. [ ] Redirected to site detail page
17. [ ] Success message shown
18. [ ] Certificate info displayed on site detail page

#### Full CLI Flow Test
1. [ ] Run: `python manage_certificates.py acme-wildcard test.example.com admin@example.com`
2. [ ] acme.sh displays TXT records
3. [ ] Add TXT record to DNS
4. [ ] Press Enter
5. [ ] acme.sh verifies DNS
6. [ ] acme.sh generates certificate
7. [ ] System installs to `/etc/caddy/certs/`
8. [ ] System updates Caddyfile
9. [ ] System reloads Caddy
10. [ ] Success message with certificate paths shown
11. [ ] Certificate is active and serving traffic

#### Database State Test
After successful generation:
- [ ] Site model has `ssl_cert_path` populated
- [ ] Site model has `ssl_key_path` populated
- [ ] `dns_challenge_key` is cleared (None or empty)
- [ ] `dns_challenge_value` is cleared (None or empty)
- [ ] Session data for txt_records is cleared

---

## Error Handling Tests

### Test Error Cases

#### 1. acme.sh Not Installed
- [ ] Click "Get TXT Records" without acme.sh installed
- [ ] Shows error: "acme.sh is not installed"
- [ ] Shows installation instructions

#### 2. DNS Record Not Added
- [ ] Click "Verify" without adding DNS record
- [ ] Shows error: "DNS TXT record not found"
- [ ] Does not proceed to certificate generation

#### 3. DNS Record Value Mismatch
- [ ] Add DNS record with wrong value
- [ ] Click "Verify"
- [ ] Shows error: "DNS TXT record exists but value doesn't match"
- [ ] Shows expected vs found values

#### 4. Caddy Not Running
- [ ] Stop Caddy: `systemctl stop caddy`
- [ ] Generate certificate
- [ ] Certificate generated and installed successfully
- [ ] Caddyfile updated
- [ ] Shows warning: "Failed to reload Caddy"
- [ ] Provides manual reload instructions

#### 5. Permission Denied
- [ ] Remove write permissions from `/etc/caddy/`
- [ ] Try to generate certificate
- [ ] Shows appropriate error message

---

## UI/UX Tests

### Visual Elements
- [ ] Green badges for success states
- [ ] Yellow/orange for warnings
- [ ] Red for errors
- [ ] Progress bars are visible and accurate
- [ ] Copy buttons change color when clicked
- [ ] Loading indicators show during async operations
- [ ] All text is readable in both light and dark mode

### Responsiveness
- [ ] Works on desktop (1920x1080)
- [ ] Works on tablet (768x1024)
- [ ] Works on mobile (375x667)
- [ ] Copy buttons are clickable on touch devices
- [ ] Tables don't overflow on small screens

### Accessibility
- [ ] All buttons have descriptive text
- [ ] Color is not the only indicator (icons also used)
- [ ] Form inputs have labels
- [ ] Error messages are clear and actionable

---

## Performance Tests

### Response Times
- [ ] "Get TXT Records" completes in <10 seconds
- [ ] DNS verification completes in <5 seconds
- [ ] Certificate generation completes in <2 minutes
- [ ] Caddy reload completes in <5 seconds
- [ ] Total end-to-end time: <3 minutes (excluding DNS wait)

### Resource Usage
- [ ] No memory leaks during generation
- [ ] CPU usage returns to normal after completion
- [ ] Disk space sufficient for certificates
- [ ] No zombie processes left behind

---

## Security Tests

### File Permissions
- [ ] Private key (`key.pem`) has restricted permissions (600 or 640)
- [ ] Certificate files are readable by Caddy user
- [ ] TXT records are cleared from database after use
- [ ] Session data is cleared after completion

### Certificate Validation
- [ ] Certificate is valid and trusted
- [ ] Private key matches certificate
- [ ] Certificate chain is complete
- [ ] No weak ciphers or protocols

---

## Regression Tests

### Existing Functionality
- [ ] Regular (non-wildcard) certificates still work
- [ ] HTTP sites still work
- [ ] Manual certificate upload still works
- [ ] Site creation/editing still works
- [ ] Other Caddy features still work

---

## Documentation Tests

### Documentation Accuracy
- [ ] All commands in docs work as written
- [ ] Screenshots match current UI
- [ ] Examples produce expected results
- [ ] Troubleshooting steps solve actual problems

---

## Summary Checklist

After completing all tests above:

- [ ] All 8 main features work correctly
- [ ] Error handling works for all edge cases
- [ ] UI/UX is polished and user-friendly
- [ ] Performance is acceptable
- [ ] Security is maintained
- [ ] No regressions introduced
- [ ] Documentation is accurate

---

## Sign-Off

**Tester Name:** _________________

**Date:** _________________

**Environment:**
- OS: _________________
- Python Version: _________________
- Django Version: _________________
- Caddy Version: _________________
- acme.sh Version: _________________

**Overall Result:** [ ] PASS  [ ] FAIL

**Notes:**
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________