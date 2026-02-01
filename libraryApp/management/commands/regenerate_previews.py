from django.core.management.base import BaseCommand
from libraryApp.models import Volume
import os
from django.conf import settings

class Command(BaseCommand):
    help = 'Regenerate preview PDFs for all volumes'

    def handle(self, *args, **kwargs):
        volumes = Volume.objects.all()
        self.stdout.write(f"Found {volumes.count()} volumes")
        
        # Clear existing previews
        preview_dir = os.path.join(settings.MEDIA_ROOT, 'previews')
        if os.path.exists(preview_dir):
            for file in os.listdir(preview_dir):
                if file.endswith('.pdf'):
                    os.remove(os.path.join(preview_dir, file))
        
        for volume in volumes:
            self.stdout.write(f"\nRegenerating preview for Volume {volume.id}: {volume}")
            try:
                # Clear existing preview
                if volume.preview_pdf:
                    volume.preview_pdf.delete()
                
                # Force preview regeneration
                import PyPDF2
                from io import BytesIO
                
                # Read full PDF
                full_pdf = PyPDF2.PdfReader(volume.pdf_file.open())
                preview_writer = PyPDF2.PdfWriter()
                num_pages = min(volume.book_set.preview_pages, len(full_pdf.pages))
                
                # Add first N pages to preview
                for page_num in range(num_pages):
                    preview_writer.add_page(full_pdf.pages[page_num])
                
                # Save to BytesIO and upload
                buffer = BytesIO()
                preview_writer.write(buffer)
                buffer.seek(0)
                
                preview_name = f"preview_{os.path.basename(volume.pdf_file.name)}"
                volume.preview_pdf.save(preview_name, buffer, save=True)
                
                self.stdout.write(self.style.SUCCESS(f"Successfully regenerated preview as {preview_name}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error generating preview: {e}"))