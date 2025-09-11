from django.contrib import admin

from app.models import LogFile


# Register your models here.
class LogFileAdmin(admin.ModelAdmin):
    pass

admin.site.register(LogFile, LogFileAdmin)
