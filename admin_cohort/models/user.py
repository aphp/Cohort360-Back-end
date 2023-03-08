from typing import List

from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import BaseUserManager, AbstractBaseUser
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import QuerySet

from admin_cohort.models import BaseModel
from admin_cohort.types import UserInfo


class UserManager(BaseUserManager):
    def create_simple_user(self, provider_username: str, email: str, lastname: str, firstname: str):
        user = get_user_model().objects.create(provider_username=provider_username,
                                               email=email,
                                               lastname=lastname,
                                               firstname=firstname)
        return user


class User(AbstractBaseUser, BaseModel):
    USERNAME_FIELD = "provider_username"
    provider_username = models.CharField(unique=True, primary_key=True, null=False, max_length=30)
    email = models.EmailField('email address', max_length=254, unique=True, null=True)
    firstname = models.TextField(blank=True, null=True)
    lastname = models.TextField(blank=True, null=True)
    provider_id = models.CharField(max_length=25, blank=True, null=True)
    password = None

    @property
    def displayed_name(self):
        deleted_suffix = self.delete_datetime and " (Supprimé)" or ""
        return f"{self.firstname} {self.lastname} ({self.provider_username}){deleted_suffix}"

    @property
    def valid_profiles(self) -> List:
        return [p for p in self.profiles.prefetch_related('accesses') if p.is_valid]

    @property
    def valid_manual_accesses_queryset(self) -> QuerySet:
        try:
            from accesses.models import get_user_valid_manual_accesses_queryset
        except ImportError:
            return QuerySet()
        return get_user_valid_manual_accesses_queryset(self)

    def __str__(self):
        return f"{self.firstname} {self.lastname} ({self.provider_username})"

    def __repr__(self):
        return f"User {self})"

    class Meta:
        db_table = 'user'


def get_or_create_user_with_info(user_info: UserInfo) -> User:
    try:
        u: User = User.objects.get(provider_username=user_info.username)
        if not u.email or not u.firstname or not u.lastname:
            u.email = user_info.email
            u.lastname = user_info.lastname
            u.firstname = user_info.firstname
            u.save()
        return u
    except ObjectDoesNotExist:
        user = UserManager().create_simple_user(provider_username=user_info.username,
                                                email=user_info.email,
                                                lastname=user_info.lastname,
                                                firstname=user_info.firstname)
    return user
