from django import forms
from .models import BookSet

class SearchForm(forms.Form):
    query = forms.CharField(max_length=100, required=False, label='Search books')

class CheckoutForm(forms.Form):
    # Stripe handles card; this is for any extras like quantity (but single set for now)
    pass  # Expand if bundles