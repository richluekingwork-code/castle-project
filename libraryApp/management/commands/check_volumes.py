from django.core.management.base import BaseCommand
from libraryApp.models import Volume
import os
from django.conf import settings

class Command(BaseCommand):
    help = 'Check Volume records and their associated files'

    def handle(self, *args, **kwargs):
        volumes = Volume.objects.all()
        self.stdout.write(f"Found {volumes.count()} volumes")
        
        for volume in volumes:
            self.stdout.write(f"\nVolume {volume.id}: {volume}")
            
            # Check PDF file
            if volume.pdf_file:
                pdf_path = os.path.join(settings.MEDIA_ROOT, str(volume.pdf_file))
                if os.path.exists(pdf_path):
                    self.stdout.write(self.style.SUCCESS(f"PDF exists at {pdf_path}"))
                else:
                    self.stdout.write(self.style.ERROR(f"PDF missing at {pdf_path}"))
            else:
                self.stdout.write(self.style.WARNING("No PDF file assigned"))
            
            # Check preview PDF
            if volume.preview_pdf:
                preview_path = os.path.join(settings.MEDIA_ROOT, str(volume.preview_pdf))
                if os.path.exists(preview_path):
                    self.stdout.write(self.style.SUCCESS(f"Preview exists at {preview_path}"))
                else:
                    self.stdout.write(self.style.ERROR(f"Preview missing at {preview_path}"))
            else:
                self.stdout.write(self.style.WARNING("No preview PDF assigned"))