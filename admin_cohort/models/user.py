from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models

from admin_cohort.models import BaseModel


class User(AbstractBaseUser, BaseModel):
    USERNAME_FIELD = "username"
    username = models.CharField(unique=True, primary_key=True, null=False, max_length=30)
    email = models.EmailField('email address', max_length=254, unique=True, null=True)
    firstname = models.CharField(blank=True, null=True)
    lastname = models.CharField(blank=True, null=True)
    password = models.CharField(blank=True, null=True, max_length=128)

    def __str__(self):
        return f"{self.firstname} {self.lastname} ({self.username})"

    def __repr__(self):
        return f"User {self})"

    @property
    def display_name(self) -> str:
        deleted_suffix = self.delete_datetime and " (deleted)" or ""
        return f"{self}{deleted_suffix}"

    class Meta:
        db_table = 'user'
