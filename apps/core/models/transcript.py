from django.db import models
from django.contrib.auth.models import User
from .base import BaseModel
from .company import Company
from .call import Call

class Transcript(BaseModel):
    call = models.ForeignKey(Call, on_delete=models.PROTECT)
    company = models.ForeignKey(Company, on_delete=models.PROTECT)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    transcription_type = models.TextField()
    transcript = models.TextField(null=True, blank=True)
    segments = models.JSONField(null=True, blank=True)
    speaker_count = models.IntegerField(null=True, blank=True)
    status = models.TextField(null=True, blank=True)

    transcript_platform = models.TextField(null=True, blank=True)
    transcript_model = models.TextField(null=True, blank=True)
    scorecard_model = models.TextField(null=True, blank=True)
    summary_model = models.TextField(null=True, blank=True)
    models_metadata = models.JSONField(null=True, blank=True)

    call_summary = models.TextField(null=True, blank=True)
    call_summary_error = models.TextField(null=True, blank=True)
    call_summary_generated_at = models.DateTimeField(null=True, blank=True)

    call_scorecard = models.JSONField(null=True, blank=True)
    call_scorecard_error = models.TextField(null=True, blank=True)
    call_scorecard_generated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "transcripts"
        managed = True
        indexes = [
            models.Index(fields=["call"]),
            models.Index(fields=["company"]),
            models.Index(fields=["user"]),
            models.Index(fields=["created_at"]),
        ]
