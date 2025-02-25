from enum import Enum

from django.db import models
from rest_framework.exceptions import ValidationError

from content_management.apps import ContentManagementConfig


class MetadataName(str, Enum):
    ORDER = 'order'
    STYLE = 'style'
    TAGS = 'tags'

    @classmethod
    def choices(cls):
        return [(item.value, item.name) for item in cls]


class ContentMetadata(models.Model):
    content = models.ForeignKey(
        'Content',
        on_delete=models.CASCADE,
        related_name='metadata'
    )
    name = models.CharField(
        max_length=50,
        choices=MetadataName.choices()
    )
    value = models.CharField(max_length=255)

    class Meta:
        unique_together = ['content', 'name']

    def __str__(self):
        return f"{self.content.title} - {self.name}: {self.value}"


class Content(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    page = models.CharField(max_length=100)
    content_type = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def clean(self):
        # Validate content_type against available types
        if self.content_type not in ContentManagementConfig.CONTENT_TYPES:
            raise ValidationError({
                'content_type': f'Invalid content type. Available types are: {", ".join(ContentManagementConfig.CONTENT_TYPES.keys())}'
            })

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
