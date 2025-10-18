# Caddy UI Quick Start Guide 🚀

## Overview

This guide shows you how to use the new Caddy management UI in the WAF system. All features are accessible through an intuitive, modern web interface.

---

## 🎯 Quick Navigation

### Main Caddy Dashboard
**URL:** `/caddy/status/`  
**Menu:** Click "Caddy" in the navigation bar

### Site-Specific Caddy Features
**URL:** `/sites/<your-site>/`  
**Menu:** Sites → Select your site

---

## 📊 Dashboard Features

### 1. Caddy Status Dashboard

Access from: **Navigation Menu → Caddy**

```
┌─────────────────────────────────────────────────────────────┐
│  Caddy Server Status                    [Refresh] [Validate]│
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────┐│
│  │ Connection  │ │ Managed     │ │ Active      │ │ Health ││
│  │ ✓ ONLINE    │ │ Sites: 5    │ │ Sites: 5    │ │ ✓ OK   ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └────────┘│
│                                                               │
│  ┌──────────────────────────┐  ┌─────────────────────────┐ │
│  │ Server Information       │  │ Quick Actions           │ │
│  │ • API: localhost:2019    │  │ [Sync All Sites]        │ │
│  │ • Status: CONNECTED      │  │ [Manage Sites]          │ │
│  │ • Servers: 5             │  │ [Validate Certificates] │ │
│  └──────────────────────────┘  │ [Cleanup Logs]          │ │
│                                 │ [Refresh Status]        │ │
│                                 └─────────────────────────┘ │
│                                                               │
│  Managed Sites in Caddy                                      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Host              Status    Type           Actions     │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ example.com      Active    Reverse Proxy  [Details]   │  │
│  │ api.example.com  Active    Reverse Proxy  [Details]   │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**What you can do:**
- ✅ View real-time connection status
- ✅ See all managed sites
- ✅ Sync all sites at once
- ✅ Validate SSL certificates
- ✅ Monitor server health

---

### 2. Site Detail - Caddy Section

Access from: **Sites → Select a site**

```
┌─────────────────────────────────────────────────────────────┐
│  example.com                                    [Edit] [Back]│
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  🔷 Caddy Reverse Proxy                                      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                 [Sync to Caddy] [SSL Status] [Config] │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │                                                         │  │
│  │  ✓ Sync Status        🔒 SSL Config        📊 Deploy  │  │
│  │  Ready to Sync        HTTPS + Auto SSL     Active     │  │
│  │                                                         │  │
│  │  ⚠️ Auto SSL Enabled                                   │  │
│  │  Caddy will automatically obtain certificates          │  │
│  │  from Let's Encrypt. Ensure DNS is configured.         │  │
│  │                                      [DNS Challenge →] │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  Configuration | Load Balancer | Addresses | Logs            │
└─────────────────────────────────────────────────────────────┘
```

**What you can do:**
- ✅ One-click sync to Caddy
- ✅ View SSL status
- ✅ Preview Caddy configuration
- ✅ Access DNS challenge manager
- ✅ Monitor deployment status

---

### 3. SSL Status Page

Access from: **Site Detail → SSL Status** or **Site Detail → Manage SSL**

```
┌─────────────────────────────────────────────────────────────┐
│  SSL/TLS Certificate Status - example.com      [Manage] [←] │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ SSL Mode     │  │ Protocol     │  │ Wildcard     │      │
│  │ 🛡️ Auto SSL  │  │ 🔒 HTTPS     │  │ ✨ Enabled   │      │
│  │ Let's Encrypt│  │ Encrypted    │  │ *.example.com│      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  📄 Certificate Information                        [VALID ✓] │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Common Name:   example.com                            │  │
│  │ Organization:  Let's Encrypt                          │  │
│  │ Issuer:        R3                                     │  │
│  │ Valid From:    2024-01-01                             │  │
│  │ Expires:       2024-04-01                             │  │
│  │ SANs:          [example.com] [www.example.com]        │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  ✅ Validation Status                                         │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ ✓ Certificate Valid                          [PASSED] │  │
│  │ ✓ Chain Valid                                [PASSED] │  │
│  │ ✓ Not Expired                                [PASSED] │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  Quick Actions:                                               │
│  [Toggle Auto SSL] [DNS Challenge] [Upload Cert] [Sync]      │
└─────────────────────────────────────────────────────────────┘
```

**What you can do:**
- ✅ View certificate details
- ✅ Check validation status
- ✅ Toggle Auto SSL on/off
- ✅ Configure DNS challenges
- ✅ Upload manual certificates
- ✅ Sync configuration to Caddy

---

### 4. Configuration Preview

Access from: **Site Detail → Caddy Config**

```
┌─────────────────────────────────────────────────────────────┐
│  Caddy Configuration Preview         [Copy] [Apply] [Back]  │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐                    │
│  │ Host │  │ Proto│  │ Auto │  │ Valid│                    │
│  │ ✓    │  │ 🔒   │  │ SSL  │  │ ✓    │                    │
│  └──────┘  └──────┘  └──────┘  └──────┘                    │
│                                                               │
│  [JSON Config] [Caddyfile] [Info]                            │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                                            [Download]  │  │
│  │  {                                         [Copy]     │  │
│  │    "apps": {                                          │  │
│  │      "http": {                                        │  │
│  │        "servers": {                                   │  │
│  │          "example_com": {                             │  │
│  │            "listen": [":443"],                        │  │
│  │            "routes": [                                │  │
│  │              {                                        │  │
│  │                "match": [{                            │  │
│  │                  "host": ["example.com"]              │  │
│  │                }],                                    │  │
│  │                "handle": [...]                        │  │
│  │              }                                        │  │
│  │            ]                                          │  │
│  │          }                                            │  │
│  │        }                                              │  │
│  │      }                                                │  │
│  │    }                                                  │  │
│  │  }                                                    │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  💡 Helpful Tips                                              │
│  • Click tabs to switch between JSON and Caddyfile formats   │
│  • Use Copy button to copy configuration to clipboard        │
│  • Click Apply to deploy configuration to Caddy              │
└─────────────────────────────────────────────────────────────┘
```

**What you can do:**
- ✅ View JSON configuration
- ✅ View Caddyfile format
- ✅ Copy configuration
- ✅ Download configuration
- ✅ Apply to Caddy with one click
- ✅ View configuration details

---

## 🎬 Common Tasks

### Task 1: Deploy a Site to Caddy

**Step-by-step:**
1. Go to **Sites** → Select your site
2. Scroll to **Caddy Reverse Proxy** section
3. Click **[Sync to Caddy]** button
4. Wait for success message
5. Verify in Caddy Status dashboard

**Visual Flow:**
```
Sites List → Site Detail → Caddy Section → [Sync to Caddy] → ✓ Success
```

---

### Task 2: Enable Auto SSL

**Step-by-step:**
1. Go to **Sites** → Select your site
2. Click **[SSL Status]** button
3. Locate **Quick Actions** section
4. Click **[Toggle Auto SSL]**
5. Confirm the change
6. Click **[Sync to Caddy]** to apply

**Requirements:**
- ⚠️ DNS must point to your server
- ⚠️ Port 80 and 443 must be open
- ⚠️ Domain must be publicly accessible

---

### Task 3: View Configuration

**Step-by-step:**
1. Go to **Sites** → Select your site
2. Click **[Caddy Config]** button
3. Review the **JSON Config** tab
4. Switch to **Caddyfile** tab if needed
5. Use **[Copy]** to copy configuration
6. Use **[Download]** to save to file

**Pro Tip:** The configuration is automatically validated before display!

---

### Task 4: Monitor Caddy Status

**Step-by-step:**
1. Click **Caddy** in the main navigation
2. View the status cards at the top
3. Check **Server Information** panel
4. Review **Managed Sites** table
5. Click **[Refresh Status]** for latest info

**Status Indicators:**
- 🟢 Green = Connected/Active/Valid
- 🔴 Red = Disconnected/Error
- 🟡 Yellow = Warning
- 🔵 Blue = Info

---

### Task 5: Bulk Sync All Sites

**Step-by-step:**
1. Go to **Caddy Status** dashboard
2. Find **Quick Actions** panel
3. Click **[Sync All Sites]**
4. Confirm the action
5. Wait for completion message
6. Review results

**Use Case:** When you've updated multiple sites and want to deploy all changes at once.

---

## 🎨 UI Elements Guide

### Color Meanings

| Color | Meaning | Example |
|-------|---------|---------|
| 🟢 Green | Success, Active, Valid | "Connected", "Valid Certificate" |
| 🔴 Red | Error, Disconnected, Invalid | "Disconnected", "Certificate Expired" |
| 🟡 Yellow | Warning, Attention Needed | "Auto SSL Enabled - Check DNS" |
| 🔵 Blue | Information, Primary Action | "Sync to Caddy", "View Config" |
| 🟣 Purple | Advanced Feature | "Validate All Certificates" |
| ⚪ Gray | Neutral, Disabled | "Not configured", "Disabled" |

### Icon Guide

| Icon | Meaning |
|------|---------|
| ✓ | Success, Valid, Enabled |
| ✗ | Error, Invalid, Disabled |
| 🔒 | HTTPS, Secure, Encrypted |
| 🛡️ | SSL, Security, Protection |
| 🔄 | Sync, Refresh, Reload |
| ⚙️ | Settings, Configuration |
| 📊 | Status, Statistics, Dashboard |
| ⚠️ | Warning, Caution |
| 💡 | Tip, Information, Help |

---

## 💡 Pro Tips

### Tip 1: Quick Navigation
- Use browser back button to navigate between pages
- All pages have breadcrumb navigation
- Quick action buttons are context-aware

### Tip 2: Copy Configuration
- Click anywhere in the code block to focus
- Use browser's Ctrl+A → Ctrl+C as backup
- Download button saves with proper filename

### Tip 3: Monitor Real-time
- Refresh button updates all data
- Status cards show live information
- Connection status updates instantly

### Tip 4: Dark Mode
- Toggle in top-right corner
- Persists across sessions
- Works on all pages

### Tip 5: Mobile Friendly
- All pages are responsive
- Cards stack on mobile devices
- Actions remain accessible

---

## 🚨 Troubleshooting

### Issue: "Cannot connect to Caddy"

**Solution:**
1. Go to Caddy Status dashboard
2. Follow the setup instructions shown
3. Ensure Caddy is running: `sudo systemctl status caddy`
4. Check API is enabled in Caddyfile
5. Click **[Refresh Status]** after fixing

### Issue: "Sync Failed"

**Possible Causes:**
- Caddy not running
- Invalid configuration
- Missing SSL certificates (for manual SSL)
- DNS not configured (for Auto SSL)

**Solution:**
1. Check Caddy Status dashboard
2. Review SSL Status page
3. Fix any validation errors
4. Try sync again

### Issue: "Certificate Invalid"

**Solution:**
1. Go to **SSL Status** page
2. Review validation errors
3. For Auto SSL: Check DNS configuration
4. For Manual SSL: Upload valid certificates
5. Toggle Auto SSL if needed

---

## 📱 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl/Cmd + C | Copy configuration (when focused) |
| Tab | Navigate between buttons |
| Enter | Activate focused button |
| Esc | Close modals (if any) |

---

## 🔗 Related Pages

- [Caddy Integration Summary](./CADDY_INTEGRATION_SUMMARY.md)
- [SSL Configuration Guide](./SSL_CONFIGURATION_GUIDE.md)
- [Caddy UI Enhancements](./CADDY_UI_ENHANCEMENTS.md)

---

## 📞 Getting Help

### In-App Help
- Hover over icons for tooltips
- Look for 💡 info boxes on each page
- Check validation messages for guidance

### Documentation Links
Each page includes links to:
- Caddy official documentation
- API reference
- WAF-specific guides

### Setup Wizard
First-time users see a setup wizard on the Caddy Status page with:
- Step-by-step installation guide
- Configuration examples
- Verification steps

---

## ✨ Feature Highlights

### What Makes This UI Special

1. **Real-time Status** - Live updates without page refresh
2. **One-Click Actions** - Deploy with a single button click
3. **Visual Feedback** - Clear indicators for all states
4. **Smart Validation** - Automatic configuration validation
5. **Multiple Formats** - View config as JSON or Caddyfile
6. **Copy/Download** - Easy configuration export
7. **Contextual Help** - Guidance where you need it
8. **Mobile Ready** - Works on all devices
9. **Dark Mode** - Easy on the eyes
10. **Accessible** - Keyboard navigation and screen readers

---

## 🎯 Quick Reference Card

```
┌─────────────────────────────────────────────────┐
│         CADDY UI QUICK REFERENCE                │
├─────────────────────────────────────────────────┤
│                                                 │
│  📊 Dashboard:     /caddy/status/               │
│  🌐 Site Detail:   /sites/<slug>/               │
│  🔒 SSL Status:    /sites/<slug>/ssl/status/    │
│  ⚙️  Config View:   /sites/<slug>/caddy-config/ │
│                                                 │
│  QUICK ACTIONS:                                 │
│  • Sync Site:      Site Detail → [Sync]        │
│  • Sync All:       Dashboard → [Sync All]       │
│  • View SSL:       Site Detail → [SSL Status]   │
│  • View Config:    Site Detail → [Caddy Config] │
│                                                 │
│  STATUS COLORS:                                 │
│  🟢 Green = OK    🔴 Red = Error                │
│  🟡 Yellow = Warn 🔵 Blue = Info                │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

**Happy Managing! 🎉**

For questions or issues, refer to the full documentation or contact your system administrator.