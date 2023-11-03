from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models

from admin_cohort.models import BaseModel


class User(AbstractBaseUser, BaseModel):
    USERNAME_FIELD = "provider_username"
    provider_username = models.CharField(unique=True, primary_key=True, null=False, max_length=30)
    email = models.EmailField('email address', max_length=254, unique=True, null=True)
    firstname = models.TextField(blank=True, null=True)
    lastname = models.TextField(blank=True, null=True)
    provider_id = models.CharField(max_length=25, blank=True, null=True)
    password = None

    def __str__(self):
        return f"{self.firstname} {self.lastname} ({self.provider_username})"

    def __repr__(self):
        return f"User {self})"

    @property
    def displayed_name(self):
        deleted_suffix = self.delete_datetime and " (Supprimé)" or ""
        return f"{self.firstname} {self.lastname} ({self.provider_username}){deleted_suffix}"

    class Meta:
        db_table = 'user'
