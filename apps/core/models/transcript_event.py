from django.db import models
from django.contrib.auth.models import User
import uuid
from .company import Company
from .call import Call
from .transcript import Transcript

class TranscriptEvent(models.Model):
    # Note: This model does NOT inherit from BaseModel because transcript_events table
    # doesn't have updated_at column in the actual database (only has created_at)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    transcript = models.ForeignKey(Transcript, on_delete=models.CASCADE)
    call = models.ForeignKey(Call, on_delete=models.PROTECT)
    company = models.ForeignKey(Company, on_delete=models.PROTECT)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    sequence_number = models.IntegerField()
    timestamp_ms = models.BigIntegerField()

    speaker = models.TextField(null=True, blank=True)
    text_chunk = models.TextField(null=True, blank=True)
    pii_redacted = models.BooleanField(default=False)
    sentiment_score = models.FloatField(null=True, blank=True)
    is_final = models.BooleanField(default=False)

    payload = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "transcript_events"
        managed = False
        indexes = [
            models.Index(fields=["transcript"]),
            models.Index(fields=["call"]),
            models.Index(fields=["company"]),
            models.Index(fields=["user"]),
            models.Index(fields=["sequence_number"]),
            models.Index(fields=["created_at"]),
        ]
