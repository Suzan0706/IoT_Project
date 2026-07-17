from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from zoneinfo import available_timezones


class Profile(models.Model):
    THEME_CHOICES = [
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('system', 'System'),
    ]

    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('sw', 'Kiswahili'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    institution = models.CharField(max_length=255, blank=True)
    department = models.CharField(max_length=255, blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    biography = models.TextField(blank=True)
    email_notifications = models.BooleanField(default=True)
    dataset_approval_notifications = models.BooleanField(default=True)
    dataset_rejection_notifications = models.BooleanField(default=True)
    new_dataset_alerts = models.BooleanField(default=False)
    profile_visibility = models.CharField(max_length=20, choices=[('public', 'Public'), ('private', 'Private')], default='public')
    allow_others_to_view_profile = models.BooleanField(default=True)
    theme_preference = models.CharField(max_length=20, choices=THEME_CHOICES, default='system')
    admin_theme_preference = models.CharField(max_length=20, choices=THEME_CHOICES, default='system')
    preferred_language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en')
    time_zone = models.CharField(max_length=64, choices=[(tz, tz) for tz in sorted(available_timezones())], default='Africa/Dar_es_Salaam')
    time_zone_auto_detected = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} profile"


class Domain(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class DatasetCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Dataset Categories'

    def __str__(self):
        return self.name


class SensorType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class SystemSetting(models.Model):
    SETTING_TYPE_CHOICES = [
        ('text', 'Text'),
        ('number', 'Number'),
        ('boolean', 'Boolean'),
        ('email', 'Email'),
        ('url', 'URL'),
        ('choice', 'Choice'),
        ('file', 'File'),
    ]

    key = models.CharField(max_length=100, unique=True)
    value = models.TextField(blank=True)
    setting_type = models.CharField(max_length=20, choices=SETTING_TYPE_CHOICES, default='text')
    category = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    is_required = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'key']

    def __str__(self):
        return f"{self.key} ({self.category})"


class Backup(models.Model):
    BACKUP_TYPE_CHOICES = [
        ('manual', 'Manual'),
        ('automatic', 'Automatic'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    name = models.CharField(max_length=255)
    backup_type = models.CharField(max_length=20, choices=BACKUP_TYPE_CHOICES, default='manual')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    file_path = models.CharField(max_length=500, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"


class SystemLog(models.Model):
    LOG_LEVEL_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]

    LOG_TYPE_CHOICES = [
        ('login', 'Login'),
        ('user_activity', 'User Activity'),
        ('dataset_upload', 'Dataset Upload'),
        ('error', 'Error'),
        ('security', 'Security'),
    ]

    level = models.CharField(max_length=20, choices=LOG_LEVEL_CHOICES, default='info')
    log_type = models.CharField(max_length=20, choices=LOG_TYPE_CHOICES, default='user_activity')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=255)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.level}] {self.action}"


class Notification(models.Model):
    NOTIFICATION_TYPE_CHOICES = [
        ('info', 'Information'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE_CHOICES, default='info')
    is_read = models.BooleanField(default=False)
    sent_email = models.BooleanField(default=False)
    sent_sms = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.user.username}"


class Dataset(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Review'),
        ('live', 'Live'),
    ]

    SENSOR_TYPE_CHOICES = [
        ('Temperature', 'Temperature'),
        ('Humidity', 'Humidity'),
        ('Air Quality', 'Air Quality'),
        ('Water Quality', 'Water Quality'),
        ('Energy', 'Energy'),
        ('Motion', 'Motion'),
        ('Sound', 'Sound'),
        ('Light', 'Light'),
        ('Other', 'Other'),
    ]

    OUTPUT_FORMAT_CHOICES = [
        ('CSV', 'CSV'),
        ('JSON', 'JSON'),
        ('Parquet', 'Parquet'),
        ('XML', 'XML'),
        ('Other', 'Other'),
    ]

    LICENSE_CHOICES = [
        ('CC BY 4.0', 'CC BY 4.0'),
        ('CC0', 'CC0'),
        ('CC BY-SA 4.0', 'CC BY-SA 4.0'),
        ('MIT', 'MIT'),
        ('Other', 'Other'),
    ]

    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    researcher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='datasets')
    lead_researcher = models.CharField(max_length=255, blank=True, help_text='Name to display as the lead researcher for this dataset.')
    domain = models.ForeignKey(Domain, on_delete=models.PROTECT, related_name='datasets')
    sensor_type = models.CharField(max_length=100, choices=SENSOR_TYPE_CHOICES, blank=True)
    iuc_project_code = models.CharField(max_length=100, blank=True)
    output_format = models.CharField(max_length=20, choices=OUTPUT_FORMAT_CHOICES, default='CSV')
    location = models.CharField(max_length=255, blank=True)
    update_frequency = models.CharField(max_length=50, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    units_of_measurement = models.CharField(max_length=100, blank=True)
    quality_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    license = models.CharField(max_length=100, choices=LICENSE_CHOICES, default='CC BY 4.0')
    download_link = models.URLField(null=True, blank=True)
    department = models.CharField(max_length=100, blank=True)
    data_file = models.FileField(upload_to='datasets/', blank=True, null=True)
    doi = models.CharField(max_length=100, blank=True, null=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    download_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('download', 'File Downloaded'),
        ('status_change', 'Status Modified'),
        ('auth_event', 'Authentication Change'),
        ('view', 'Page View'),
        ('error', 'System Alert'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    endpoint_path = models.CharField(max_length=255)
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.get_action_type_display()} — {self.endpoint_path}"


class Feedback(models.Model):
    CATEGORY_CHOICES = [
        ('bug', 'Bug Report'),
        ('feature', 'Feature Request'),
        ('general', 'General Suggestion'),
        ('compliment', 'Compliment'),
    ]

    STATUS_CHOICES = [
        ('new', 'New'),
        ('reviewed', 'Reviewed'),
        ('resolved', 'Resolved'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='feedbacks')
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    comment = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Feedback #{self.id} — {self.get_category_display()} ({self.rating}★)"



