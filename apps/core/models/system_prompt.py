from django.db import models
from .base import BaseModel
from .company import Company

class SummarySystemPrompt(BaseModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT)
    prompt_key = models.TextField()
    name = models.TextField(null=True, blank=True)
    segment = models.TextField(null=True, blank=True)
    version = models.IntegerField()
    is_active = models.BooleanField(default=False)

    system_prompt = models.TextField()
    model = models.TextField(null=True, blank=True)
    model_metadata = models.JSONField(null=True, blank=True)

    metadata = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "summary_system_prompts"
        managed = True
        indexes = [
            models.Index(fields=["company"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("company", "prompt_key", "version"),
                name="summary_prompts_unique_version",
            ),
        ]


class ScorecardSystemPrompt(BaseModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT)
    prompt_key = models.TextField()
    name = models.TextField(null=True, blank=True)
    segment = models.TextField(null=True, blank=True)
    version = models.IntegerField()
    is_active = models.BooleanField(default=False)

    system_prompt = models.TextField()
    model = models.TextField(null=True, blank=True)
    model_metadata = models.JSONField(null=True, blank=True)

    metadata = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "scorecard_system_prompts"
        managed = True
        indexes = [
            models.Index(fields=["company"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("company", "prompt_key", "version"),
                name="scorecard_prompts_unique_version",
            ),
        ]
