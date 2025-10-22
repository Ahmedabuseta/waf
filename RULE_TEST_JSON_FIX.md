# Rule Test JSON Parse Error Fix

## Issue

When clicking the "XSS" quick test payload button in the Rule Testing interface, users encountered a JavaScript error:

```
Error: JSON.parse: unexpected character at line 2 column 1 of the JSON data
```

This error occurred in the browser console and prevented the XSS test payload from being properly loaded into the form.

## Root Cause

The issue was in the `rule_test.html` template's JavaScript code. The problem had two parts:

### 1. Object vs String Assignment

The XSS payload was defined as a JavaScript object:

```javascript
xss: {
    url: "https://{{ site.host }}/comment",
    method: "POST",
    body: {"comment": `<script>alert(\'XSS\')</script>`}  // Object, not string
}
```

When the `loadPayload()` function loaded this payload, it directly assigned the object to the textarea:

```javascript
document.getElementById('testBody').value = payload.body;  // Assigns "[object Object]"
```

This caused the textarea to display `[object Object]` instead of proper JSON.

### 2. JSON Parsing Issue

When submitting the form, the code attempted to send the body value directly without proper handling:

```javascript
const testData = {
    body: body,  // Could be "[object Object]" or invalid JSON
    // ...
};
```

Then when `JSON.stringify(testData)` was called, it would create invalid JSON structure, causing the parse error.

## Solution

### Fix 1: Convert Object to JSON String in loadPayload()

Updated the `loadPayload()` function to properly serialize objects to JSON strings:

```javascript
function loadPayload(type) {
    const payload = payloads[type];
    document.getElementById('testUrl').value = payload.url;
    document.getElementById('testMethod').value = payload.method;
    
    // Convert body object to JSON string if it's an object
    const bodyValue = typeof payload.body === 'object' && payload.body !== null
        ? JSON.stringify(payload.body, null, 2)  // Pretty-print JSON
        : payload.body;
    document.getElementById('testBody').value = bodyValue;
}
```

Now when you click "XSS", the textarea shows:
```json
{
  "comment": "<script>alert('XSS')</script>"
}
```

### Fix 2: Parse JSON Body Before Sending

Updated the form submission handler to properly parse JSON strings:

```javascript
let body = document.getElementById('testBody').value;

// Try to parse body as JSON if it's not empty
let parsedBody = body;
if (body && body.trim()) {
    try {
        parsedBody = JSON.parse(body);
    } catch (e) {
        // If it's not valid JSON, use as string
        parsedBody = body;
    }
}

const testData = {
    url: url,
    path: path,
    method: method,
    params: params,
    body: parsedBody,  // Now properly parsed
    headers: {}
};
```

## Files Modified

- `waf_app/templates/site_management/rule_test.html`
  - Updated `loadPayload()` function to serialize objects to JSON strings
  - Updated form submit handler to parse JSON strings before sending

## Testing

After the fix, all quick test payloads work correctly:

1. **SQL Injection** - URL parameter with SQL injection attempt
2. **XSS** - POST body with script tag (now properly formatted as JSON)
3. **Path Traversal** - URL parameter with path traversal attempt
4. **Command Injection** - URL parameter with command injection attempt

### Test Steps

1. Navigate to Rule Testing page for any site
2. Click "XSS" button
3. Verify the Request Body textarea shows properly formatted JSON:
   ```json
   {
     "comment": "<script>alert('XSS')</script>"
   }
   ```
4. Click "Test Request"
5. Verify no JavaScript errors in console
6. Verify results are displayed correctly (blocked or allowed)

## Benefits

1. **User Experience**: No more confusing error messages
2. **Data Integrity**: Request bodies are properly formatted and parsed
3. **Flexibility**: Supports both JSON objects and plain strings in request body
4. **Error Handling**: Gracefully handles invalid JSON by falling back to string

## Related Code

### Payload Definitions

The payloads object defines test cases:

```javascript
const payloads = {
    sqli: {
        url: "https://{{ site.host }}/search?q=1' OR '1'='1",
        method: "GET",
        body: ""
    },
    xss: {
        url: "https://{{ site.host }}/comment",
        method: "POST",
        body: {"comment": `<script>alert(\'XSS\')</script>`}
    },
    path: {
        url: "https://{{ site.host }}/files?path=../../etc/passwd",
        method: "GET",
        body: ""
    },
    cmd: {
        url: "https://{{ site.host }}/ping?host=127.0.0.1;ls -la",
        method: "GET",
        body: ""
    }
};
```

### API Endpoint

The test data is sent to:
```
POST /sites/{{ site.slug }}/rules/test/
```

With JSON payload:
```json
{
    "url": "https://example.com/comment",
    "path": "/comment",
    "method": "POST",
    "params": {},
    "body": {
        "comment": "<script>alert('XSS')</script>"
    },
    "headers": {}
}
```

## Prevention

To prevent similar issues in the future:

1. **Type Checking**: Always check if a value is an object before assigning to form fields
2. **JSON Validation**: Parse and validate JSON before sending to API
3. **Error Handling**: Implement try-catch blocks for JSON operations
4. **Testing**: Test all quick payload buttons, not just the first one

## Conclusion

This fix ensures that the Rule Testing interface properly handles JavaScript objects in payload definitions and correctly serializes them to JSON for both display and API submission. Users can now test all payload types without encountering JSON parsing errors.