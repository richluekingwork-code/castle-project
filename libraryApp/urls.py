from django.urls import path
from . import views
from django.contrib.auth import views as auth_views  # For login

urlpatterns = [
    # Browsing
    path('', views.Home.as_view(), name='home'),  # Temporary home view
    path('library_list', views.LibraryListView.as_view(), name='library_list'),
    path('search/', views.LibraryListView.as_view(), name='search'),  # Same view, ?q= param

    # Book details & preview
    path('book/<int:pk>/', views.BookDetailView.as_view(), name='book_detail'),
    path('preview/<int:volume_id>/', views.preview_volume, name='preview_volume'),  # AJAX

    # Purchase & Access
    path('checkout/<int:book_id>/', views.checkout, name='checkout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('download/<int:book_id>/', views.download_set, name='download_set'),

    # Auth (integrate with allauth)
    path('accounts/login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    # Add more allauth paths in main urls.py
]