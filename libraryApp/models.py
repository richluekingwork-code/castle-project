from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.text import slugify
import PyPDF2  # For preview generation
from io import BytesIO

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    is_student = models.BooleanField(default=False)  # For student-only access
    verified_at = models.DateTimeField(null=True, blank=True)  # Timestamp if verified (e.g., via email)

    def __str__(self):
        return f"Profile for {self.user.email}"

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

# Auto-create profile on user signup
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)  # Auto-generated
    description = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        indexes = [models.Index(fields=['slug'])]

class BookSet(models.Model):
    ACCESS_CHOICES = [
        ('free', 'Free'),
        ('paid', 'Paid'),
        ('students', 'Students Only'),
    ]

    title = models.CharField(max_length=200)
    author = models.CharField(max_length=100, default="Your Client's Name")  # Customize as needed
    cover_image = models.ImageField(upload_to='covers/', blank=True, null=True)
    description = models.TextField()
    categories = models.ManyToManyField(Category, related_name='book_sets')
    access_type = models.CharField(max_length=20, choices=ACCESS_CHOICES, default='paid')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    preview_pages = models.PositiveIntegerField(default=10)  # Pages to extract for preview
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['title', 'access_type'])]

class Volume(models.Model):
    book_set = models.ForeignKey(BookSet, on_delete=models.CASCADE, related_name='volumes')
    volume_number = models.PositiveIntegerField()
    title = models.CharField(max_length=200, blank=True)  # Optional per-volume title
    pdf_file = models.FileField(upload_to='volumes/')
    preview_pdf = models.FileField(upload_to='previews/', blank=True)  # Auto-generated

    def __str__(self):
        return f"{self.book_set.title} - Volume {self.volume_number}"

    class Meta:
        ordering = ['volume_number']
        unique_together = ['book_set', 'volume_number']  # Prevent duplicates

# Signal to auto-generate preview PDF on volume save
@receiver(post_save, sender=Volume)
def generate_preview_pdf(sender, instance, **kwargs):
    if instance.pdf_file and not instance.preview_pdf:
        try:
            # Read full PDF
            full_pdf = PyPDF2.PdfReader(instance.pdf_file.open())
            preview_writer = PyPDF2.PdfWriter()
            num_pages = min(instance.book_set.preview_pages, len(full_pdf.pages))
            
            # Add first N pages to preview
            for page_num in range(num_pages):
                preview_writer.add_page(full_pdf.pages[page_num])
            
            # Save to BytesIO and upload
            buffer = BytesIO()
            preview_writer.write(buffer)
            buffer.seek(0)
            instance.preview_pdf.save(f"preview_{instance.pdf_file.name}", buffer)
        except Exception as e:
            print(f"Error generating preview: {e}")  # Log in prod

class Purchase(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='purchases')
    book_set = models.ForeignKey(BookSet, on_delete=models.CASCADE, related_name='purchases')
    purchased_at = models.DateTimeField(auto_now_add=True)
    access_expires = models.DateTimeField(null=True, blank=True)  # e.g., for 1-year access

    def __str__(self):
        return f"{self.user.email} purchased {self.book_set.title}"

    class Meta:
        unique_together = ['user', 'book_set']  # One purchase per user/set
        indexes = [models.Index(fields=['purchased_at'])]

        