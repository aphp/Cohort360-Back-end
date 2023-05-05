from django.db import models
from django.utils import timezone


class UndeletableModelManager(models.Manager):
    def all(self, even_deleted=False):
        usual_all = super(UndeletableModelManager, self).all()
        if even_deleted:
            return usual_all
        return usual_all.filter(delete_datetime__isnull=True)

    def filter(self, *args, **kwargs):
        return self.all(even_deleted=kwargs.get('even_deleted', False)).filter(*args, **kwargs)

    def get(self, *args, **kwargs):
        return self.all(even_deleted=kwargs.get('even_deleted', False)).get(*args, **kwargs)


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
