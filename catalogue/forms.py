from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from zoneinfo import available_timezones
from .models import Dataset, Domain, Profile, DatasetCategory, SensorType, SystemSetting, Backup, SystemLog


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
            'department', 'lead_researcher', 'data_file', 'doi'
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
            'lead_researcher': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your name or username'}),
            'data_file': forms.FileInput(attrs={'class': 'form-control'}),
            'doi': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional DOI or record identifier'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['doi'].label = 'DOI / Identifier'
        optional_fields = [
            'title', 'description', 'sensor_type', 'iuc_project_code',
            'output_format', 'location', 'update_frequency', 'start_date',
            'end_date', 'units_of_measurement', 'quality_score', 'license',
            'download_link', 'department', 'lead_researcher', 'data_file', 'doi'
        ]
        for field_name in optional_fields:
            self.fields[field_name].required = False
            self.fields[field_name].help_text = self.fields[field_name].help_text or 'Optional'


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
        user.is_staff = False
        user.is_superuser = False
        user.save()
        Profile.objects.get_or_create(user=user)
        if hasattr(user, 'profile'):
            user.profile.phone_number = phone_number
            user.profile.save()
        return user

    def signup(self, request, user):
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.phone_number = self.cleaned_data.get('phone_number', '').strip()
        profile.save()


class FeedbackForm(forms.Form):
    RATING_CHOICES = [(i, f"{i} Star{'s' if i > 1 else ''}") for i in range(1, 6)]
    CATEGORY_CHOICES = [
        ('bug', 'Bug Report'),
        ('feature', 'Feature Request'),
        ('general', 'General Suggestion'),
        ('compliment', 'Compliment'),
    ]

    rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Rating'
    )
    category = forms.ChoiceField(
        choices=CATEGORY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Category'
    )
    comment = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Tell us more about your experience...'}),
        label='Comments',
        required=False
    )


class UserAccountSettingsForm(forms.Form):
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )


class ProfileSettingsForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['phone_number', 'institution', 'department', 'biography']
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+255 7xx xxx xxx'}),
            'institution': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your institution'}),
            'department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your department'}),
            'biography': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Tell us about yourself...'}),
        }


class AccountSettingsForm(forms.Form):
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'readonly': True})
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )


class NotificationPreferencesForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['email_notifications', 'dataset_approval_notifications', 'dataset_rejection_notifications', 'new_dataset_alerts']
        widgets = {
            'email_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'dataset_approval_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'dataset_rejection_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'new_dataset_alerts': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class PrivacySettingsForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['profile_visibility', 'allow_others_to_view_profile']
        widgets = {
            'profile_visibility': forms.Select(attrs={'class': 'form-control'}),
            'allow_others_to_view_profile': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class AppearanceSettingsForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['theme_preference']
        widgets = {
            'theme_preference': forms.Select(attrs={'class': 'form-control'}),
        }


class LanguageSettingsForm(forms.ModelForm):
    preferred_language = forms.ChoiceField(
        choices=[('en', 'English'), ('sw', 'Kiswahili')],
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = Profile
        fields = ['preferred_language']


class TimeZoneSettingsForm(forms.ModelForm):
    time_zone = forms.ChoiceField(
        choices=[(tz, tz) for tz in sorted(available_timezones())],
        initial='Africa/Dar_es_Salaam',
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_time_zone'}),
    )

    class Meta:
        model = Profile
        fields = ['time_zone']


class ProfilePictureForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['profile_picture']
        widgets = {
            'profile_picture': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/jpeg,image/jpg,image/png'}),
        }

    def clean_profile_picture(self):
        picture = self.cleaned_data.get('profile_picture')
        if picture:
            if picture.size > 2 * 1024 * 1024:
                raise forms.ValidationError('Image size must be less than 2MB.')
            if not picture.content_type in ['image/jpeg', 'image/jpg', 'image/png']:
                raise forms.ValidationError('Only JPG, JPEG, and PNG images are allowed.')
        return picture


class GeneralSettingsForm(forms.Form):
    portal_name = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ARU IoT Dataset Catalogue'})
    )
    institution_name = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ARU'})
    )
    contact_email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'contact@aru.ac.ug'})
    )
    contact_phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+255 7xx xxx xxx'})
    )
    time_zone = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Africa/Kampala'})
    )
    default_language = forms.ChoiceField(
        choices=settings.LANGUAGES,
        initial='en',
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class DatasetSettingsForm(forms.Form):
    allowed_file_formats = forms.MultipleChoiceField(
        choices=[('CSV', 'CSV'), ('JSON', 'JSON'), ('XLSX', 'XLSX'), ('XML', 'XML'), ('Parquet', 'Parquet')],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        initial=['CSV', 'JSON', 'XLSX']
    )
    max_upload_size_mb = forms.IntegerField(
        min_value=1,
        max_value=5000,
        initial=100,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    default_visibility = forms.ChoiceField(
        choices=[('public', 'Public'), ('private', 'Private')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    default_quality_rating = forms.DecimalField(
        max_digits=3,
        decimal_places=2,
        min_value=0,
        max_value=5,
        initial=0.00,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'})
    )
    enable_versioning = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    require_metadata_before_upload = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class DatasetCategoryForm(forms.ModelForm):
    class Meta:
        model = DatasetCategory
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class SensorTypeForm(forms.ModelForm):
    class Meta:
        model = SensorType
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ResearchDomainForm(forms.ModelForm):
    class Meta:
        model = Domain
        fields = ['name', 'slug', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class UserSettingsForm(forms.Form):
    enable_registration = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    require_admin_approval = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    enable_email_verification = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    default_user_role = forms.ChoiceField(
        choices=[('researcher', 'Researcher'), ('admin', 'Admin')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    min_password_length = forms.IntegerField(
        min_value=6,
        max_value=100,
        initial=8,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    max_login_attempts = forms.IntegerField(
        min_value=1,
        max_value=100,
        initial=5,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    session_timeout_minutes = forms.IntegerField(
        min_value=1,
        max_value=1440,
        initial=60,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    enable_email_notifications = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class SecuritySettingsForm(forms.Form):
    password_complexity_rules = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'e.g., min 8 chars, 1 uppercase, 1 number, 1 special char'})
    )
    enable_two_factor_auth = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    https_enforcement = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    login_audit_logging = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    failed_login_lockout_duration = forms.IntegerField(
        min_value=1,
        max_value=1440,
        initial=30,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )


class BackupForm(forms.Form):
    name = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Backup name'})
    )
    backup_type = forms.ChoiceField(
        choices=[('manual', 'Manual'), ('automatic', 'Automatic')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )

