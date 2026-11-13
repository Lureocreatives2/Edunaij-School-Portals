import os
import shutil
import zipfile
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Creates a compressed backup of the database.'

    def handle(self, *args, **options):
        db_settings = settings.DATABASES['default']
        db_engine = db_settings['ENGINE']
        
        # Create backups directory if it doesn't exist
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if 'sqlite3' in db_engine:
            db_path = db_settings['NAME']
            if not os.path.exists(db_path):
                self.stdout.write(self.style.ERROR(f'Database file not found at {db_path}'))
                return
                
            zip_filename = f'db_backup_sqlite_{timestamp}.zip'
            zip_path = os.path.join(backup_dir, zip_filename)
            
            try:
                # Create a zip file containing the database
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write(db_path, os.path.basename(db_path))
                
                self.stdout.write(self.style.SUCCESS(f'✅ Successfully backed up SQLite database to: {zip_path}'))
                logger.info(f'Database backup created: {zip_path}')
                
                # Optional: Clean up backups older than 30 days
                self.cleanup_old_backups(backup_dir)
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Failed to create backup: {e}'))
                logger.error(f'Database backup failed: {e}')
        else:
            self.stdout.write(self.style.WARNING('⚠️ Non-SQLite database detected. Please configure pg_dump/mysqldump logic for this engine.'))

    def cleanup_old_backups(self, backup_dir, days=30):
        """Deletes backup files older than the specified number of days."""
        now = datetime.now()
        deleted_count = 0
        for filename in os.listdir(backup_dir):
            filepath = os.path.join(backup_dir, filename)
            if os.path.isfile(filepath):
                file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                if (now - file_mtime).days > days:
                    os.remove(filepath)
                    deleted_count += 1
        
        if deleted_count > 0:
            self.stdout.write(self.style.SUCCESS(f'🧹 Cleaned up {deleted_count} old backup(s).'))
