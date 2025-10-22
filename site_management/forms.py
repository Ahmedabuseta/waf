"""
Forms for site management application
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Site, WafTemplate, Addresses, LoadBalancers
from .validators import SiteSSLValidator


class LoginForm(AuthenticationForm):
    """Custom login form with Tailwind styling"""
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white',
            'placeholder': 'Username',
            'required': True,
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white',
            'placeholder': 'Password',
            'required': True,
        })
    )


class SignUpForm(UserCreationForm):
    """Custom signup form with Tailwind styling"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white',
            'placeholder': 'Email',
        })
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white',
            'placeholder': 'Username',
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white',
            'placeholder': 'Password',
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white',
            'placeholder': 'Confirm Password',
        })


class SiteForm(forms.ModelForm):
    """
    Enhanced form for Site model with comprehensive SSL/TLS validation
    Validates certificates, ensures protocol consistency, and checks domain coverage
    """

    # Add optional fields for certificate upload
    ssl_certificate = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pem,.crt,.cer'}),
        help_text='Upload SSL certificate (PEM format)'
    )
    ssl_key = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pem,.key'}),
        help_text='Upload SSL private key (PEM format)'
    )
    ssl_chain = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pem,.crt,.cer'}),
        help_text='Upload SSL certificate chain (optional, PEM format)'
    )

    class Meta:
        model = Site
        fields = [
            'host', 'slug', 'protocol', 'auto_ssl', 'support_subdomains',
            'action_type', 'sensitivity_level', 'status', 'WafTemplate'
        ]
        widgets = {
            'host': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'example.com'
            }),
            'slug': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'auto-generated-from-host'
            }),
            'protocol': forms.Select(attrs={
                'class': 'form-control',
                'onchange': 'toggleSSLFields()'
            }),
            'auto_ssl': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'onchange': 'toggleManualCertFields()'
            }),
            'support_subdomains': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'onchange': 'checkSubdomainRequirements()'
            }),
            'action_type': forms.Select(attrs={'class': 'form-control'}),
            'sensitivity_level': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'WafTemplate': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ssl_validator = SiteSSLValidator()
        self.dns_challenge_info = None

        # Add helpful text for fields
        self.fields['host'].help_text = 'Domain or IP address of the site (e.g., example.com)'
        self.fields['slug'].help_text = 'URL-friendly identifier (auto-generated from host if left blank)'
        self.fields['protocol'].help_text = 'Select HTTP or HTTPS'
        self.fields['auto_ssl'].help_text = 'Enable automatic SSL certificate management via Let\'s Encrypt'
        self.fields['support_subdomains'].help_text = 'Enable wildcard certificate for subdomains (*.example.com)'

    def clean(self):
        """
        Comprehensive validation of SSL/TLS configuration
        Ensures protocol, certificates, and domain settings are consistent
        """
        cleaned_data = super().clean()

        protocol = cleaned_data.get('protocol')
        auto_ssl = cleaned_data.get('auto_ssl')
        support_subdomains = cleaned_data.get('support_subdomains')
        host = cleaned_data.get('host')

        ssl_certificate = self.files.get('ssl_certificate')
        ssl_key = self.files.get('ssl_key')
        ssl_chain = self.files.get('ssl_chain')

        # Validate complete SSL configuration
        is_valid, errors = self.ssl_validator.validate_site_ssl_configuration(
            protocol=protocol,
            auto_ssl=auto_ssl,
            support_subdomains=support_subdomains,
            host=host,
            ssl_certificate=ssl_certificate,
            ssl_key=ssl_key,
            ssl_chain=ssl_chain
        )

        if not is_valid:
            for error in errors:
                self.add_error(None, error)

        # Generate DNS challenge info if needed
        if protocol == 'https' and auto_ssl and support_subdomains:
            self.dns_challenge_info = self.ssl_validator.get_acme_dns_challenge(
                host, support_subdomains
            )

        return cleaned_data

    def save(self, commit=True):
        """
        Save site with SSL certificates if provided
        """
        instance = super().save(commit=False)

        # Handle certificate uploads
        if 'ssl_certificate' in self.files:
            instance.ssl_certificate = self.files['ssl_certificate']
        if 'ssl_key' in self.files:
            instance.ssl_key = self.files['ssl_key']
        if 'ssl_chain' in self.files:
            instance.ssl_chain = self.files['ssl_chain']

        if commit:
            instance.save()

        return instance

    def get_dns_challenge_info(self):
        """
        Get DNS challenge information for wildcard certificates
        Returns None if not applicable
        """
        return self.dns_challenge_info


class AddressForm(forms.ModelForm):
    """Form for Address model"""
    class Meta:
        model = Addresses
        fields = ['site', 'ip_address', 'port', 'is_allowed']
        widgets = {
            'site': forms.Select(attrs={'class': 'form-control'}),
            'ip_address': forms.TextInput(attrs={'class': 'form-control'}),
            'port': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_allowed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class LoadBalancerForm(forms.ModelForm):
    """Form for LoadBalancer model"""
    class Meta:
        model = LoadBalancers
        fields = ['site', 'algorithm', 'health_check_url']
        widgets = {
            'site': forms.Select(attrs={'class': 'form-control'}),
            'algorithm': forms.Select(attrs={'class': 'form-control'}),
            'health_check_url': forms.URLInput(attrs={'class': 'form-control'}),
        }

class WafTemplateForm(forms.ModelForm):
    """Form for WafTemplate model"""
    class Meta:
        model = WafTemplate
        fields = ['name', 'description', 'template_type']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'template_type': forms.Select(attrs={'class': 'form-control'}),
        }
