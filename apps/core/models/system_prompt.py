from django.db import models
from .base import BaseModel
from .company import Company

class SummarySystemPrompt(BaseModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT)
    name = models.TextField()
    segment = models.TextField()
    version = models.IntegerField()
    is_active = models.BooleanField(default=False)

    system_prompt = models.TextField()
    model = models.TextField()
    model_metadata = models.TextField(null=True, blank=True)

    metadata = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "summary_system_prompts"
        managed = False
        indexes = [
            models.Index(fields=["company"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("company", "segment", "version"),
                name="unique_summary_prompt_version_per_company",
            ),
        ]


class ScorecardSystemPrompt(BaseModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT)
    name = models.TextField()
    segment = models.TextField()
    version = models.IntegerField()
    is_active = models.BooleanField(default=False)

    system_prompt = models.TextField()
    model = models.TextField()
    model_metadata = models.TextField(null=True, blank=True)

    metadata = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "scorecard_system_prompts"
        managed = False
        indexes = [
            models.Index(fields=["company"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("company", "segment", "version"),
                name="unique_scorecard_prompt_version_per_company",
            ),
        ]
