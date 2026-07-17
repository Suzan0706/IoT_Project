from django.contrib import admin
from .models import Domain, Dataset, Feedback

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

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'rating', 'category', 'status', 'created_at')
    list_filter = ('category', 'status', 'created_at')
    search_fields = ('comment', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    fields = ('user', 'rating', 'category', 'comment', 'status', 'admin_notes', 'created_at', 'updated_at')


