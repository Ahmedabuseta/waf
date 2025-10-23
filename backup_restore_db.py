#!/usr/bin/env python
"""
Database Backup and Restore Utility for WAF System

This script helps you backup and restore your database data using Django fixtures.
It prevents data loss when working with Git.

Usage:
    # Backup all data
    python backup_restore_db.py backup

    # Backup specific apps
    python backup_restore_db.py backup --apps site_management analytics

    # Restore from backup
    python backup_restore_db.py restore

    # Restore specific backup
    python backup_restore_db.py restore --file fixtures/backup_2024-01-15.json

    # List all backups
    python backup_restore_db.py list
"""

import os
import sys
import django
import json
from datetime import datetime
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'waf_app.settings')
django.setup()

from django.core.management import call_command
from django.core import serializers
from django.apps import apps


FIXTURES_DIR = Path(__file__).parent / 'fixtures'
FIXTURES_DIR.mkdir(exist_ok=True)


def backup_database(app_labels=None, filename=None):
    """
    Backup database to JSON fixture file

    Args:
        app_labels: List of app labels to backup (None = all apps)
        filename: Custom filename (None = auto-generate with timestamp)
    """
    print("=" * 80)
    print("DATABASE BACKUP")
    print("=" * 80)

    # Generate filename if not provided
    if not filename:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'backup_{timestamp}.json'

    filepath = FIXTURES_DIR / filename

    # Determine which apps to backup
    if app_labels:
        apps_to_backup = app_labels
    else:
        # Backup only project apps (exclude Django built-in apps)
        apps_to_backup = ['site_management', 'analytics']

    print(f"\n📦 Backing up apps: {', '.join(apps_to_backup)}")
    print(f"📁 Output file: {filepath}")

    try:
        # Collect all data
        all_objects = []
        for app_label in apps_to_backup:
            try:
                app_config = apps.get_app_config(app_label)
                models = app_config.get_models()

                for model in models:
                    model_name = model._meta.model_name
                    objects = model.objects.all()
                    count = objects.count()

                    if count > 0:
                        print(f"   ✓ {app_label}.{model_name}: {count} objects")
                        all_objects.extend(objects)
                    else:
                        print(f"   - {app_label}.{model_name}: 0 objects (skipped)")

            except LookupError:
                print(f"   ✗ App '{app_label}' not found")
                continue

        # Serialize all objects to JSON
        if all_objects:
            print(f"\n💾 Serializing {len(all_objects)} total objects...")

            with open(filepath, 'w', encoding='utf-8') as f:
                serializers.serialize(
                    'json',
                    all_objects,
                    indent=2,
                    use_natural_foreign_keys=True,
                    use_natural_primary_keys=False,
                    stream=f
                )

            file_size = filepath.stat().st_size / 1024  # KB
            print(f"✅ Backup successful!")
            print(f"   File size: {file_size:.2f} KB")
            print(f"   Location: {filepath}")
        else:
            print("\n⚠️  No data to backup!")

    except Exception as e:
        print(f"\n❌ Backup failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    print("=" * 80)
    return True


def restore_database(filename=None):
    """
    Restore database from JSON fixture file

    Args:
        filename: Backup file to restore (None = latest backup)
    """
    print("=" * 80)
    print("DATABASE RESTORE")
    print("=" * 80)

    # Find backup file
    if filename:
        filepath = Path(filename)
        if not filepath.is_absolute():
            filepath = FIXTURES_DIR / filename
    else:
        # Find latest backup
        backups = sorted(FIXTURES_DIR.glob('backup_*.json'), reverse=True)
        if not backups:
            print("\n❌ No backup files found!")
            print(f"   Looking in: {FIXTURES_DIR}")
            return False
        filepath = backups[0]

    if not filepath.exists():
        print(f"\n❌ Backup file not found: {filepath}")
        return False

    print(f"\n📁 Restoring from: {filepath}")
    file_size = filepath.stat().st_size / 1024  # KB
    print(f"   File size: {file_size:.2f} KB")

    # Confirm restoration
    print("\n⚠️  WARNING: This will overwrite existing data!")
    response = input("   Continue? (yes/no): ").strip().lower()

    if response not in ['yes', 'y']:
        print("\n❌ Restore cancelled")
        return False

    try:
        print(f"\n🔄 Restoring data...")

        # Load and restore data
        call_command('loaddata', str(filepath), verbosity=2)

        print(f"\n✅ Restore successful!")

    except Exception as e:
        print(f"\n❌ Restore failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    print("=" * 80)
    return True


def list_backups():
    """
    List all available backup files
    """
    print("=" * 80)
    print("AVAILABLE BACKUPS")
    print("=" * 80)

    backups = sorted(FIXTURES_DIR.glob('backup_*.json'), reverse=True)

    if not backups:
        print("\n⚠️  No backup files found")
        print(f"   Directory: {FIXTURES_DIR}")
        print("\nRun 'python backup_restore_db.py backup' to create a backup")
    else:
        print(f"\n📁 Backup directory: {FIXTURES_DIR}\n")

        for i, backup in enumerate(backups, 1):
            file_size = backup.stat().st_size / 1024  # KB
            modified = datetime.fromtimestamp(backup.stat().st_mtime)
            modified_str = modified.strftime('%Y-%m-%d %H:%M:%S')

            print(f"{i}. {backup.name}")
            print(f"   Size: {file_size:.2f} KB")
            print(f"   Modified: {modified_str}")
            print()

    print("=" * 80)
    return True


def create_initial_backup():
    """
    Create initial backup with essential data
    """
    print("=" * 80)
    print("CREATING INITIAL BACKUP")
    print("=" * 80)

    print("\nThis will create a backup of your current database state.")
    print("You should do this BEFORE removing db.sqlite3 from Git.\n")

    response = input("Continue? (yes/no): ").strip().lower()

    if response not in ['yes', 'y']:
        print("\n❌ Cancelled")
        return False

    return backup_database(filename='initial_backup.json')


def show_usage():
    """
    Display usage information
    """
    print(__doc__)


def main():
    """
    Main entry point
    """
    if len(sys.argv) < 2:
        show_usage()
        return

    command = sys.argv[1].lower()

    if command == 'backup':
        # Parse optional arguments
        apps = None
        filename = None

        if '--apps' in sys.argv:
            idx = sys.argv.index('--apps')
            apps = sys.argv[idx + 1:]
        elif '--file' in sys.argv:
            idx = sys.argv.index('--file')
            filename = sys.argv[idx + 1]

        backup_database(app_labels=apps, filename=filename)

    elif command == 'restore':
        # Parse optional arguments
        filename = None

        if '--file' in sys.argv:
            idx = sys.argv.index('--file')
            filename = sys.argv[idx + 1]

        restore_database(filename=filename)

    elif command == 'list':
        list_backups()

    elif command == 'initial':
        create_initial_backup()

    elif command == 'help':
        show_usage()

    else:
        print(f"❌ Unknown command: {command}")
        print("\nValid commands: backup, restore, list, initial, help")
        show_usage()


if __name__ == '__main__':
    main()
