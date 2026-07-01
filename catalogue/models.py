from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} profile"


class Domain(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


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

    title = models.CharField(max_length=255)
    description = models.TextField()
    researcher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='datasets')
    domain = models.ForeignKey(Domain, on_delete=models.PROTECT, related_name='datasets')
    sensor_type = models.CharField(max_length=100, choices=SENSOR_TYPE_CHOICES)
    iuc_project_code = models.CharField(max_length=100)
    output_format = models.CharField(max_length=20, choices=OUTPUT_FORMAT_CHOICES, default='CSV')
    location = models.CharField(max_length=255)
    update_frequency = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    units_of_measurement = models.CharField(max_length=100)
    quality_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    license = models.CharField(max_length=100, choices=LICENSE_CHOICES, default='CC BY 4.0')
    download_link = models.URLField(null=True, blank=True)
    department = models.CharField(max_length=100)
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
