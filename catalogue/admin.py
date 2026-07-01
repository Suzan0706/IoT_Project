from django.contrib import admin
from .models import Domain, Dataset

@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ('title', 'domain', 'researcher', 'status', 'quality_score', 'download_count', 'created_at')
    list_filter = ('status', 'domain', 'created_at')
    search_fields = ('title', 'description', 'location')
    date_hierarchy = 'created_at'
    readonly_fields = ('download_count', 'created_at')
