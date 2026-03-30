from django import forms
from .models import Business, BusinessCategory


class BusinessForm(forms.ModelForm):
    """Form for creating and editing business listings"""
    
    class Meta:
        model = Business
        fields = [
            'name', 'category', 'service', 'location', 'phone',
            'details', 'image', 'address', 'area', 'working_hours',
            'price_range_min', 'price_range_max'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Business Name'
            }),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'service': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Service Type (e.g., Plumber, Electrician, Tailor)'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City/Area'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Contact Number'
            }),
            'details': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe your services...'
            }),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Full Address'
            }),
            'area': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Local Area/Neighborhood'
            }),
            'working_hours': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 9 AM - 6 PM'
            }),
            'price_range_min': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Minimum Price'
            }),
            'price_range_max': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Maximum Price'
            }),
        }

