# JSON Parse Fix Summary - Rule Test Template

## Problem Fixed ✅

**Error Message:**
```
Error: JSON.parse: unexpected character at line 2 column 1 of the JSON data
```

**When it occurred:** Clicking the "XSS" quick test button in the Rule Testing interface (`/sites/{slug}/rules/test/`)

## Root Cause

The XSS payload was defined as a JavaScript object:
```javascript
body: {"comment": `<script>alert('XSS')</script>`}  // Object
```

When loaded into the form textarea, it became `"[object Object]"` instead of proper JSON, causing parse errors when submitted.

## Solution

### Changed File
- `waf_app/templates/site_management/rule_test.html`

### Fix 1: Object to JSON Conversion
```javascript
// BEFORE (broken)
document.getElementById('testBody').value = payload.body;

// AFTER (fixed)
const bodyValue = typeof payload.body === 'object' && payload.body !== null
    ? JSON.stringify(payload.body, null, 2)
    : payload.body;
document.getElementById('testBody').value = bodyValue;
```

### Fix 2: JSON Parsing Before Submission
```javascript
// BEFORE (broken)
const body = document.getElementById('testBody').value;
const testData = { body: body, ... };

// AFTER (fixed)
let body = document.getElementById('testBody').value;
let parsedBody = body;
if (body && body.trim()) {
    try {
        parsedBody = JSON.parse(body);
    } catch (e) {
        parsedBody = body;  // Fallback to string
    }
}
const testData = { body: parsedBody, ... };
```

## Testing

### Test File Created
`test_rule_test_payloads.html` - Standalone test page with automated test suite

### Manual Test Steps
1. Go to any site's Rule Testing page
2. Click each quick test button (SQL Injection, XSS, Path Traversal, Command Injection)
3. Verify the Request Body textarea shows:
   - Empty string for GET requests
   - Properly formatted JSON for POST requests
4. Click "Test Request"
5. Verify no JavaScript errors in browser console
6. Verify results display correctly

### Expected Results
- ✅ No JavaScript errors
- ✅ XSS payload shows: `{"comment": "<script>alert('XSS')</script>"}`
- ✅ Request properly submitted to backend
- ✅ Results displayed (blocked/allowed)

## What Now Works

All quick test payloads load and submit correctly:

1. **SQL Injection** ✅ - URL with `1' OR '1'='1`
2. **XSS** ✅ - POST body with script tag (now properly JSON formatted)
3. **Path Traversal** ✅ - URL with `../../etc/passwd`
4. **Command Injection** ✅ - URL with `127.0.0.1;ls -la`

## Key Benefits

- 🎯 **User Experience**: No confusing error messages
- 📊 **Data Integrity**: Proper JSON formatting maintained
- 🔄 **Flexibility**: Handles both objects and plain strings
- 🛡️ **Error Handling**: Gracefully handles invalid JSON

## Related Fixes

This session also fixed:
- ✅ `acme.sh` PATH issue - Updated certificate manager to use full path `~/.acme.sh/acme.sh`
- ✅ `manage_certificates.py` corrupted line

## Documentation

- `RULE_TEST_JSON_FIX.md` - Detailed technical explanation
- `ACME_SH_PATH_FIX.md` - acme.sh path fix documentation
- `test_rule_test_payloads.html` - Interactive test suite