# Intel DNS Management

Manage DNS records within Intel network using Men&Mice and DDI portal.

## Overview

This skill provides guidance for creating, updating, and verifying DNS records in the Intel network infrastructure. It covers both Men&Mice portal and DDI portal workflows, with specific focus on CNAME record management for Intel domains.

## Prerequisites

- Access to Intel Men&Mice portal
- Access to Intel DDI portal (fallback)
- VPN connection to Intel network
- Command-line access with `nslookup` or `dig`

## Usage

### Check DNS Propagation

```bash
# Check if DNS record has propagated
nslookup <domain>

# Example
nslookup ocode.intel.com
```

### Expected Output
```
Server:  UnKnown
Address:  <DNS-server-IP>

Non-authoritative answer:
Name:    apps1-fm-int.icloud.intel.com
Address:  10.64.22.120
Aliases:  ocode.intel.com
```

## Creating DNS Records

### Method 1: Men&Mice Portal (Primary)

1. Navigate to Men&Mice portal
2. Select "DNS" → "Zones"
3. Find the appropriate Intel zone (e.g., `intel.com`)
4. Click "Add Record"
5. Fill in record details:
   - **Name**: Your subdomain (e.g., `ocode`)
   - **Type**: CNAME
   - **Target**: `apps1-fm-int.icloud.intel.com.` ⚠️ **Include trailing dot!**
   - **TTL**: Default (or 300 seconds)
6. Save and submit

### Method 2: DDI Portal (Fallback)

Use DDI portal when Men&Mice times out or is unavailable:

1. Navigate to DDI portal
2. Follow similar workflow as Men&Mice
3. Ensure trailing dot on CNAME targets

## CNAME Target Format

### ✅ Correct Format
```
apps1-fm-int.icloud.intel.com.
```
**Note the trailing dot (`.`) - this is critical!**

### ❌ Incorrect Format
```
apps1-fm-int.icloud.intel.com    # Missing trailing dot
inlc4596.iind.intel.com          # Wrong target
10.64.22.120                     # IP instead of CNAME
```

## Common Targets

| Target | Purpose |
|--------|---------|
| `apps1-fm-int.icloud.intel.com.` | Intel CAAS load balancer |
| `inlc4596.iind.intel.com.` | Specific server (avoid for load-balanced apps) |

## Verification Steps

1. **Immediate check** (may not work yet):
   ```bash
   nslookup ocode.intel.com
   ```

2. **Wait for propagation**: DNS changes can take 5-15 minutes

3. **Verify CNAME chain**:
   ```bash
   nslookup ocode.intel.com
   # Should show:
   # ocode.intel.com → apps1-fm-int.icloud.intel.com → 10.64.22.120
   ```

4. **Test from application**:
   ```bash
   curl -I http://ocode.intel.com
   ```

## Troubleshooting

### Issue: DNS not resolving

**Symptoms:**
```
*** UnKnown can't find ocode.intel.com: Non-existent domain
```

**Solutions:**
1. Wait 5-15 minutes for propagation
2. Clear DNS cache: `ipconfig /flushdns` (Windows) or `sudo systemd-resolve --flush-caches` (Linux)
3. Verify record was created in portal
4. Check if you're on Intel VPN

### Issue: Wrong IP returned

**Symptoms:**
```
Name:    inlc4596.iind.intel.com
Address:  10.45.xxx.xxx    # Wrong IP
```

**Solutions:**
1. Verify CNAME target is `apps1-fm-int.icloud.intel.com.` (with trailing dot)
2. Update the record in Men&Mice/DDI portal
3. Wait for propagation

### Issue: Men&Mice portal timeout

**Symptoms:**
- Portal hangs or times out during record creation
- "Request timeout" errors

**Solutions:**
1. Use DDI portal as fallback
2. Try again during off-peak hours
3. Contact Intel network team if persistent

## Common Missteps to Avoid

### 1. ⚠️ Forgetting Trailing Dot

**Problem**: CNAME target without trailing dot may be treated as relative domain

```yaml
# ❌ Wrong
Target: apps1-fm-int.icloud.intel.com

# ✅ Correct
Target: apps1-fm-int.icloud.intel.com.
```

### 2. ⚠️ Using Wrong Target

**Problem**: Using specific server instead of load balancer

```yaml
# ❌ Wrong (single server)
Target: inlc4596.iind.intel.com.

# ✅ Correct (load balancer)
Target: apps1-fm-int.icloud.intel.com.
```

### 3. ⚠️ Testing Before Propagation

**Problem**: Testing immediately after creating record

**Solution**: Wait 5-15 minutes for DNS propagation before testing

### 4. ⚠️ Not Verifying CNAME Chain

**Problem**: DNS resolves but to wrong IP

**Solution**: Always verify the full CNAME chain shows correct target

## Examples

### Example 1: Create DNS for ocode.intel.com

```bash
# Step 1: Create CNAME in Men&Mice portal
# Name: ocode
# Type: CNAME
# Target: apps1-fm-int.icloud.intel.com.

# Step 2: Wait for propagation (5-15 min)

# Step 3: Verify
nslookup ocode.intel.com

# Expected output:
# ocode.intel.com → apps1-fm-int.icloud.intel.com → 10.64.22.120
```

### Example 2: Create DNS for omnicode.intel.com

```bash
# If Men&Mice times out, use DDI portal
# Follow same CNAME creation steps
# Target: apps1-fm-int.icloud.intel.com.

# Verify after propagation
nslookup omnicode.intel.com
```

## Related Skills

- `skill_k8s` - Update Kubernetes ingress after DNS is created
- `skill_caas` - Container registry for applications behind DNS

## Notes

- Always include trailing dot (`.`) on CNAME targets
- DNS propagation typically takes 5-15 minutes
- Use Men&Mice portal as primary, DDI portal as fallback
- Verify the full CNAME chain, not just A record resolution
- Contact Intel network team for issues with portal access
