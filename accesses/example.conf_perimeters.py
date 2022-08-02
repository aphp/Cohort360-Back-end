from typing import List, Union, OrderedDict

from rest_framework import serializers

from accesses.perimeters_API import ApiPerimeter


def get_provider_id(user_id: str) -> int:
    raise NotImplementedError


def get_all_level_parents_perimeters(
        perimeter_ids: List[str], ids_only: bool = False) -> List[ApiPerimeter]:
    """
    @param perimeter_ids: ids to filter
    @return: perimeter objects with parent_id
    """
    raise NotImplementedError


class PerimeterSerializer(serializers.ModelSerializer):
    pass


def rootify_perimeters(
        perimeters: List[OrderedDict], roots_ids: List[str]
) -> List[OrderedDict]:
    """
    Given a full list of Perimeters that contain 'parent_id' that will
    necessary be within the list,
    returns the small list of perimeters from the roots_ids, completed
    with the field parent showing directly the matching perimeter
    @param perimeters: full list of perimeters
    @param roots_ids: ids of the perimeters that should be returned
    @return:
    """
    raise NotImplementedError


def get_perimeters(ids_only: bool = False, **kwargs) \
        -> List[Union[ApiPerimeter, str]]:
    """
    Request to get a list of Perimeters
    kwargs possibilities should match with
    CustomPerimeterViewSet.filterset_fields,
    with keys without 'perimeter_' start
    @param kwargs:
    @return:
    """
    raise NotImplementedError


class CustomPerimeterViewSet:
    filterset_fields = []
    search_fields = []
    ordering_fields = []

    def get_queryset(self):
        raise NotImplementedError

    def get_manageable(self, request):
        raise NotImplementedError

    def children(self, request):
        raise NotImplementedError

    def list(self, request, *args, **kwargs):
        raise NotImplementedError

    def retrieve(self, request, *args, **kwargs):
        raise NotImplementedError
