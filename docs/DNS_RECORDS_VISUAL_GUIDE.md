# Visual Guide: DNS Records for Wildcard Certificates

## Understanding Multiple TXT Records

### ✅ CORRECT: Two Separate Records (Same Name, Different Values)

```
┌─────────────────────────────────────────────────────────────────┐
│                     DNS PROVIDER INTERFACE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  TXT Record #1                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Type: TXT                                               │   │
│  │ Name: _acme-challenge.example.com                       │   │
│  │ Value: sPJc4iVCg-FMu6b-UTISFMg5_URMtjybNzfAH30APos      │   │
│  │ TTL:  300                                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  TXT Record #2                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Type: TXT                                               │   │
│  │ Name: _acme-challenge.example.com    ← SAME NAME!       │   │
│  │ Value: xK2Lp9RvNq-8YtUvBmQwXz4_VaNpQdEfGh56Ij78KlM      │   │
│  │ TTL:  300                                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Result:** ✅ DNS verification succeeds!

```
DNS Query: dig TXT _acme-challenge.example.com
Response:
  "sPJc4iVCg-FMu6b-UTISFMg5_URMtjybNzfAH30APos"
  "xK2Lp9RvNq-8YtUvBmQwXz4_VaNpQdEfGh56Ij78KlM"
```

---

### ❌ WRONG: Only One Record Added

```
┌─────────────────────────────────────────────────────────────────┐
│                     DNS PROVIDER INTERFACE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  TXT Record #1                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Type: TXT                                               │   │
│  │ Name: _acme-challenge.example.com                       │   │
│  │ Value: sPJc4iVCg-FMu6b-UTISFMg5_URMtjybNzfAH30APos      │   │
│  │ TTL:  300                                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ❌ Record #2 is MISSING!                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Result:** ❌ DNS verification fails!

```
Error:
Record #1: ✅ verified successfully
Record #2: ❌ VALUE MISMATCH - This record value is missing!

Expected: xK2Lp9RvNq-8YtUvBmQwXz4_VaNpQdEfGh56Ij78KlM
Found:    sPJc4iVCg-FMu6b-UTISFMg5_URMtjybNzfAH30APos (only Record #1)
```

---

### ❌ WRONG: Combined Values in One Record

```
┌─────────────────────────────────────────────────────────────────┐
│                     DNS PROVIDER INTERFACE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  TXT Record                                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Type: TXT                                               │   │
│  │ Name: _acme-challenge.example.com                       │   │
│  │ Value: sPJc4iVCg... , xK2Lp9RvNq...   ← WRONG!         │   │
│  │ TTL:  300                                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Result:** ❌ DNS verification fails - values are concatenated, not separate records!

---

### ❌ WRONG: Different Names for Each Record

```
┌─────────────────────────────────────────────────────────────────┐
│                     DNS PROVIDER INTERFACE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  TXT Record #1                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Type: TXT                                               │   │
│  │ Name: _acme-challenge.example.com                       │   │
│  │ Value: sPJc4iVCg-FMu6b-UTISFMg5_URMtjybNzfAH30APos      │   │
│  │ TTL:  300                                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  TXT Record #2                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Type: TXT                                               │   │
│  │ Name: _acme-challenge-2.example.com  ← WRONG NAME!      │   │
│  │ Value: xK2Lp9RvNq-8YtUvBmQwXz4_VaNpQdEfGh56Ij78KlM      │   │
│  │ TTL:  300                                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Result:** ❌ DNS verification fails - Record #2 has wrong name!

---

## How DNS Queries Work

### When Both Records Exist (Correct)

```
┌──────────────┐                           ┌──────────────┐
│   Your DNS   │                           │  DNS Server  │
│   Provider   │                           │              │
└──────┬───────┘                           └──────┬───────┘
       │                                          │
       │  Stores TWO TXT records:                │
       │  1. _acme-challenge.example.com → ABC   │
       │  2. _acme-challenge.example.com → XYZ   │
       │                                          │
       │                                          │
                    ┌────────────────────┐
                    │  Let's Encrypt     │
                    │  Makes DNS Query   │
                    └─────────┬──────────┘
                              │
                              │ Query: TXT _acme-challenge.example.com
                              ▼
                    ┌──────────────────┐
                    │   DNS Response   │
                    ├──────────────────┤
                    │  Value 1: ABC    │
                    │  Value 2: XYZ    │
                    └──────────────────┘
                              │
                              │ ✅ Both values found!
                              │ ✅ Challenges verified!
                              ▼
                    ┌──────────────────┐
                    │  Certificate     │
                    │  Issued! 🎉      │
                    └──────────────────┘
```

### When Only One Record Exists (Wrong)

```
┌──────────────┐                           ┌──────────────┐
│   Your DNS   │                           │  DNS Server  │
│   Provider   │                           │              │
└──────┬───────┘                           └──────┬───────┘
       │                                          │
       │  Stores ONE TXT record only:            │
       │  1. _acme-challenge.example.com → ABC   │
       │  ❌ Record #2 is MISSING!                │
       │                                          │
       │                                          │
                    ┌────────────────────┐
                    │  Let's Encrypt     │
                    │  Makes DNS Query   │
                    └─────────┬──────────┘
                              │
                              │ Query: TXT _acme-challenge.example.com
                              ▼
                    ┌──────────────────┐
                    │   DNS Response   │
                    ├──────────────────┤
                    │  Value 1: ABC    │
                    │  ❌ Value 2: ???  │
                    └──────────────────┘
                              │
                              │ ✅ Challenge #1 verified
                              │ ❌ Challenge #2 FAILED!
                              ▼
                    ┌──────────────────┐
                    │  Certificate     │
                    │  Request DENIED  │
                    └──────────────────┘
```

---

## Why Two Records Are Needed

### Wildcard Certificate Covers Two Things

```
Certificate for: example.com + *.example.com
                     │              │
                     │              └─── All subdomains
                     └────────────────── Base domain

Let's Encrypt requires separate proof for each:

Challenge #1: Prove you control example.com
  → Requires TXT record with value ABC

Challenge #2: Prove you control *.example.com  
  → Requires TXT record with value XYZ

Both challenges use the SAME record name:
  _acme-challenge.example.com
```

---

## Step-by-Step: Adding Records

### Step 1: Get Both TXT Records from the UI

```
┌───────────────────────────────────────────────────────────────┐
│  TXT Record #1 (1 of 2)                                       │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ Name:  _acme-challenge.example.com                      │  │
│  │ Value: sPJc4iVCg-FMu6b-UTISFMg5_URMtjybNzfAH30APos      │  │
│  │        [📋 Copy]                                        │  │
│  └─────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│  TXT Record #2 (2 of 2)                                       │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ Name:  _acme-challenge.example.com                      │  │
│  │ Value: xK2Lp9RvNq-8YtUvBmQwXz4_VaNpQdEfGh56Ij78KlM      │  │
│  │        [📋 Copy]                                        │  │
│  └─────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

### Step 2: Add FIRST Record to DNS Provider

```
Log into your DNS provider → Add New TXT Record

Type:  TXT
Name:  _acme-challenge.example.com
Value: sPJc4iVCg-FMu6b-UTISFMg5_URMtjybNzfAH30APos
TTL:   300

[Save Record]  ← Click to save
```

### Step 3: Add SECOND Record (Don't Replace First!)

```
Still in your DNS provider → Add ANOTHER TXT Record

Type:  TXT
Name:  _acme-challenge.example.com  ← SAME NAME as Record #1!
Value: xK2Lp9RvNq-8YtUvBmQwXz4_VaNpQdEfGh56Ij78KlM
TTL:   300

[Save Record]  ← Click to save as a NEW record
```

### Step 4: Verify Both Records Are There

```
Your DNS provider should now show:

📋 TXT Records
┌────────────────────────────────────────────────────────────┐
│ _acme-challenge.example.com                                │
│ TXT: sPJc4iVCg-FMu6b-UTISFMg5_URMtjybNzfAH30APos           │
├────────────────────────────────────────────────────────────┤
│ _acme-challenge.example.com                                │
│ TXT: xK2Lp9RvNq-8YtUvBmQwXz4_VaNpQdEfGh56Ij78KlM           │
└────────────────────────────────────────────────────────────┘

✅ Both records present with SAME name!
```

---

## Real DNS Provider Examples

### Cloudflare

```
DNS Records
┌──────────┬───────────────────────────┬─────────────────────┬─────┐
│ Type     │ Name                      │ Content             │ TTL │
├──────────┼───────────────────────────┼─────────────────────┼─────┤
│ TXT      │ _acme-challenge           │ sPJc4iVCg...        │ Auto│
├──────────┼───────────────────────────┼─────────────────────┼─────┤
│ TXT      │ _acme-challenge           │ xK2Lp9RvNq...       │ Auto│
└──────────┴───────────────────────────┴─────────────────────┴─────┘

Note: Use "_acme-challenge" in Name field (Cloudflare auto-adds domain)
```

### AWS Route53

```
Record Set Details

Record 1:
Name: _acme-challenge.example.com.
Type: TXT
Value: "sPJc4iVCg-FMu6b-UTISFMg5_URMtjybNzfAH30APos"
TTL:  300

Record 2:
Name: _acme-challenge.example.com.
Type: TXT
Value: "xK2Lp9RvNq-8YtUvBmQwXz4_VaNpQdEfGh56Ij78KlM"
TTL:  300

Note: Include trailing dot and quotes around values
```

### Namecheap

```
Host                    Record Type   Value                TTL
_acme-challenge         TXT          sPJc4iVCg...         Automatic
_acme-challenge         TXT          xK2Lp9RvNq...        Automatic

Note: Use just "_acme-challenge" in Host field
```

---

## Verification Commands

### Check if both records are present

```bash
# Using dig (Linux/Mac)
dig TXT _acme-challenge.example.com +short

# Expected output (both values):
"sPJc4iVCg-FMu6b-UTISFMg5_URMtjybNzfAH30APos"
"xK2Lp9RvNq-8YtUvBmQwXz4_VaNpQdEfGh56Ij78KlM"

# ✅ If you see BOTH values, you're good!
# ❌ If you see only ONE value, add the missing record
```

```bash
# Using nslookup (Windows/Mac/Linux)
nslookup -type=TXT _acme-challenge.example.com

# Look for multiple TXT records in the response
```

---

## Quick Checklist

Before clicking "Verify DNS & Generate Certificate":

- [ ] I have added Record #1 to my DNS provider
- [ ] I have added Record #2 to my DNS provider
- [ ] Both records have the SAME name (_acme-challenge.mydomain.com)
- [ ] Both records have DIFFERENT values
- [ ] I can see BOTH records in my DNS provider's interface
- [ ] I waited 5-10 minutes for DNS to propagate
- [ ] I verified with `dig` or online DNS checker
- [ ] Both values appear in the DNS query results

If all boxes are checked: ✅ You're ready to verify!

---

## Common Questions

**Q: Why do both records need the same name?**  
A: Let's Encrypt always queries `_acme-challenge.yourdomain.com` for validation. It expects to find BOTH challenge values in that query response.

**Q: Won't the second record replace the first?**  
A: No! DNS supports multiple records with the same name. When queried, it returns ALL matching records.

**Q: My DNS provider won't let me add two records with the same name!**  
A: Most modern DNS providers support this. If yours doesn't, consider:
- Checking their documentation (it's often supported but not obvious)
- Using a different DNS provider for just the `_acme-challenge` subdomain
- Contacting their support to confirm

**Q: How long should I wait after adding records?**  
A: Typically 5-10 minutes, but it can vary:
- Cloudflare: 1-2 minutes
- Route53: 2-5 minutes
- Most others: 5-15 minutes
- TTL affects caching time

**Q: Can I delete the records after getting the certificate?**  
A: Yes! Once the certificate is issued, you can remove the `_acme-challenge` records. You'll need to add new ones when renewing (values will be different).

---

**Remember:** The key is TWO separate records, SAME name, DIFFERENT values! 🔑