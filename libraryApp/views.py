from django.utils import timezone
from django.http import HttpResponse
from django.views import View
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from django.db.models import Q
from django.conf import settings
from .models import BookSet, Volume, Purchase, Category
from .forms import SearchForm, CheckoutForm
import stripe
import zipfile
from io import BytesIO
from django.http import HttpResponse


class Home(View):
    def get(self, request):
        return HttpResponse("Hello, this is the Home view for testing.")


class LibraryListView(ListView):
    model = BookSet
    template_name = 'libraryApp/list.html'  # Grid like Leanpub storefront
    context_object_name = 'books'
    paginate_by = 12  # Modern pagination

    def get_queryset(self):
        queryset = BookSet.objects.all()
        query = self.request.GET.get('q')
        category = self.request.GET.get('category')
        access_type = self.request.GET.get('access')
        if query:
            queryset = queryset.filter(Q(title__icontains=query) | Q(description__icontains=query))
        if category:
            queryset = queryset.filter(categories__slug=category)
        if access_type:
            queryset = queryset.filter(access_type=access_type)
        return queryset.distinct().order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()  # For filters
        context['search_form'] = SearchForm(self.request.GET)
        context['access_types'] = [('free', 'Free'), ('paid', 'Paid'), ('students', 'Students Only')]
        return context

class BookDetailView(DetailView):
    model = BookSet
    template_name = 'libraryApp/details.html'  # Leanpub-style: hero, desc, TOC, preview
    context_object_name = 'book'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book = context['book']
        context['volumes'] = book.volumes.all()  # TOC-like list
        #context['is_purchased'] = self.request.user.is_authenticated and Purchase.objects.filter(user=self.user, book_set=book).exists()
        context['preview_volumes'] = book.volumes.filter(preview_pdf__isnull=False)[:2]  # First 2 for teaser
        #context['stripe_key'] = settings.STRIPE_PUBLISHABLE_KEY
        context['feedback_url'] = f"mailto:{book.author}@example.com"  # Like Leanpub email
        return context

@login_required
def dashboard(request):
    # Post-purchase access: List bought books, downloads
    purchases = Purchase.objects.filter(user=request.user, access_expires__gte=timezone.now()).select_related('book_set')
    context = {'purchases': purchases}
    return render(request, 'libraryApp/dashboard.html', context)

def checkout(request, book_id):
    book = get_object_or_404(BookSet, id=book_id, access_type='paid')
    if book.price == 0:
        messages.warning(request, 'This book is free!')
        return redirect('book_detail', pk=book.id)

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{
                        'price_data': {
                            'currency': 'usd',
                            'product_data': {'name': book.title},
                            'unit_amount': int(book.price * 100),
                        },
                        'quantity': 1,
                    }],
                    mode='payment',
                    success_url=request.build_absolute_uri(reverse('dashboard')),
                    cancel_url=request.build_absolute_uri(reverse('book_detail', args=[book.id])),
                    metadata={'book_id': book.id, 'user_email': request.user.email if request.user.is_authenticated else ''},
                )
                # Create pending purchase or handle in webhook
                return redirect(session.url, code=303)
            except stripe.error.StripeError as e:
                messages.error(request, f'Payment error: {str(e)}')
    else:
        form = CheckoutForm()

    return render(request, 'libraryApp/checkout.html', {'book': book, 'form': form})

@login_required
def download_set(request, book_id):
    book = get_object_or_404(BookSet, id=book_id)
    if not Purchase.objects.filter(user=request.user, book_set=book).exists():
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    # Create ZIP of all volumes
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for volume in book.volumes.all():
            if volume.pdf_file:
                zip_file.write(volume.pdf_file.path, f"{book.title}_Vol{volume.volume_number}.pdf")

    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename={book.slug}.zip'
    return response

def preview_volume(request, volume_id):
    # AJAX for modal preview (like Leanpub reader)
    print(f"Received preview request for volume_id: {volume_id}")  # Debug log
    
    volume = get_object_or_404(Volume, id=volume_id)
    print(f"Found volume: {volume}")  # Debug log
    
    try:
        if request.user.is_authenticated and Purchase.objects.filter(user=request.user, book_set=volume.book_set).exists():
            if not volume.pdf_file:
                print("Full PDF file is missing")  # Debug log
                return JsonResponse({'error': 'Full PDF file is missing.'}, status=404)
            pdf_path = volume.pdf_file.url
            print(f"Using full PDF: {pdf_path}")  # Debug log
        else:
            if not volume.preview_pdf:
                print("No preview PDF, attempting to generate")  # Debug log
                # Try to regenerate the preview
                try:
                    import PyPDF2
                    from io import BytesIO
                    
                    # Read full PDF
                    print(f"Opening PDF file: {volume.pdf_file.path}")  # Debug log
                    full_pdf = PyPDF2.PdfReader(volume.pdf_file.open())
                    preview_writer = PyPDF2.PdfWriter()
                    num_pages = min(volume.book_set.preview_pages, len(full_pdf.pages))
                    print(f"Generating preview with {num_pages} pages")  # Debug log
                    
                    # Add first N pages to preview
                    for page_num in range(num_pages):
                        preview_writer.add_page(full_pdf.pages[page_num])
                    
                    # Save to BytesIO and upload
                    buffer = BytesIO()
                    preview_writer.write(buffer)
                    buffer.seek(0)
                    
                    preview_name = f"preview_{volume.pdf_file.name}"
                    print(f"Saving preview as: {preview_name}")  # Debug log
                    volume.preview_pdf.save(preview_name, buffer, save=True)
                    print("Preview generated successfully")  # Debug log
                except Exception as e:
                    print(f"Error generating preview: {e}")  # Debug log
                    return JsonResponse({'error': f'Error generating preview: {str(e)}'}, status=500)
            
            pdf_path = volume.preview_pdf.url if volume.preview_pdf else None
            print(f"Using preview PDF: {pdf_path}")  # Debug log

        if not pdf_path:
            print("No PDF path available")  # Debug log
            return JsonResponse({'error': 'No preview available.'}, status=404)

        # Verify file exists on disk
        import os
        from django.conf import settings
        
        file_path = os.path.join(settings.MEDIA_ROOT, pdf_path.replace(settings.MEDIA_URL, '').lstrip('/'))
        print(f"Checking file existence at: {file_path}")  # Debug log
        
        if not os.path.exists(file_path):
            print(f"File not found on disk: {file_path}")  # Debug log
            return JsonResponse({'error': 'PDF file not found on disk.'}, status=404)

        print(f"Returning PDF URL: {pdf_path}")  # Debug log
        return JsonResponse({'pdf_url': pdf_path})

    except Exception as e:
        print(f"Unexpected error: {e}")  # Debug log
        return JsonResponse({'error': f'Error accessing PDF: {str(e)}'}, status=500)

