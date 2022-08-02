from rest_framework import serializers
from rest_framework.relations import MANY_RELATION_KWARGS, ManyRelatedField

from workspaces.models import Account, Kernel, JupyterMachine, \
    RangerHivePolicy, LdapGroup, Project


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = "__all__"


class PublicProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        exclude = ["insert_datetime", "data_conservation_duration",
                   "data_recipients", ]


class KernelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Kernel
        fields = "__all__"


class JupyterMachineSerializer(serializers.ModelSerializer):
    class Meta:
        model = JupyterMachine
        fields = "__all__"


class RangerHivePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = RangerHivePolicy
        fields = "__all__"


class LdapGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = LdapGroup
        fields = "__all__"


class KernelManyRelatedField(ManyRelatedField):
    def to_representation(self, iterable):
        iterable_names = [value.name for value in iterable]

        return dict([
            (k.name, k.name in iterable_names) for k in Kernel.objects.all()
        ])


class KernelRelatedField(serializers.RelatedField):
    @classmethod
    def many_init(cls, *args, **kwargs):
        list_kwargs = {'child_relation': cls(*args, **kwargs)}
        for key in kwargs:
            if key in MANY_RELATION_KWARGS:
                list_kwargs[key] = kwargs[key]
        return KernelManyRelatedField(**list_kwargs)


class JoinedManyRelatedField(ManyRelatedField):
    def to_representation(self, iterable):
        return " ".join([
            self.child_relation.to_representation(value)
            for value in iterable
        ])


class LdapGroupRelatedField(serializers.SlugRelatedField):
    @classmethod
    def many_init(cls, *args, **kwargs):
        list_kwargs = {'child_relation': cls(*args, **kwargs)}
        for key in kwargs:
            if key in MANY_RELATION_KWARGS:
                list_kwargs[key] = kwargs[key]
        return JoinedManyRelatedField(**list_kwargs)


class DbAccountSerializer(serializers.ModelSerializer):
    kernels = KernelRelatedField(many=True, read_only=True)
    jupyter_machines = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="name",
    )
    ldap_groups = LdapGroupRelatedField(
        many=True, read_only=True, slug_field="name"
    )
    ranger_hive_policy_type = serializers.CharField(
        source="ranger_hive_policy.policy_type"
    )
    ranger_hive_policy_db = serializers.CharField(
        source="ranger_hive_policy.db"
    )
    ranger_hive_policy_db_tables = serializers.CharField(
        source="ranger_hive_policy.db_tables"
    )
    ranger_hive_policy_db_imagerie = serializers.CharField(
        source="ranger_hive_policy.db_imagerie"
    )
    ranger_hive_policy_db_work = serializers.CharField(
        source="ranger_hive_policy.db_work"
    )

    class Meta:
        model = Account
        exclude = ["ranger_hive_policy"]


class AccountSerializer(serializers.ModelSerializer):
    kernels = KernelSerializer(many=True, allow_null=True)
    jupyter_machines = JupyterMachineSerializer(many=True, allow_null=True)
    ldap_groups = LdapGroupSerializer(many=True, allow_null=True)
    ranger_hive_policy = RangerHivePolicySerializer(allow_null=True)

    class Meta:
        model = Account
        fields = "__all__"
