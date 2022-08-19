from typing import List, Union
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import BaseUserManager, AbstractBaseUser
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import SET_NULL
from django.utils import timezone
from safedelete import SOFT_DELETE_CASCADE
from safedelete.models import SafeDeleteModel

from admin_cohort import conf_auth
from admin_cohort.types import UserInfo, JobStatus, NewJobStatus


class UndeletableModelManager(models.Manager):
    def all(self, even_deleted=False):
        usual_all = super(UndeletableModelManager, self).all()
        return usual_all.filter(delete_datetime__isnull=True) \
            if not even_deleted else usual_all

    def filter(self, *args, **kwargs):
        return self.all(even_deleted=kwargs.get('even_deleted', False))\
            .filter(*args, **kwargs)

    def get(self, *args, **kwargs):
        return self.all(even_deleted=kwargs.get('even_deleted', False))\
            .get(*args, **kwargs)


class BaseModel(models.Model):
    insert_datetime = models.DateTimeField(null=True, auto_now_add=True)
    update_datetime = models.DateTimeField(null=True, auto_now=True)
    delete_datetime = models.DateTimeField(blank=True, null=True)

    objects = UndeletableModelManager()

    class Meta:
        abstract = True

    def delete(self):
        if self.delete_datetime is None:
            self.delete_datetime = timezone.now()
            self.save()


class CohortBaseModel(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE

    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False,
                            auto_created=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserManager(BaseUserManager):
    def create_simple_user(self, provider_username: str, email: str,
                           lastname: str, firstname: str):
        user = get_user_model().objects.create(
            provider_username=provider_username,
            email=email,
            lastname=lastname,
            firstname=firstname,
        )
        return user


class User(AbstractBaseUser, BaseModel):
    USERNAME_FIELD = "provider_username"
    provider_username = models.CharField(unique=True, primary_key=True,
                                         null=False, max_length=30)
    email = models.EmailField('email address', max_length=254,
                              unique=True, null=True)
    firstname = models.TextField(blank=True, null=True)
    lastname = models.TextField(blank=True, null=True)
    provider_id = models.BigIntegerField(blank=True, null=True)

    password = None

    @property
    def displayed_name(self):
        deleted_info = "(Supprimé)" if self.delete_datetime is not None else ""
        return f"{self.firstname} {self.lastname} ({self.provider_username}) " \
               f"{deleted_info}"

    # @property
    # def provider(self):
    #     res = get_provider(provider_source_value=self.provider_username)
    #     return res

    @property
    def valid_profiles(self) -> List:
        return [p for p in self.profiles.prefetch_related('accesses')
                if p.is_valid]

    @property
    def valid_accesses(self):
        return [a for a in
                sum([list(p.accesses.all())
                     for p in self.valid_profiles],
                    list()) if a.is_valid]

    def __str__(self):
        return f"{self.firstname} {self.lastname} ({self.provider_username})"

    class Meta:
        managed = True
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
        user = UserManager().create_simple_user(
            provider_username=user_info.username,
            email=user_info.email,
            lastname=user_info.lastname,
            firstname=user_info.firstname,
        )
    return user


def get_or_create_user(jwt_access_token: str) -> User:
    user_info = conf_auth.get_user_info(jwt_access_token=jwt_access_token)
    return get_or_create_user_with_info(user_info)


def get_user(user_id: str) -> User:
    user = User.objects.filter(provider_username=user_id).first()
    if user is None:
        raise User.DoesNotExist
    return user


class JobModel(models.Model):
    request_job_id = models.TextField(blank=True, null=True)
    request_job_status = models.CharField(
        max_length=10,
        choices=[(e.value.lower(), e.value.lower()) for e in JobStatus],
        default=JobStatus.PENDING.name.lower(), null=True
    )
    new_request_job_status = models.CharField(
        max_length=10,
        choices=[(e.value.lower(), e.value.lower()) for e in NewJobStatus],
        default=JobStatus.PENDING.name.lower(), null=True
    )
    request_job_fail_msg = models.TextField(blank=True, null=True)
    request_job_duration = models.TextField(blank=True, null=True)

    class Meta:
        abstract = True

    def validate(self):
        if self.new_request_job_status != NewJobStatus.new:
            raise Exception(
                f"Job can be validated only if current status is "
                f"'{NewJobStatus.new}'. Current status is "
                f"'{self.new_request_job_status}'")
        self.new_request_job_status = NewJobStatus.validated
        self.save()

    def deny(self):
        if self.new_request_job_status != NewJobStatus.new:
            raise Exception(
                f"Job can be denied only if current status is "
                f"'{NewJobStatus.new}'. Current status is "
                f"'{self.new_request_job_status}'")
        self.new_request_job_status = NewJobStatus.denied
        self.save()


class JobModelWithReview(JobModel):
    reviewer_fk = models.ForeignKey(
        User, related_name='reviewed_export_requests',
        on_delete=SET_NULL, null=True)
    review_request_datetime = models.DateTimeField(null=True)

    class Meta:
        abstract = True

    def validate(self, reviewer: Union[User, None]):
        self.reviewer_fk = reviewer
        self.review_request_datetime = timezone.now()
        return super(JobModelWithReview, self).validate()

    def deny(self, reviewer: Union[User, None]):
        self.reviewer_fk = reviewer
        self.review_request_datetime = timezone.now()
        return super(JobModelWithReview, self).deny()


class MaintenancePhase(BaseModel):
    id = models.AutoField(primary_key=True)
    subject = models.TextField()
    start_datetime = models.DateTimeField(null=False)
    end_datetime = models.DateTimeField(null=False)

    @property
    def active(self):
        return self.start_datetime < timezone.now() < self.end_datetime


def get_next_maintenance() -> Union[MaintenancePhase, None]:
    current = MaintenancePhase.objects\
        .filter(start_datetime__lte=timezone.now(),
                end_datetime__gte=timezone.now())\
        .order_by('-end_datetime').first()
    if current is not None:
        return current

    next = MaintenancePhase.objects\
        .filter(start_datetime__gte=timezone.now())\
        .order_by('start_datetime').first()
    return next
