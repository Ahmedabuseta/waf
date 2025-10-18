# WAF Template Navigation - Visual Guide

## Overview
This guide shows the completed navigation flow from WAF Template list to detail view.

---

## 1. Template List Page (`/waf-templates/`)

```
┌─────────────────────────────────────────────────────────────────┐
│                         WAF Templates                           │
│  Manage reusable WAF configuration templates    [+ Add Template]│
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  │
│  │ Standard Web   │  │ High Security  │  │ Basic Protection│ │
│  │ [Basic]    ✏️ 🗑️│  │ [Advanced] ✏️ 🗑️│  │ [Basic]    ✏️ 🗑️│ │
│  │                │  │                │  │                │  │
│  │ Standard prot. │  │ Advanced rules │  │ Minimal rules  │  │
│  │ for web apps   │  │ for sensitive  │  │ for testing    │  │
│  │                │  │ data           │  │                │  │
│  ├────────────────┤  ├────────────────┤  ├────────────────┤  │
│  │ Sites: 5       │  │ Sites: 2       │  │ Sites: 0       │  │
│  │ [View Details] │  │ [View Details] │  │ [View Details] │  │
│  └────────────────┘  └────────────────┘  └────────────────┘  │
│       ↓ CLICK             ↓ CLICK             ↓ CLICK        │
└─────────────────────────────────────────────────────────────────┘
```

### User Actions:
- Click **template name** → Navigate to detail view
- Click **[View Details]** button → Navigate to detail view
- Click ✏️ → Edit template
- Click 🗑️ → Delete template (with confirmation)

---

## 2. Template Detail Page (`/waf-templates/<id>/`)

```
┌───────────────────────────────────────────────────────────────────┐
│  Standard Web Protection [Basic]         [Edit] [Back to List]   │
│  WAF Template Details                                             │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────┐  ┌─────────────────────┐       │
│  │  Template Information       │  │  Statistics         │       │
│  ├─────────────────────────────┤  ├─────────────────────┤       │
│  │ Name: Standard Web Protect. │  │                     │       │
│  │ Type: [Basic]               │  │         5           │       │
│  │ Description:                │  │   Sites Using       │       │
│  │   Standard protection for   │  │     Template        │       │
│  │   web applications with...  │  │                     │       │
│  │ Created: Oct 10, 2024       │  └─────────────────────┘       │
│  │ Updated: Oct 15, 2024       │                                │
│  └─────────────────────────────┘                                │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Sites Using This Template                    │  │
│  ├───────────────────────────────────────────────────────────┤  │
│  │ Host          │ Protocol │ Status  │ SSL  │ Sensitivity  │  │
│  ├───────────────┼──────────┼─────────┼──────┼──────────────┤  │
│  │ api.site.com  │ [HTTPS]  │[Active] │ Auto │ [Medium]     │  │
│  │ app.site.com  │ [HTTPS]  │[Active] │ Auto │ [High]       │  │
│  │ blog.site.com │ [HTTP]   │[Active] │Manual│ [Low]        │  │
│  │ dev.site.com  │ [HTTPS]  │[Testing]│ Auto │ [Low]        │  │
│  │ shop.site.com │ [HTTPS]  │[Active] │ Auto │ [High]       │  │
│  └───────────────┴──────────┴─────────┴──────┴──────────────┘  │
│                      Each row has [View Site] link →            │
│                                                                   │
│  ℹ️  About Basic Templates:                                      │
│     Basic templates provide standard WAF protection suitable    │
│     for most applications...                                    │
│                                                                   │
│  ⚠️  Danger Zone                                                 │
│     Deleting this template is irreversible...                   │
│     [Delete Template]                                           │
└───────────────────────────────────────────────────────────────────┘
```

### User Actions:
- Click **[Edit]** → Navigate to edit form
- Click **[Back to List]** → Return to template list
- Click **[View Site]** on any row → Navigate to site detail page
- Click **[Delete Template]** → Delete (with confirmation)

---

## 3. Navigation Flow Diagram

```
                    ┌─────────────────────┐
                    │   Template List     │
                    │  /waf-templates/    │
                    └──────────┬──────────┘
                               │
                 ┌─────────────┼─────────────┐
                 │             │             │
         Click Name     Click Button    Click Edit
                 │             │             │
                 └─────────┬───┴─────────────┘
                           │
                           ▼
                 ┌─────────────────────┐
                 │  Template Detail    │ ◄───────┐
                 │ /waf-templates/<id>/│         │
                 └──────────┬──────────┘         │
                            │                     │
              ┌─────────────┼──────────┐         │
              │             │          │         │
        Click Edit    Click Site   Click Back   │
              │             │          │         │
              ▼             ▼          └─────────┘
    ┌─────────────┐  ┌─────────────┐
    │ Edit Form   │  │ Site Detail │
    │/templates/  │  │ /sites/...  │
    │  <id>/edit/ │  └─────────────┘
    └─────────────┘
```

---

## 4. URL Structure

```
Base URL: /waf-templates/

├── /                           → List all templates
├── /add/                       → Add new template (form)
├── /<id>/                      → View template details ⭐ NEW
├── /<id>/edit/                 → Edit template (form)
└── /<id>/delete/               → Delete template (POST only)
```

---

## 5. Key Features

### ✅ List Page Enhancements
- **Clickable Template Names**: Hover effect, clear visual feedback
- **View Details Button**: Prominent call-to-action on each card
- **Consistent Actions**: Edit and delete icons remain in top-right

### ✅ Detail Page Features
- **Complete Information**: All template metadata displayed
- **Sites Table**: Full list with status indicators and badges
- **Quick Navigation**: Links to edit, sites, and back to list
- **Statistics**: Visual count of sites using template
- **Empty States**: Helpful message when no sites use template
- **Danger Zone**: Clear warning for destructive actions
- **Contextual Help**: Info box explaining template types

### ✅ User Experience
- **Multiple Entry Points**: Click name or button
- **Breadcrumb-like Navigation**: Clear path back to list
- **Related Content**: Direct links to associated sites
- **Status Indicators**: Color-coded badges for quick scanning
- **Consistent Design**: Matches existing site management pages

---

## 6. Database Relationships

```
┌─────────────────┐
│   WafTemplate   │
│─────────────────│
│ • id            │
│ • name          │
│ • description   │◄────────┐
│ • template_type │         │
│ • created_at    │         │
│ • updated_at    │         │
└─────────────────┘         │
                             │
                    Foreign Key (Many-to-One)
                             │
                   ┌─────────────────┐
                   │      Site       │
                   │─────────────────│
                   │ • id            │
                   │ • host          │
                   │ • WafTemplate   ├──────┘
                   │ • protocol      │
                   │ • status        │
                   │ • ...           │
                   └─────────────────┘
```

The detail view uses: `template.sites.all()` (reverse foreign key)

---

## 7. Code Flow

### Request → Response Flow

```
1. User clicks link/button
   └─> URL: /waf-templates/123/

2. Django URL resolver
   └─> Matches: path('waf-templates/<int:template_id>/', ...)
   └─> Calls: views.waf_template_detail(request, template_id=123)

3. View function executes
   ├─> Fetches template: get_object_or_404(WafTemplate, id=123)
   ├─> Gets related sites: template.sites.all().order_by('host')
   ├─> Builds context: {template, sites, sites_count}
   └─> Renders: 'site_management/waf_template_detail.html'

4. Template renders
   ├─> Displays template info
   ├─> Shows statistics
   ├─> Lists sites in table
   └─> Provides action buttons

5. HTML response sent to browser
   └─> User sees detail page
```

---

## 8. Testing Scenarios

### Happy Path
1. ✓ Navigate to template list
2. ✓ Click template name
3. ✓ View detail page with all information
4. ✓ Click site link, navigate to site
5. ✓ Click back button, return to list

### Edge Cases
1. ✓ Template with no sites → Shows empty state
2. ✓ Template with many sites → Table scrolls properly
3. ✓ Invalid template ID → 404 error page
4. ✓ Dark mode → All elements properly styled

### Actions
1. ✓ Edit from detail page → Navigate to edit form
2. ✓ Delete from detail page → Confirm and redirect
3. ✓ View site from table → Navigate to site detail

---

## Summary

The WAF Template detail view completes the CRUD (Create, Read, Update, Delete) 
functionality for templates. Users now have a comprehensive way to:

- **Browse** templates in the list
- **View** complete details and relationships
- **Navigate** between templates and sites seamlessly
- **Manage** templates with clear action buttons

This implementation follows Django best practices and maintains consistency 
with the existing site management interface design.