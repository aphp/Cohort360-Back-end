from rest_framework import serializers
from rest_framework.fields import Field, _UnvalidatedField


class MyListField(Field):
    child = _UnvalidatedField()
    initial = []
    default_error_messages = {}

    def to_representation(self, data):
        """
        List of object instances -> List of dicts of primitive datatypes.
        """
        return data.split(',')


class ApiIssueSerializer(serializers.Serializer):
    title = serializers.CharField(allow_null=False)
    id = serializers.IntegerField(allow_null=False)
    iid = serializers.IntegerField(allow_null=False)
    project_id = serializers.IntegerField(allow_null=False)
    description = serializers.CharField()
    state = serializers.CharField()
    created_at = serializers.DateTimeField(allow_null=False)
    updated_at = serializers.DateTimeField(allow_null=False)
    closed_at = serializers.DateTimeField(allow_null=True)
    closed_by = serializers.DateTimeField(allow_null=True)
    labels = serializers.ListField(serializers.CharField())
    type = serializers.CharField(allow_null=True)
    issue_type = serializers.CharField(allow_null=True)
    web_url = serializers.CharField(allow_null=True)


class IssuePostSerializer(serializers.Serializer):
    title = serializers.CharField(required=True)
    description = serializers.CharField(required=True)
    label = serializers.CharField(required=True)
    attachment = serializers.FileField(required=False)


class ThumbSerializer(serializers.Serializer):
    issue_iid = serializers.IntegerField(required=True)
    vote = serializers.IntegerField(required=True)

