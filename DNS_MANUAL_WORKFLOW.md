# acme.sh dns_manual Workflow Guide

## Understanding dns_manual Mode

The `dns_manual` mode in acme.sh is a **two-step process** that requires careful coordination between generating challenge tokens and completing verification.

## ⚠️ CRITICAL: Challenge Token Lifecycle

### The Challenge Token Problem

Each time you run `acme.sh --issue --dns dns_manual`, it generates **NEW, UNIQUE challenge tokens**. These tokens are:
- ✅ Stored in `~/.acme.sh/domain/domain.conf`
- ✅ Used for Let's Encrypt DNS-01 validation
- ❌ **DIFFERENT every time you run --issue**

**This means:** The TXT records you add to DNS **MUST match** the exact challenge tokens from the SAME acme.sh run that you later complete with `--renew`.

### Workflow Breakdown

```
Step 1: Generate Challenge
┌─────────────────────────────────────────────────────────────┐
│ acme.sh --issue --dns dns_manual -d example.com             │
│         --yes-I-know-dns-manual-mode-enough-go-ahead-please │
│                                                             │
│ Input: n  (decline to proceed)                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
        ┌─────────────────────────────┐
        │ Creates ~/.acme.sh/example/ │
        │ - example.com.conf          │
        │ - example.com.key           │
        │ - example.com.csr           │
        │                             │
        │ Contains challenge tokens:  │
        │ - Token1: ABC123...         │
        │ - Token2: XYZ789...         │
        └─────────────────────────────┘
                      │
                      ▼
        ┌─────────────────────────────┐
        │ Displays TXT records:       │
        │                             │
        │ _acme-challenge.example.com │
        │ Value: ABC123...            │
        │                             │
        │ _acme-challenge.example.com │
        │ Value: XYZ789...            │
        └─────────────────────────────┘

Step 2: Add TXT Records to DNS
┌─────────────────────────────────────────────────────────────┐
│ User adds BOTH TXT records to DNS provider                  │
│ - Record #1: _acme-challenge.example.com → ABC123...        │
│ - Record #2: _acme-challenge.example.com → XYZ789...        │
│                                                             │
│ Wait 5-10 minutes for DNS propagation                      │
└─────────────────────────────────────────────────────────────┘

Step 3: Complete Challenge
┌─────────────────────────────────────────────────────────────┐
│ acme.sh --renew -d example.com                              │
│         --yes-I-know-dns-manual-mode-enough-go-ahead-please │
│                                                             │
│ This reads the tokens from ~/.acme.sh/example/example.conf │
│ Tells Let's Encrypt to verify DNS                          │
│ Let's Encrypt checks: Does DNS have ABC123 and XYZ789?     │
│ If YES → Certificate issued ✅                              │
│ If NO  → Verification fails ❌                              │
└─────────────────────────────────────────────────────────────┘
```

## ❌ Common Mistakes

### Mistake #1: Running --issue Multiple Times

```bash
# First run
acme.sh --issue --dns dns_manual -d example.com
# Output: TXT value: ABC123...

# Add ABC123 to DNS

# Second run (WRONG!)
acme.sh --issue --dns dns_manual -d example.com
# Output: TXT value: XYZ789... (DIFFERENT!)

# Now DNS has ABC123 but acme.sh expects XYZ789
# Result: ❌ Verification fails!
```

**Fix:** Only run `--issue` ONCE. Use `--renew` to complete.

### Mistake #2: Deleting acme.sh Config

```bash
# Generate challenge
acme.sh --issue --dns dns_manual -d example.com
# Output: TXT value: ABC123...

# Add ABC123 to DNS

# Delete config (WRONG!)
rm -rf ~/.acme.sh/example.com/

# Try to renew
acme.sh --renew -d example.com
# Result: ❌ Cannot find domain configuration!
```

**Fix:** NEVER delete `~/.acme.sh/domain/` between --issue and --renew.

### Mistake #3: Stale TXT Records

```bash
# Week 1: Generate challenge
acme.sh --issue --dns dns_manual -d example.com
# Output: TXT value: OLD123...
# Add OLD123 to DNS
# Never complete with --renew

# Week 2: Generate NEW challenge
acme.sh --issue --dns dns_manual -d example.com
# Output: TXT value: NEW456...
# Add NEW456 to DNS (but OLD123 still there)

# Try to renew
acme.sh --renew -d example.com
# Expects: NEW456
# DNS has: OLD123, NEW456
# Result: ❌ May fail if OLD123 is found first
```

**Fix:** Remove old TXT records before generating new ones.

## ✅ Correct Workflow

### In Our Application

#### Step 1: User Clicks "Get TXT Records from acme.sh"

**Code:** `get_dns_txt_records_for_verification()`

```python
# Runs:
acme.sh --issue --dns dns_manual -d example.com -d *.example.com
        --email user@example.com
        --yes-I-know-dns-manual-mode-enough-go-ahead-please

# With input: 'n\n' (decline to proceed)

# Result:
# - Creates ~/.acme.sh/example.com/
# - Stores challenge tokens in example.com.conf
# - Returns TXT records to display in UI
```

**Important:** This creates the challenge and stores tokens. Don't run this again unless you delete the old config first!

#### Step 2: User Adds TXT Records to DNS

User copies the displayed TXT records and adds them to their DNS provider:
- Record #1: `_acme-challenge.example.com` → `value1`
- Record #2: `_acme-challenge.example.com` → `value2`

Wait 5-10 minutes for propagation.

#### Step 3: User Clicks "Verify DNS & Generate Certificate"

**Code:** `verify_dns_challenge_and_generate_cert()`

```python
# Step 3a: Verify DNS has correct values
for each txt_record:
    verify_dns_challenge_record(domain, expected_value)
    # Checks if DNS contains the exact value from Step 1

# If verification passes...

# Step 3b: Check if acme.sh config exists
if not exists ~/.acme.sh/example.com/example.com.conf:
    return ERROR: "TXT records are stale, regenerate them"

# Step 3c: Complete challenge
acme.sh --renew -d example.com
        --yes-I-know-dns-manual-mode-enough-go-ahead-please

# This:
# - Reads tokens from ~/.acme.sh/example.com/example.com.conf
# - Tells Let's Encrypt to verify DNS
# - Let's Encrypt queries DNS for TXT records
# - Validates that DNS values match stored tokens
# - Issues certificate if valid
```

## 🔄 Regeneration Workflow

If the acme.sh config is deleted or challenge expires, you MUST regenerate:

```bash
# 1. Clean up old config (if exists)
rm -rf ~/.acme.sh/example.com/

# 2. Remove old TXT records from DNS
# Delete all _acme-challenge.example.com TXT records

# 3. Generate fresh challenge
acme.sh --issue --dns dns_manual -d example.com
# Get NEW TXT values

# 4. Add NEW TXT records to DNS

# 5. Wait for propagation

# 6. Complete challenge
acme.sh --renew -d example.com
```

## 📋 Validation Checklist

Before clicking "Verify DNS & Generate Certificate":

- [ ] `~/.acme.sh/domain/domain.conf` exists
- [ ] TXT records in DNS match values from "Get TXT Records"
- [ ] Did NOT run "Get TXT Records" multiple times
- [ ] Did NOT delete `~/.acme.sh/domain/` folder
- [ ] Waited 5-10 minutes for DNS propagation
- [ ] Verified with `dig TXT _acme-challenge.domain.com`

## 🐛 Troubleshooting

### Error: "acme.sh domain configuration not found"

**Cause:** The `~/.acme.sh/domain/` folder was deleted between generating TXT records and verification.

**Fix:**
1. Click "Get TXT Records from acme.sh" to regenerate
2. Update DNS with NEW TXT record values
3. Wait 5-10 minutes
4. Try verification again

### Error: "Incorrect TXT record"

**Cause:** DNS has different values than what acme.sh expects.

**Fix:**
1. Check what acme.sh expects:
   ```bash
   cat ~/.acme.sh/domain/domain.conf | grep Le_Vlist
   ```
2. Check what's in DNS:
   ```bash
   dig TXT _acme-challenge.domain.com +short
   ```
3. If they don't match, regenerate fresh TXT records

### Error: "Cannot find DNS API hook for: dns_manual"

**Cause:** You ran `--issue` instead of `--renew`, or forgot `--yes-I-know-dns-manual-mode-enough-go-ahead-please`.

**Fix:**
```bash
acme.sh --renew -d domain.com --yes-I-know-dns-manual-mode-enough-go-ahead-please
```

## 💡 Best Practices

1. **One Generation Per Attempt**
   - Generate TXT records once
   - Complete the challenge once
   - Don't regenerate unless you start over

2. **Keep Config Intact**
   - Don't delete `~/.acme.sh/domain/` between steps
   - Don't manually edit `domain.conf`

3. **Clean Slate for Retry**
   - If something fails, start completely fresh:
     ```bash
     rm -rf ~/.acme.sh/domain/
     # Remove TXT records from DNS
     # Start over from "Get TXT Records"
     ```

4. **Use Short TTL**
   - Set TXT record TTL to 300 seconds (5 minutes)
   - Helps with faster propagation and updates

5. **Verify Before Completing**
   - Always check DNS with `dig` before clicking verify
   - Use diagnostic tool: `python3 check_dns_records.py`

## 🔐 Security Note

The challenge tokens in `domain.conf` are **temporary and public**. They're meant to be added to DNS (which is public). However:
- Don't share the `domain.key` file (private key)
- The conf file can be deleted after certificate is issued
- Tokens expire after some time (usually hours)

## 📚 References

- [acme.sh dns_manual wiki](https://github.com/acmesh-official/acme.sh/wiki/dns-manual-mode)
- [Let's Encrypt DNS-01 Challenge](https://letsencrypt.org/docs/challenge-types/#dns-01-challenge)
- Our docs: `docs/DNS_VERIFICATION_TROUBLESHOOTING.md`

---

**Summary:** dns_manual mode requires a two-step dance. Generate tokens once, add them to DNS, then complete the challenge using the SAME tokens. Never regenerate between steps!