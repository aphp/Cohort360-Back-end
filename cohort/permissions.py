from rest_framework.permissions import IsAuthenticated


class IsOwnerPermission(IsAuthenticated):

    def has_object_permission(self, request, view, obj):
        return getattr(obj, "owner", None) == request.user
