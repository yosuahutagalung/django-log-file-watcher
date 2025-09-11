from django.contrib import admin

from app.models import LogFile


@admin.register(LogFile)
class LogFileAdmin(admin.ModelAdmin):
    list_display = ['name', 'path', 'encoding', 'updated_at', 'created_at']
    search_fields = ['name', 'path', 'encoding']
