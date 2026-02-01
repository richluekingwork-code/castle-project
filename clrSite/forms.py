# forms.py
from django import forms
from .models import *
class DonationForm(forms.ModelForm):
    class Meta:
        model = Donation
        fields = ['amount', 'donor_name', 'email', 'phone_number', 'payment_method']

class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'message']
        
        
        