from django.db import models


class TimestampBaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class LogFile(TimestampBaseModel):
    name = models.CharField(max_length=255)
    path = models.CharField(max_length=255)
    encoding = models.CharField(max_length=20, default='utf-8')

    def __str__(self):
        return f'({self.id}) {self.name}'
    
    class Meta:
        db_table = 'log_files'

    
