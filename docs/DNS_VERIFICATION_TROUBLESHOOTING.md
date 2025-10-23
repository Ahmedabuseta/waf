# DNS Verification Troubleshooting Guide

## Common Issue: "Record #2 NOT FOUND IN DNS"

### Problem Description

When generating a wildcard certificate, you see:
- ✅ Record #1 verified successfully
- ❌ Record #2 NOT FOUND IN DNS - You need to add this record!

### Why This Happens

**Wildcard certificates require TWO TXT records with the SAME name but DIFFERENT values.**

When requesting a certificate for both `example.com` AND `*.example.com`, Let's Encrypt requires TWO separate DNS challenges:
- One challenge for the base domain (`example.com`)
- One challenge for the wildcard (`*.example.com`)

Both challenges use the same DNS record name (`_acme-challenge.example.com`), but each has a unique validation value.

### The Solution

You need to add **BOTH TXT records** to your DNS provider. They should look like this:

```
Type: TXT
Name: _acme-challenge.example.com
Value: sPJc4iVCg-FMu6b-UTISFMg5_URMtjybNzfAH30APos

Type: TXT
Name: _acme-challenge.example.com
Value: xK2Lp9RvNq-8YtUvBmQwXz4_VaNpQdEfGh56Ij78KlM
```

**Important:** These are TWO SEPARATE records, NOT one record with both values!

### Step-by-Step Fix

1. **Identify Missing Records**
   - Check the verification error message
   - Note which record numbers failed (usually Record #2)

2. **Go to Your DNS Provider**
   - Log into your DNS management console
   - Navigate to your domain's DNS records

3. **Add ALL TXT Records**
   - Add Record #1:
     - Type: `TXT`
     - Name/Host: `_acme-challenge.example.com` (or just `_acme-challenge` if your provider auto-adds the domain)
     - Value: (copy from "TXT Record #1" in the interface)
     - TTL: `300` or `Auto`
   
   - Add Record #2 (as a SEPARATE record):
     - Type: `TXT`
     - Name/Host: `_acme-challenge.example.com` (SAME as Record #1)
     - Value: (copy from "TXT Record #2" in the interface - DIFFERENT value than Record #1)
     - TTL: `300` or `Auto`

4. **Verify Both Records Were Added**
   - You should see TWO TXT records in your DNS provider
   - Both with the same name
   - Each with a different value

5. **Wait for DNS Propagation**
   - Wait 5-10 minutes for changes to propagate
   - Some providers are faster (1-2 minutes)
   - Some can take up to 24 hours

6. **Check Propagation**
   - Click "Check DNS Propagation" button
   - Verify both values are found

7. **Verify and Generate Certificate**
   - Click "Verify DNS & Generate Certificate"
   - Should now succeed if both records are present

## DNS Provider-Specific Notes

### Cloudflare
- ✅ Supports multiple TXT records with the same name
- Use `_acme-challenge` in the Name field (omit domain)
- TTL: Set to "Auto" or "2 minutes"
- Make sure "Proxy status" is set to "DNS only" (gray cloud)

### AWS Route53
- ✅ Supports multiple TXT records with the same name
- Use FQDN: `_acme-challenge.example.com.` (note the trailing dot)
- Add both values as separate records
- TTL: 300 seconds recommended

### GoDaddy
- ✅ Supports multiple TXT records with the same name
- Use `_acme-challenge` in the Host field
- Add each record separately with "Add Another Record" button
- TTL: 600 seconds (default)

### Namecheap
- ✅ Supports multiple TXT records with the same name
- Use `_acme-challenge` in the Host field
- Add both records separately
- TTL: Automatic

### Google Domains (Cloud DNS)
- ✅ Supports multiple TXT records with the same name
- Use FQDN: `_acme-challenge.example.com`
- Add as separate TXT records
- TTL: 300 seconds

### Some DNS Providers Don't Support Multiple TXT Records
If your DNS provider doesn't support multiple TXT records with the same name:
- Consider using a different DNS provider for just the `_acme-challenge` subdomain
- Use DNS delegation to delegate `_acme-challenge.example.com` to a different nameserver
- Contact your provider to ask if they support multiple TXT records

## Verification Commands

You can manually verify your DNS records using command-line tools:

### Using dig (Linux/Mac)
```bash
dig TXT _acme-challenge.example.com +short
```

**Expected output (both values):**
```
"sPJc4iVCg-FMu6b-UTISFMg5_URMtjybNzfAH30APos"
"xK2Lp9RvNq-8YtUvBmQwXz4_VaNpQdEfGh56Ij78KlM"
```

### Using nslookup (Windows/Mac/Linux)
```bash
nslookup -type=TXT _acme-challenge.example.com
```

### Using online tools
- https://mxtoolbox.com/TXTLookup.aspx
- https://dnschecker.org/
- https://www.whatsmydns.net/

## Common Mistakes

### ❌ Mistake #1: Only Adding One Record
**Wrong:** Adding only Record #1 and skipping Record #2

**Why it fails:** Let's Encrypt needs to verify both the base domain and wildcard separately

**Fix:** Add BOTH records

### ❌ Mistake #2: Replacing Instead of Adding
**Wrong:** Deleting Record #1 when adding Record #2

**Why it fails:** Both records must exist simultaneously

**Fix:** Keep Record #1 and ADD Record #2 as a separate entry

### ❌ Mistake #3: Combining Values
**Wrong:** Creating one record with both values like:
```
Name: _acme-challenge.example.com
Value: value1,value2
```

**Why it fails:** Each value must be in a separate TXT record

**Fix:** Create two separate TXT records

### ❌ Mistake #4: Wrong Record Name
**Wrong:** Using different names for each record:
```
_acme-challenge.example.com
_acme-challenge-2.example.com
```

**Why it fails:** Both records MUST have the exact same name

**Fix:** Use `_acme-challenge.example.com` for BOTH records

### ❌ Mistake #5: Not Waiting for Propagation
**Wrong:** Clicking "Verify" immediately after adding records

**Why it fails:** DNS changes need time to propagate

**Fix:** Wait 5-10 minutes, use "Check DNS Propagation" first

## Understanding the Error Message

When you see this error:

```
Record #1: _acme-challenge.example.com
✅ Record #1 verified successfully!
Value matches: sPJc4iVCg...

Record #2: _acme-challenge.example.com
❌ VALUE MISMATCH - This record value is missing!
Expected TXT value: xK2Lp9RvN...
Found in DNS: sPJc4iVCg... (only the first value)
```

**This means:**
- The DNS system found Record #1's value ✅
- The DNS system did NOT find Record #2's value ❌
- You need to ADD Record #2 (don't replace Record #1!)

## Debugging Steps

If you're still having issues after adding both records:

1. **Check with dig/nslookup**
   ```bash
   dig TXT _acme-challenge.example.com +short
   ```
   - You should see TWO different values in the output
   - If you only see one, the second record isn't added correctly

2. **Check Multiple DNS Servers**
   ```bash
   dig TXT _acme-challenge.example.com @8.8.8.8 +short
   dig TXT _acme-challenge.example.com @1.1.1.1 +short
   ```
   - Google DNS (8.8.8.8)
   - Cloudflare DNS (1.1.1.1)
   - If results differ, DNS hasn't fully propagated yet

3. **Check Your DNS Provider's Interface**
   - Log into your DNS provider
   - View all TXT records
   - Confirm you see TWO separate entries with the same name

4. **Wait Longer**
   - Some DNS providers can take 15-30 minutes
   - TTL (Time To Live) affects how long caches persist
   - If TTL was 3600 (1 hour) before, old records may be cached

5. **Clear DNS Cache (if self-hosting)**
   ```bash
   sudo systemd-resolve --flush-caches  # Ubuntu/Debian
   sudo dscacheutil -flushcache         # macOS
   ipconfig /flushdns                   # Windows
   ```

## Still Having Issues?

### Check acme.sh logs
```bash
cat ~/.acme.sh/acme.sh.log
```

### Verify record format
Make sure:
- No extra quotes around the value
- No spaces before/after the value
- Value is exactly as shown (case-sensitive)
- Record type is TXT, not CNAME or A

### Contact Support
If all else fails:
1. Take screenshots of your DNS provider showing both records
2. Run `dig TXT _acme-challenge.yourdomain.com +short` and save output
3. Check the application logs for detailed error messages
4. Verify your DNS provider supports multiple TXT records with the same name

## Quick Reference

| What You Need | Details |
|---------------|---------|
| **Number of Records** | 2 (for wildcard cert) |
| **Record Type** | TXT |
| **Record Name** | `_acme-challenge.yourdomain.com` (SAME for both) |
| **Record Values** | Different for each record (shown in UI) |
| **TTL** | 300 seconds (5 minutes) or Auto |
| **Wait Time** | 5-10 minutes after adding |
| **Verification** | Use `dig` or online DNS checker |

## Success Checklist

- [ ] Both TXT records added to DNS provider
- [ ] Both records have the SAME name
- [ ] Both records have DIFFERENT values
- [ ] Values match exactly what's shown in the interface
- [ ] Waited at least 5-10 minutes
- [ ] Verified with `dig` or DNS checker showing both values
- [ ] "Check DNS Propagation" shows both records found
- [ ] Ready to click "Verify DNS & Generate Certificate"

---

**Remember:** The key to success is having BOTH TXT records active in DNS at the same time, with the same name but different values!