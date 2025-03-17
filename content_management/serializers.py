from rest_framework import serializers

from content_management.apps import ContentManagementConfig
from content_management.models import Content, ContentMetadata, MetadataName


class ContentMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentMetadata
        fields = ['name', 'value']


class ContentSerializer(serializers.ModelSerializer):
    content_type_display = serializers.SerializerMethodField()
    metadata = serializers.DictField(
        child=serializers.CharField(),
        required=False
    )

    class Meta:
        model = Content
        fields = ['id', 'title', 'content', 'page', 'content_type', 'content_type_display', 'metadata',
                  'created_at', 'modified_at', 'deleted_at']
        read_only_fields = ['created_at', 'modified_at']

    def validate_metadata(self, value):
        if not value:  # If metadata is empty or None, return it as is
            return value

        valid_names = set(item.value for item in MetadataName)
        invalid_names = set(value.keys()) - valid_names
        if invalid_names:
            raise serializers.ValidationError(
                f"Invalid metadata name(s): {', '.join(invalid_names)}. "
                f"Must be one of {', '.join(valid_names)}"
            )
        return value


    def _metadata_dict_to_list(self, metadata_dict):
        """Convert metadata from dict format to list of name-value pairs"""
        return [
            {'name': name, 'value': str(value)}
            for name, value in metadata_dict.items()
        ]

    def _metadata_list_to_dict(self, metadata_list):
        """Convert metadata from list of name-value pairs to dict format"""
        return {
            item.name: item.value
            for item in metadata_list
        }

    def get_content_type_display(self, obj) -> str:
        return ContentManagementConfig.CONTENT_TYPES.get(obj.content_type, {}).get('label', obj.content_type)

    def validate_content_type(self, value):
        if value not in ContentManagementConfig.CONTENT_TYPES:
            raise serializers.ValidationError(
                f'Invalid content type. Available types are: {", ".join(ContentManagementConfig.CONTENT_TYPES.keys())}'
            )
        return value

    def create(self, validated_data):
        metadata = validated_data.pop('metadata', [])
        content = Content.objects.create(**validated_data)

        if metadata:
            metadata_list = self._metadata_dict_to_list(metadata)
            for meta in metadata_list:
                ContentMetadata.objects.create(content=content, **meta)

        return content

    def update(self, instance, validated_data):
        metadata = validated_data.pop('metadata', None)

        # Update content fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update metadata if provided
        if metadata is not None:
            # Remove existing metadata
            instance.metadata.all().delete()
            # Convert and create new metadata
            metadata_list = self._metadata_dict_to_list(metadata)
            for meta in metadata_list:
                ContentMetadata.objects.create(content=instance, **meta)

        return instance

    def to_representation(self, instance):
        """Convert the model instance to a dictionary for serialization"""
        # Remove metadata field from fields
        self.fields.pop('metadata', None)

        # Get the basic representation
        data = super().to_representation(instance)

        # Add metadata as dict
        data['metadata'] = self._metadata_list_to_dict(instance.metadata.all())
        return data
