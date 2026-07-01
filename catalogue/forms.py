from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from .models import Dataset, Domain, Profile


class DatasetForm(forms.ModelForm):
    class Meta:
        model = Dataset
        fields = ['title', 'domain', 'description', 'quality_score', 'download_count', 'status']


class DatasetRegistrationForm(forms.ModelForm):
    class Meta:
        model = Dataset
        fields = [
            'title', 'description', 'domain', 'sensor_type', 'iuc_project_code',
            'output_format', 'location', 'update_frequency', 'start_date', 'end_date',
            'units_of_measurement', 'quality_score', 'license', 'download_link',
            'department', 'data_file', 'doi'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Kampala BRT Corridor — Bus Dwell-Time'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Provide data scope abstract...'}),
            'domain': forms.Select(attrs={'class': 'form-control'}),
            'sensor_type': forms.Select(attrs={'class': 'form-control'}),
            'iuc_project_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., IUC-Mobility'}),
            'output_format': forms.Select(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City, country'}),
            'update_frequency': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 1 min, 30 s'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'units_of_measurement': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., µg/m³, °C, %RH'}),
            'quality_score': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 5, 'step': 0.1, 'value': 4.0}),
            'license': forms.Select(attrs={'class': 'form-control'}),
            'download_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Department name'}),
            'data_file': forms.FileInput(attrs={'class': 'form-control'}),
            'doi': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'https://doi.org/…'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['doi'].label = 'DOI / Identifier'
        self.fields['end_date'].required = False
        self.fields['download_link'].required = False
        self.fields['data_file'].required = False


class AdminProfileForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        required=True,
        label='Username',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'autocomplete': 'username',
        })
    )
    current_password = forms.CharField(
        required=True,
        label='Current password',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'current-password',
        })
    )
    new_password = forms.CharField(
        required=False,
        label='New password',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'new-password',
            'placeholder': 'Leave blank to keep current password',
        })
    )


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'autocomplete': 'username',
            'placeholder': 'Username',
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'autocomplete': 'current-password',
            'placeholder': 'Password',
        })


class SignupForm(forms.Form):
    full_name = forms.CharField(
        max_length=150,
        required=True,
        label='Full Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'autocomplete': 'name',
            'placeholder': 'Your full name',
        })
    )
    email = forms.EmailField(
        required=True,
        label='Email Address',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'autocomplete': 'email',
            'placeholder': 'you@example.com',
        })
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        label='Phone Number',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'autocomplete': 'tel',
            'placeholder': '+255 7xx xxx xxx',
        })
    )
    terms = forms.BooleanField(
        required=True,
        label='I agree to the Terms & Conditions',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    password1 = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'new-password',
            'placeholder': 'Create a strong password',
        })
    )
    password2 = forms.CharField(
        label='Confirm Password',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'new-password',
            'placeholder': 'Confirm your password',
        })
    )

    def save(self, request):
        full_name = self.cleaned_data.get('full_name', '').strip()
        email = self.cleaned_data.get('email', '').strip()
        phone_number = self.cleaned_data.get('phone_number', '').strip()
        password = self.cleaned_data.get('password1')

        username = email.split('@')[0]
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=full_name,
        )
        Profile.objects.get_or_create(user=user)
        if hasattr(user, 'profile'):
            user.profile.phone_number = phone_number
            user.profile.save()
        return user

    def signup(self, request, user):
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.phone_number = self.cleaned_data.get('phone_number', '').strip()
        profile.save()
