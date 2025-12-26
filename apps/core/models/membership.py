from django.db import models
from django.contrib.auth.models import User
from .base import BaseModel
from .company import Company

class CompanyMembership(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    role = models.TextField()

    class Meta:
        db_table = "company_memberships"
        managed = False
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["company"]),
            models.Index(fields=["created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=['user', 'company'], name='unique_user_company')
        ]
