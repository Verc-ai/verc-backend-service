from django.db import models
from .base import BaseModel


class Company(BaseModel):
    name = models.TextField()
    slug = models.TextField(unique=True)
    address = models.TextField(blank=True, null=True)
    phone = models.TextField(blank=True, null=True)
    email = models.TextField(blank=True, null=True)
    other_info = models.JSONField(blank=True, null=True)

    class Meta:
        db_table = "companies"
        managed = True
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["created_at"]),
        ]
