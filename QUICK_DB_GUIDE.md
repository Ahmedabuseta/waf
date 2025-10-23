# Quick Database Management Guide

## 🚨 IMPORTANT: Database is NO LONGER in Git!

Your `db.sqlite3` file is now **ignored by Git** (added to `.gitignore`).

### Why?
- ✅ Prevents merge conflicts
- ✅ Keeps sensitive data out of version control
- ✅ Each environment has its own database
- ✅ No more data loss on push/pull!

---

## 📋 Quick Commands

### Backup Your Data
```bash
# Create a backup (do this regularly!)
python backup_restore_db.py backup
```

### Restore Your Data
```bash
# Restore from latest backup
python backup_restore_db.py restore

# Restore from specific backup
python backup_restore_db.py restore --file fixtures/initial_backup.json
```

### List All Backups
```bash
python backup_restore_db.py list
```

---

## 🔄 Common Workflows

### After Git Pull
```bash
git pull
python manage.py migrate  # Apply any new database changes
# Your data is still intact in db.sqlite3!
```

### Fresh Clone (New Machine/Server)
```bash
git clone <repo-url>
cd base-waf
pip install -r requirements.txt
python manage.py migrate
python backup_restore_db.py restore --file fixtures/initial_backup.json
python manage.py createsuperuser  # Create admin account
```

### Before Making Big Changes
```bash
# Always backup first!
python backup_restore_db.py backup
# Now make your changes...
```

### Share Your Configuration with Team
```bash
# 1. Create a backup
python backup_restore_db.py backup --file fixtures/team_setup.json

# 2. Commit and push the fixture
git add fixtures/team_setup.json
git commit -m "Add team configuration"
git push

# 3. Team members restore:
python backup_restore_db.py restore --file fixtures/team_setup.json
```

### Database Corrupted? Start Fresh
```bash
rm db.sqlite3
python manage.py migrate
python backup_restore_db.py restore
```

---

## 💡 Best Practices

1. **Backup before major changes**
   ```bash
   python backup_restore_db.py backup --file fixtures/before_migration.json
   ```

2. **Keep important fixtures in Git**
   - ✅ `fixtures/initial_backup.json` - Your base configuration
   - ✅ `fixtures/production_config.json` - Production setup
   - ❌ Don't commit daily auto-backups (too many files)

3. **Use descriptive filenames**
   ```bash
   python backup_restore_db.py backup --file fixtures/ssl_config_2024.json
   ```

4. **Never commit db.sqlite3**
   - It's already in `.gitignore`
   - If you see it in `git status`, something is wrong!

---

## ⚡ What Changed?

### Before (❌ Bad)
```
db.sqlite3 tracked in Git
↓
You push changes
↓
Someone pulls
↓
Their database gets overwritten
↓
Data loss! 😢
```

### Now (✅ Good)
```
db.sqlite3 ignored by Git (in .gitignore)
Fixtures stored in fixtures/ folder
↓
You push fixtures (JSON data)
↓
Team pulls and restores from fixture
↓
Everyone has their own database
↓
No data loss! 🎉
```

---

## 📁 File Structure

```
base-waf/
├── db.sqlite3                    # ❌ NOT in Git (your local database)
├── .gitignore                    # ✅ Ignores db.sqlite3
├── backup_restore_db.py          # ✅ Backup/restore tool
├── DATABASE_MANAGEMENT.md        # ✅ Full documentation
├── QUICK_DB_GUIDE.md            # ✅ This file
└── fixtures/                     # ✅ In Git
    ├── initial_backup.json      # Your initial setup
    └── backup_YYYYMMDD_HHMMSS.json  # Auto-generated backups
```

---

## 🆘 Troubleshooting

### "My Sites/Addresses disappeared after git pull!"
This should **no longer happen** because `db.sqlite3` is not tracked.
If it does happen, restore from backup:
```bash
python backup_restore_db.py restore
```

### "I accidentally deleted db.sqlite3"
No problem! Restore from backup:
```bash
python manage.py migrate
python backup_restore_db.py restore
```

### "No backup files found"
Create your first backup:
```bash
python backup_restore_db.py backup
```

### "Git still wants to track db.sqlite3"
Make sure `.gitignore` is committed:
```bash
git add .gitignore
git commit -m "Add .gitignore"
git push
```

---

## 📚 More Information

For detailed documentation, see: [DATABASE_MANAGEMENT.md](DATABASE_MANAGEMENT.md)

For backup script help:
```bash
python backup_restore_db.py help
```

---

## ✅ Checklist for New Team Members

- [ ] Clone the repository
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Run migrations: `python manage.py migrate`
- [ ] Restore initial data: `python backup_restore_db.py restore --file fixtures/initial_backup.json`
- [ ] Create superuser: `python manage.py createsuperuser`
- [ ] Start server: `python manage.py runserver`
- [ ] **Never commit db.sqlite3!**

---

**Remember:** 
- 💾 Backup regularly: `python backup_restore_db.py backup`
- 🔄 Restore when needed: `python backup_restore_db.py restore`
- 📋 List backups: `python backup_restore_db.py list`
- ❌ Never commit `db.sqlite3` to Git!