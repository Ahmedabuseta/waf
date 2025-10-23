# Database Management Guide

## ⚠️ Important: Database and Git

Your SQLite database (`db.sqlite3`) should **NOT** be tracked in Git because:

1. **Binary file conflicts** - Causes merge conflicts that can't be resolved
2. **Data privacy** - Contains sensitive user data and credentials
3. **Environment-specific** - Each developer/server should have their own database
4. **File size** - Grows large over time, bloating your Git repository

## ✅ Solution: Use Fixtures for Data Backup

We've set up a fixture-based backup system that lets you:
- Save your important data to JSON files
- Version control the data structure (not the binary database)
- Restore data easily on any environment

---

## Quick Start

### 1. Create Your First Backup

Before removing the database from Git, backup your current data:

```bash
python backup_restore_db.py initial
```

This creates `fixtures/initial_backup.json` with all your current data.

### 2. Remove Database from Git

The database has already been removed from Git tracking:

```bash
# Already done:
git rm --cached db.sqlite3
```

### 3. Commit the Changes

```bash
git add .gitignore fixtures/
git commit -m "Remove database from Git, add fixture backup system"
git push
```

---

## Daily Usage

### Create a Backup

**Backup everything:**
```bash
python backup_restore_db.py backup
```

**Backup specific apps:**
```bash
python backup_restore_db.py backup --apps site_management
```

**Custom filename:**
```bash
python backup_restore_db.py backup --file my_backup.json
```

### Restore from Backup

**Restore latest backup:**
```bash
python backup_restore_db.py restore
```

**Restore specific backup:**
```bash
python backup_restore_db.py restore --file fixtures/backup_20240115_143022.json
```

### List All Backups

```bash
python backup_restore_db.py list
```

---

## Common Scenarios

### Scenario 1: Fresh Clone on New Machine

When you clone the repository on a new machine:

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd base-waf

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run migrations
python manage.py migrate

# 4. Restore from backup
python backup_restore_db.py restore --file fixtures/initial_backup.json

# 5. Create superuser (if needed)
python manage.py createsuperuser
```

### Scenario 2: After Git Pull

After pulling changes that modified the database schema:

```bash
# 1. Backup current data (optional but recommended)
python backup_restore_db.py backup

# 2. Pull changes
git pull

# 3. Run migrations
python manage.py migrate

# 4. Your data should still be intact in db.sqlite3
```

### Scenario 3: Sharing Data with Team

To share your current Sites and Addresses configuration:

```bash
# 1. Create a backup
python backup_restore_db.py backup --file fixtures/team_config.json

# 2. Commit the fixture
git add fixtures/team_config.json
git commit -m "Add team configuration"
git push

# 3. Team members can restore:
python backup_restore_db.py restore --file fixtures/team_config.json
```

### Scenario 4: Database Corrupted

If your database gets corrupted:

```bash
# 1. Delete corrupted database
rm db.sqlite3

# 2. Recreate database
python manage.py migrate

# 3. Restore from backup
python backup_restore_db.py restore

# 4. Done!
```

---

## Best Practices

### 1. Regular Backups

Create backups before:
- Major configuration changes
- Deploying to production
- Database schema migrations
- Sharing your setup with team

```bash
# Quick backup
python backup_restore_db.py backup
```

### 2. Keep Important Fixtures in Git

Store these in `fixtures/` and commit them:
- ✅ `initial_backup.json` - Your initial configuration
- ✅ `production_config.json` - Production-ready configuration
- ✅ `test_data.json` - Test data for development
- ❌ Don't commit: Daily automatic backups (too many files)

### 3. Use Descriptive Names

```bash
# Good
python backup_restore_db.py backup --file fixtures/before_ssl_migration.json
python backup_restore_db.py backup --file fixtures/production_2024_01.json

# Not so good
python backup_restore_db.py backup --file fixtures/backup1.json
```

### 4. Clean Old Backups

Periodically remove old automatic backups:

```bash
# Keep only last 10 backups
cd fixtures/
ls -t backup_*.json | tail -n +11 | xargs rm
```

---

## Using Django Management Commands

You can also use Django's built-in commands:

### Export Data (Backup)

```bash
# All apps
python manage.py dumpdata --indent=2 --output=fixtures/backup.json

# Specific app
python manage.py dumpdata site_management --indent=2 --output=fixtures/sites.json

# Exclude certain tables
python manage.py dumpdata --indent=2 --exclude=contenttypes --exclude=auth.permission --output=fixtures/backup.json
```

### Import Data (Restore)

```bash
# Load a fixture
python manage.py loaddata fixtures/backup.json

# Load multiple fixtures
python manage.py loaddata fixtures/sites.json fixtures/addresses.json
```

---

## Production Deployment

### Option 1: Use Fixtures (Small Sites)

For small sites with minimal data:

```bash
# On production server
python manage.py migrate
python backup_restore_db.py restore --file fixtures/production_config.json
```

### Option 2: Use PostgreSQL (Recommended)

For production, switch to PostgreSQL:

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'waf_db',
        'USER': 'waf_user',
        'PASSWORD': 'secure_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

Then migrate data:

```bash
# 1. Export from SQLite
python manage.py dumpdata --indent=2 --output=fixtures/migrate_to_postgres.json

# 2. Update settings.py to use PostgreSQL

# 3. Create PostgreSQL database
createdb waf_db

# 4. Run migrations
python manage.py migrate

# 5. Import data
python manage.py loaddata fixtures/migrate_to_postgres.json
```

---

## Automated Backups (Optional)

### Using Cron (Linux/Mac)

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * cd /path/to/base-waf && /path/to/venv/bin/python backup_restore_db.py backup
```

### Using Task Scheduler (Windows)

Create a batch file `backup.bat`:

```batch
@echo off
cd C:\path\to\base-waf
C:\path\to\venv\Scripts\python.exe backup_restore_db.py backup
```

Schedule it in Task Scheduler to run daily.

---

## Troubleshooting

### "No module named 'django'"

Make sure you're in the correct directory and virtual environment:

```bash
cd base-waf
source venv/bin/activate  # or: venv\Scripts\activate on Windows
python backup_restore_db.py backup
```

### "Backup file not found"

Check the fixtures directory:

```bash
ls -la fixtures/
python backup_restore_db.py list
```

### "IntegrityError" during restore

This usually means data already exists. You have two options:

1. **Clear database first:**
```bash
rm db.sqlite3
python manage.py migrate
python backup_restore_db.py restore
```

2. **Restore only specific data:**
```bash
# Edit the fixture file and remove duplicate entries
```

### Database gets recreated in Git

Make sure `.gitignore` is committed:

```bash
git add .gitignore
git commit -m "Add .gitignore"
git push
```

---

## File Structure

```
base-waf/
├── db.sqlite3              # ❌ NOT in Git (ignored)
├── .gitignore              # ✅ In Git (ignores db.sqlite3)
├── backup_restore_db.py    # ✅ In Git (backup utility)
├── DATABASE_MANAGEMENT.md  # ✅ In Git (this guide)
└── fixtures/               # ✅ In Git
    ├── initial_backup.json      # Your initial configuration
    ├── production_config.json   # Production-ready setup
    ├── test_data.json          # Test data
    └── backup_*.json           # Auto-generated (optional in Git)
```

---

## Summary

| Action | Command |
|--------|---------|
| Create backup | `python backup_restore_db.py backup` |
| Restore backup | `python backup_restore_db.py restore` |
| List backups | `python backup_restore_db.py list` |
| Initial setup | `python backup_restore_db.py initial` |
| After git pull | `python manage.py migrate` |
| Fresh clone | `python manage.py migrate && python backup_restore_db.py restore` |

---

## Need Help?

- Run `python backup_restore_db.py help` for usage
- Check Django docs: https://docs.djangoproject.com/en/stable/howto/initial-data/
- Check your backups: `python backup_restore_db.py list`

---

**Remember:** Your `db.sqlite3` is now in `.gitignore` and won't be tracked by Git. Always use fixtures to share data!