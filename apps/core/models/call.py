
from django.db import models
from django.contrib.auth.models import User
from .base import BaseModel
from .company import Company

class Call(BaseModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    call_sid = models.TextField(null=True, blank=True)
    caller_number = models.TextField(null=True, blank=True)
    destination_number = models.TextField(null=True, blank=True)
    direction = models.TextField(null=True, blank=True)
    caller_info = models.TextField(null=True, blank=True)

    filename = models.TextField(null=True, blank=True)
    audio_url = models.TextField(null=True, blank=True)
    user_uploaded = models.BooleanField(default=False)

    call_started_at = models.DateTimeField(null=True, blank=True)
    call_ended_at = models.DateTimeField(null=True, blank=True)
    call_duration = models.IntegerField(null=True, blank=True)

    metadata = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "calls"
        managed = False
        indexes = [
            models.Index(fields=["company"]),
            models.Index(fields=["user"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["call_sid"]),
        ]
