# acme.sh Path Fix Summary

## Issue

When attempting to generate wildcard certificates, the system was failing with the error:
```
Failed to generate certificate: acme.sh is not installed or not available in PATH
```

This occurred even though `acme.sh` was properly installed in the user's home directory at `~/.acme.sh/`.

## Root Cause

The `CertificateManager` class in `site_management/utils/certificate_manager.py` was attempting to call `acme.sh` as a command directly (assuming it was in the system PATH):

```python
# Old code
result = subprocess.run(['acme.sh', '--version'], capture_output=True, timeout=5)
cmd = ['acme.sh', '--issue', '--dns', 'dns_manual']
```

However, `acme.sh` installs itself to `~/.acme.sh/acme.sh` by default and doesn't automatically add itself to the PATH. This caused the command to fail with a `FileNotFoundError`.

## Solution

Updated two methods in `CertificateManager` to use the full path to `acme.sh`:

### 1. `_check_acme_sh_available()` Method

**Before:**
```python
def _check_acme_sh_available(self) -> bool:
    """Check if acme.sh is available on the system"""
    try:
        result = subprocess.run(['acme.sh', '--version'], capture_output=True, timeout=5)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
```

**After:**
```python
def _check_acme_sh_available(self) -> bool:
    """Check if acme.sh is available on the system"""
    try:
        acme_sh_path = Path.home() / '.acme.sh' / 'acme.sh'
        if not acme_sh_path.exists():
            return False
        result = subprocess.run([str(acme_sh_path), '--version'], capture_output=True, timeout=5)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
```

### 2. `_build_acme_command()` Method

**Before:**
```python
def _build_acme_command(self, domain: str, wildcard_domain: str, email: str,
                      dns_provider: str, staging: bool) -> List[str]:
    """Build acme.sh command for wildcard certificate generation"""
    cmd = ['acme.sh', '--issue', '--dns', 'dns_manual']
    # ... rest of method
```

**After:**
```python
def _build_acme_command(self, domain: str, wildcard_domain: str, email: str,
                      dns_provider: str, staging: bool) -> List[str]:
    """Build acme.sh command for wildcard certificate generation"""
    acme_sh_path = str(Path.home() / '.acme.sh' / 'acme.sh')
    cmd = [acme_sh_path, '--issue', '--dns', 'dns_manual']
    # ... rest of method
```

## Changes Made

### Files Modified

1. **`site_management/utils/certificate_manager.py`**
   - Updated `_check_acme_sh_available()` to use full path `~/.acme.sh/acme.sh`
   - Updated `_build_acme_command()` to use full path `~/.acme.sh/acme.sh`

2. **`WILDCARD_CERTIFICATE_GUIDE.md`**
   - Updated installation instructions to clarify that acme.sh doesn't need to be in PATH
   - Updated troubleshooting section with better guidance

## Verification

The fix was verified by:

1. Checking that `acme.sh` exists at the expected location:
   ```bash
   $ ls -la ~/.acme.sh/acme.sh
   -rwxr-xr-x 1 override override 229821 Oct 22 23:47 /home/override/.acme.sh/acme.sh
   ```

2. Testing the full path works correctly:
   ```bash
   $ ~/.acme.sh/acme.sh --version
   https://github.com/acmesh-official/acme.sh
   v3.1.2
   ```

3. Verifying Python can call it:
   ```python
   from pathlib import Path
   import subprocess
   acme_sh_path = str(Path.home() / '.acme.sh' / 'acme.sh')
   result = subprocess.run([acme_sh_path, '--version'], capture_output=True, timeout=5)
   # Returns exit code 0 (success)
   ```

## Benefits

1. **No PATH modification needed**: Users don't need to modify their shell configuration
2. **Standard installation**: Works with the default `acme.sh` installation location
3. **More reliable**: Doesn't depend on environment PATH configuration
4. **Better error handling**: Explicitly checks if the file exists before attempting to run it

## Usage

After this fix, wildcard certificate generation works as expected:

```bash
# Generate wildcard certificate
python manage_certificates.py acme-wildcard example.com admin@example.com --dns-provider cloudflare

# With staging environment
python manage_certificates.py acme-wildcard example.com admin@example.com --staging

# Force renewal
python manage_certificates.py acme-wildcard example.com admin@example.com --force-renew
```

## Alternative Approaches Considered

1. **Add acme.sh to PATH**: Would require modifying shell configuration files
   - Rejected: Too intrusive and environment-dependent

2. **Symlink to /usr/local/bin**: Would require sudo permissions
   - Rejected: Not all users have admin access

3. **Use full path (chosen)**: Works with standard installation
   - Accepted: Clean, reliable, no special permissions needed

## Related Documentation

- `WILDCARD_CERTIFICATE_GUIDE.md` - Complete guide for wildcard certificate generation
- `site_management/utils/certificate_manager.py` - Main certificate management class
- [acme.sh GitHub](https://github.com/acmesh-official/acme.sh) - Official acme.sh documentation

## Testing Checklist

- [x] Verify `acme.sh` version check works
- [x] Verify wildcard certificate generation command builds correctly
- [x] Update documentation to reflect changes
- [x] Test that error message is clear when acme.sh is not installed

## Future Improvements

1. Add configuration option for custom acme.sh installation paths
2. Support multiple acme.sh installation locations (e.g., `/usr/local/bin/acme.sh`)
3. Add automatic acme.sh installation if not present
4. Better detection of acme.sh on different platforms

## Conclusion

This fix resolves the PATH issue with `acme.sh` by using the full installation path (`~/.acme.sh/acme.sh`) instead of relying on the command being in the system PATH. This makes the certificate manager more robust and easier to use with standard `acme.sh` installations.