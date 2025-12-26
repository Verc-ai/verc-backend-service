import uuid
from django.db import models


# ==========================
# COMPANIES
# ==========================
class Company(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.TextField()
    slug = models.SlugField(unique=True)

    address = models.TextField(blank=True, null=True)
    phone = models.TextField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    other_info = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "app.companies"
        indexes = [
            models.Index(fields=["slug"]),
        ]


# ==========================
# COMPANY MEMBERSHIPS
# ==========================
class CompanyMembership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user_id = models.UUIDField()  # Google Identity Platform compatible
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="memberships",
    )

    role = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "app.company_memberships"
        unique_together = ("user_id", "company")
        indexes = [
            models.Index(fields=["user_id"]),
            models.Index(fields=["company"]),
        ]


# ==========================
# CALLS
# ==========================
class Call(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="calls",
    )

    user_id = models.UUIDField(blank=True, null=True)

    call_sid = models.TextField()
    caller_number = models.TextField(blank=True, null=True)
    destination_number = models.TextField(blank=True, null=True)
    direction = models.TextField()
    caller_info = models.TextField(blank=True, null=True)

    filename = models.TextField(blank=True, null=True)
    audio_url = models.TextField(blank=True, null=True)
    user_uploaded = models.BooleanField(default=False)

    call_started_at = models.DateTimeField(blank=True, null=True)
    call_ended_at = models.DateTimeField(blank=True, null=True)
    call_duration = models.IntegerField(blank=True, null=True)

    metadata = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "app.calls"
        indexes = [
            models.Index(fields=["company"]),
            models.Index(fields=["call_started_at"]),
        ]


# ==========================
# TRANSCRIPTS
# ==========================
class Transcript(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    call = models.ForeignKey(
        Call,
        on_delete=models.CASCADE,
        related_name="transcripts",
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="transcripts",
    )

    user_id = models.UUIDField(blank=True, null=True)

    transcription_type = models.TextField()  # post_call | real_time

    transcript = models.TextField(blank=True, null=True)
    segments = models.JSONField(blank=True, null=True)
    speaker_count = models.IntegerField(blank=True, null=True)
    status = models.TextField(blank=True, null=True)

    transcript_platform = models.TextField(blank=True, null=True)
    transcript_model = models.TextField(blank=True, null=True)
    scorecard_model = models.TextField(blank=True, null=True)
    summary_model = models.TextField(blank=True, null=True)
    models_metadata = models.JSONField(blank=True, null=True)

    call_summary = models.TextField(blank=True, null=True)
    call_summary_error = models.TextField(blank=True, null=True)
    call_summary_generated_at = models.DateTimeField(blank=True, null=True)

    call_scorecard = models.JSONField(blank=True, null=True)
    call_scorecard_error = models.TextField(blank=True, null=True)
    call_scorecard_generated_at = models.DateTimeField(blank=True, null=True)

    summary_prompt_id = models.UUIDField(blank=True, null=True)
    scorecard_prompt_id = models.UUIDField(blank=True, null=True)

    metadata = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "app.transcripts"
        indexes = [
            models.Index(fields=["company"]),
            models.Index(fields=["call"]),
            models.Index(fields=["created_at"]),
        ]


# ==========================
# TRANSCRIPT EVENTS
# ==========================
class TranscriptEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    transcript = models.ForeignKey(
        Transcript,
        on_delete=models.CASCADE,
        related_name="events",
    )

    call = models.ForeignKey(
        Call,
        on_delete=models.CASCADE,
        related_name="events",
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="transcript_events",
    )

    user_id = models.UUIDField(blank=True, null=True)

    sequence_number = models.IntegerField()
    timestamp_ms = models.BigIntegerField()

    speaker = models.TextField()
    text_chunk = models.TextField()
    pii_redacted = models.BooleanField(default=False)
    sentiment_score = models.FloatField(blank=True, null=True)
    is_final = models.BooleanField(default=False)

    payload = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "app.transcript_events"
        indexes = [
            models.Index(fields=["transcript", "sequence_number"]),
            models.Index(fields=["call"]),
            models.Index(fields=["company"]),
        ]
