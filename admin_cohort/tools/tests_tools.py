from __future__ import annotations

import json
import random
import string
from typing import Tuple, List

from django.conf import settings
from django.db.models import Manager, Field, Model
from django.test import TestCase
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate

from accesses.models import Role, Profile, Perimeter
from admin_cohort.models import BaseModel, User
from cohort.models import CohortBaseModel
from admin_cohort.settings import PERIMETERS_TYPES, ROOT_PERIMETER_TYPE, MANUAL_SOURCE
from admin_cohort.tools import prettify_dict, prettify_json
from admin_cohort.types import MissingDataError


class ObjectView(object):
    def __init__(self, d):
        self.__dict__ = d


class PagedResponse:
    def __init__(self, response: Response):
        result = json.loads(response.content)

        if 'count' not in result:
            raise MissingDataError('No count in response')
        if not isinstance(result['count'], int):
            raise MissingDataError('"count" in response is not integer')
        self.count = result['count']

        if 'next' not in result:
            raise MissingDataError('No next in response')
        if not isinstance(result['next'], str) and result['next'] is not None:
            raise MissingDataError('"next" in response is not string')
        self.next = result['next']

        if 'previous' not in result:
            raise MissingDataError('No previous in response')
        if not isinstance(result['previous'], str) and result['previous'] is not None:
            raise MissingDataError('"previous" in response is not str')
        self.previous = result['previous']

        if 'results' not in result:
            raise MissingDataError('No results in response')
        if not isinstance(result['results'], list):
            raise MissingDataError('"results" in response is not list')
        self.results = result['results']


ALL_RIGHTS = [
    f.name for f in Role._meta.fields
    if f.name.startswith('right_')
]


def new_random_user(
        provider_id: int = None,
        firstname: str = '', lastname: str = '', email: str = ''
) -> User:
    if provider_id is None:
        provider_id = str(random.randint(0, 10000000))

        while provider_id in [
            p.provider_username for p in User.objects.all()
        ]:
            provider_id = str(random.randint(0, 10000000))

    u: User = User.objects.create(
        provider_username=str(provider_id),
        firstname=firstname,
        lastname=lastname,
        email=email,
        provider_id=provider_id,
    )
    return u


def new_user_and_profile(
        p_name: str = '', provider_id: int = None,
        firstname: str = '', lastname: str = '', email: str = ''
) -> Tuple[User, Profile]:
    """
    Creates a triplet necessary to define a new empty user
    @param p_name: provider_name
    @type p_name: str
    @param provider_id:
    @type provider_id: int
    @param firstname:
    @type firstname: str
    @param lastname:
    @type lastname: str
    @param email:
    @type email: str
    @return: a basic User, Provider, Profile tuple
    @rtype: Tuple[User, Provider, Profile]
    """
    u = new_random_user(provider_id, firstname, lastname, email)

    p: Profile = Profile.objects.create(
        provider_name=p_name,
        source=MANUAL_SOURCE,
        provider_id=provider_id,
        user=u,
        is_active=True,
        email=email,
        firstname=firstname,
        lastname=lastname,
    )

    return u, p


class CaseRetrieveFilter:
    def __init__(self, exclude: dict = None, **kwargs):
        self.exclude = exclude or dict()

    @property
    def args(self) -> dict:
        return dict([(k, v) for (k, v)
                     in self.__dict__.items() if k != 'exclude'])


class RequestCase:
    def __init__(self, user: User, status: int, success: bool, title: str = "",
                 **kwargs):
        self.title = title
        self.user = user
        self.status = status
        self.success = success

    def clone(self, **kwargs) -> RequestCase:
        return self.__class__(**{**self.__dict__, **kwargs})

    @property
    def description_dict(self) -> dict:
        d = {
            **self.__dict__,
            'user': self.user and self.user.displayed_name,
        }
        d.pop('title', None)
        return d

    @property
    def description(self):
        return f"Case {self.title}: {prettify_dict(self.description_dict)}"

    def __str__(self):
        return self.title


class CreateCase(RequestCase):
    retrieve_filter: CaseRetrieveFilter

    def __init__(self, data: dict, retrieve_filter: CaseRetrieveFilter,
                 **kwargs):
        super(CreateCase, self).__init__(**kwargs)
        self.data = data
        self.retrieve_filter = retrieve_filter

    @property
    def json_data(self) -> dict:
        d = self.data.copy()
        return d


class DeleteCase(RequestCase):
    def __init__(self, data_to_delete: dict, **kwargs):
        super(DeleteCase, self).__init__(**kwargs)
        self.data_to_delete = data_to_delete


class PatchCase(RequestCase):
    def __init__(self, initial_data: dict,
                 data_to_update: dict, **kwargs):
        super(PatchCase, self).__init__(**kwargs)
        self.initial_data = initial_data
        self.data_to_update = data_to_update


class ListCase(RequestCase):
    def __init__(self, to_find: list = None, url: str = "",
                 page_size: int = None, params: dict = None,
                 previously_found_ids: List = None, **kwargs):
        super(ListCase, self).__init__(**kwargs)
        self.to_find = to_find or []
        self.url = url
        self.page_size = page_size if page_size is not None \
            else settings.REST_FRAMEWORK.get('PAGE_SIZE')
        self.params = params or {}
        self.previously_found_ids = previously_found_ids or []

    @property
    def description_dict(self) -> dict:
        d = {
            **super(ListCase, self).description_dict,
            'previously_found_ids': [],
            'to_find': ([str(obj) for obj in self.to_find[0:10]]
                        + (["..."] if len(self.to_find) > 10 else [])),
        }
        return d

    def clone(self, **kwargs) -> ListCase:
        return self.__class__(**{**self.__dict__, **kwargs})


class NestedListCase(ListCase):
    def __init__(self, view: any, source_id: str, **kwargs):
        super(NestedListCase, self).__init__(**kwargs)
        self.view = view
        self.source_id = source_id


class RetrieveCase(RequestCase):
    def __init__(self, to_find: any = None, url: str = "", params: dict = None,
                 view_params: dict = None, **kwargs):
        super(RetrieveCase, self).__init__(**kwargs)
        self.to_find = to_find
        self.url = url
        self.params = params or {}
        self.view_params = view_params or dict()

    @property
    def description_dict(self) -> dict:
        d = {
            **super(RetrieveCase, self).description_dict,
            'to_find': str(self.to_find)
        }
        return d

    def clone(self, **kwargs) -> RetrieveCase:
        return self.__class__(**{**self.__dict__, **kwargs})


class BaseTests(TestCase):
    databases = ["default"]
    unupdatable_fields = []
    unsettable_fields = []
    unsettable_default_fields = {}
    manual_dupplicated_fields = []

    def setUp(self):
        self.factory = APIRequestFactory()
        self.all_rights = [f.name for f in Role._meta.fields
                           if f.name.startswith('right_')]

    def get_response_payload(self, response):
        response.render()
        return json.loads(response.content)

    def check_is_created(self, base_instance,
                         request_model: dict = None, **kwargs):
        request_model = request_model or dict()
        self.assertIsNotNone(base_instance)
        self.assertTrue(isinstance(base_instance, (BaseModel, CohortBaseModel)))
        self.assertIsNotNone(base_instance)

        [
            self.assertEqual(
                getattr(base_instance, f), v, f"Error with model's {f}"
            ) for [f, v] in self.unsettable_default_fields.items()
        ]

        if len(request_model.items()) > 0:
            [
                self.assertNotEqual(
                    getattr(base_instance, f), request_model.get(f),
                    f"Error with model's {f}"
                ) for f in self.unsettable_fields if f in request_model
            ]

        for dupp_field in self.manual_dupplicated_fields:
            self.assertIsNone(getattr(base_instance, dupp_field), dupp_field)
            if dupp_field in request_model:
                manual_field = f"manual_{dupp_field}"
                self.assertEqual(
                    getattr(base_instance, manual_field),
                    request_model[dupp_field],
                    f"Error with model's {dupp_field}"
                )

    def check_is_deleted(self, base_instance: any):
        if isinstance(base_instance, BaseModel):
            self.assertIsNotNone(base_instance)
            self.assertIsNotNone(base_instance.delete_datetime)
        elif isinstance(base_instance, CohortBaseModel):
            self.assertIsNotNone(base_instance)
            self.assertIsNotNone(base_instance.deleted)
        else:
            self.assertIsNone(base_instance)

    def check_unupdatable_not_updated(self, instance_1,
                                      instance_2, request_model=dict()):
        self.assertTrue(isinstance(instance_1, (BaseModel, CohortBaseModel)))
        self.assertTrue(isinstance(instance_2, (BaseModel, CohortBaseModel)))
        [self.assertNotEqual(getattr(instance_1, f), request_model[f],
                             f"Error with model's {f}")
         for f in self.unupdatable_fields + self.manual_dupplicated_fields
         if f in request_model]

        for dupp_field in self.manual_dupplicated_fields:
            if dupp_field in request_model:
                manual_field = f"manual_{dupp_field}"
                self.assertEqual(getattr(instance_1, manual_field),
                                 request_model[dupp_field])


class SimplePerimSetup:
    def setUp(self):
        # PERIMETERS
        #         aphp
        #        /    \
        # hospital1   hospital2
        #                |
        #             hospital3
        self.aphp: Perimeter = Perimeter.objects.create(
            local_id="0",
            name=ROOT_PERIMETER_TYPE,
            type_source_value=PERIMETERS_TYPES[0]
        )
        self.hospital1: Perimeter = Perimeter.objects.create(
            local_id="1",
            name="Galbadia Garden",
            type_source_value=PERIMETERS_TYPES[1],
            parent=self.aphp,
        )
        self.hospital2: Perimeter = Perimeter.objects.create(
            local_id="2",
            name="Balamb Garden",
            type_source_value=PERIMETERS_TYPES[1],
            parent=self.aphp,
        )
        self.hospital3: Perimeter = Perimeter.objects.create(
            local_id="3",
            name="Seeds",
            type_source_value=PERIMETERS_TYPES[2],
            parent=self.hospital2,
        )
        self.all_perimeters: List[Perimeter] = [
            self.aphp, self.hospital1, self.hospital2, self.hospital3
        ]


class NumerousPerimSetup:
    def setUp(self):
        #      perim0
        #     /     \
        # perim11   perim12
        #   |          /   \
        # perim21   perim22 perim23
        #   |    \            |
        # perim31 perim32   perim33
        t = PERIMETERS_TYPES[0]
        self.perim0 = Perimeter.objects.create(type_source_value=t, local_id="0")
        self.perim11 = Perimeter.objects.create(type_source_value=t, parent=self.perim0, local_id="11")
        self.perim21 = Perimeter.objects.create(type_source_value=t, parent=self.perim11, local_id="21")
        self.perim31 = Perimeter.objects.create(type_source_value=t, parent=self.perim21, local_id="31")
        self.perim32 = Perimeter.objects.create(type_source_value=t, parent=self.perim21, local_id="32")
        self.perim12 = Perimeter.objects.create(type_source_value=t, parent=self.perim0, local_id="12")
        self.perim22 = Perimeter.objects.create(type_source_value=t, parent=self.perim12, local_id="22")
        self.perim23 = Perimeter.objects.create(type_source_value=t, parent=self.perim12, local_id="23")
        self.perim33 = Perimeter.objects.create(type_source_value=t, parent=self.perim23, local_id="33")
        self.list_cs: List[Perimeter] = [self.perim0, self.perim11, self.perim21, self.perim31, self.perim32,
                                         self.perim12, self.perim22, self.perim23, self.perim33]


class ViewSetTests(BaseTests):
    objects_url: str
    create_view: any
    update_view: any
    delete_view: any
    list_view: any
    retrieve_view: any
    model: Model
    model_objects: Manager
    model_fields: List[Field]

    def check_create_case(self, case: CreateCase, other_view: any = None, **view_kwargs):
        request = self.factory.post(path=self.objects_url, data=case.json_data, format='json')
        request.jwt_access_key = "dummy_jwt_access_key"
        if case.user:
            force_authenticate(request, case.user)

        response = other_view and other_view(request, **view_kwargs) or self.__class__.create_view(request)
        response.render()

        self.assertEqual(
            response.status_code, case.status,
            msg=(f"{case.description}"
                 + (f" -> {prettify_json(response.content)}"
                    if response.content else "")),
        )

        inst = self.model_objects.filter(**case.retrieve_filter.args)\
            .exclude(**case.retrieve_filter.exclude).first()

        if case.success:
            self.check_is_created(inst, request_model=case.data, user=case.user)
        else:
            self.assertIsNone(inst)

    def check_delete_case(self, case: DeleteCase):
        obj_id = self.model_objects.create(**case.data_to_delete).pk

        request = self.factory.delete(self.objects_url)
        force_authenticate(request, case.user)
        response = self.__class__.delete_view(
            request, **{self.model._meta.pk.name: obj_id}
        )
        response.render()

        self.assertEqual(
            response.status_code, case.status,
            msg=(f"{case.description}"
                 + (f" -> {prettify_json(response.content)}"
                    if response.content else "")),
        )

        if isinstance(self.model, (BaseModel, CohortBaseModel)):
            obj = self.model_objects.filter(even_deleted=True, pk=obj_id).first()
        else:
            obj = self.model_objects.filter(pk=obj_id).first()

        if case.success:
            self.check_is_deleted(obj)
        else:
            self.assertIsNotNone(obj)
            if isinstance(self.model, (BaseModel, CohortBaseModel)):
                self.assertIsNone(obj.delete_datetime)
            obj.delete()

    def check_patch_case(self, case: PatchCase):
        obj_id = self.model_objects.create(**case.initial_data).pk
        obj = self.model_objects.get(pk=obj_id)

        request = self.factory.patch(
            self.objects_url, case.data_to_update, format='json'
        )
        force_authenticate(request, case.user)
        response = self.__class__.update_view(
            request, **{self.model._meta.pk.name: obj_id}
        )
        response.render()

        self.assertEqual(
            response.status_code, case.status,
            msg=(f"{case.description}"
                 + (f" -> {prettify_json(response.content)}"
                    if response.content else "")),
        )

        new_obj = self.model_objects.filter(pk=obj_id).first()

        if case.success:
            for field in case.data_to_update:
                f = f"manual_{field}" if \
                    field in self.manual_dupplicated_fields else field

                new_value = getattr(new_obj, f)
                new_value = getattr(new_value, 'pk', new_value)

                if f in self.unupdatable_fields:
                    self.assertNotEqual(
                        new_value, case.data_to_update.get(field),
                        f"{field} updated")
                else:
                    self.assertEqual(new_value, case.data_to_update.get(field),
                                     f"{field} not updated")
        else:
            [self.assertEqual(
                getattr(new_obj, f), getattr(obj, f), case.description
            ) for f in [fd.name for fd in self.model_fields]]

    def check_get_paged_list_case(self, case: ListCase, other_view: any = None, **view_kwargs):
        request = self.factory.get(path=case.url or self.objects_url,
                                   data=[] if case.url else case.params)
        force_authenticate(request, case.user)
        response = other_view(request, **view_kwargs) if other_view else self.__class__.list_view(request)

        response.render()
        self.assertEqual(response.status_code, case.status,
                         msg=(f"{case.title}: " + prettify_json(response.content) if response.content else ""))

        if not case.success:
            self.assertNotIn('results', response.data, f"Case {case.title}")
            return

        res = PagedResponse(response)

        self.assertEqual(res.count, len(case.to_find),
                         case.description + f'''Found: {" - ".join([f"{r.get('id')}({r.get('name')})" for r in res.results])}''')

        obj_to_find_ids = [str(obj.pk) for obj in case.to_find]
        current_obj_found_ids = [obj.get(self.model._meta.pk.name)
                                 for obj in res.results]
        obj_found_ids = current_obj_found_ids + case.previously_found_ids

        if case.page_size is not None:
            if res.next:
                self.assertEqual(
                    len(current_obj_found_ids), case.page_size
                )
                next_case = case.clone(
                    url=res.next, previously_found_ids=obj_found_ids)
                self.check_get_paged_list_case(next_case, other_view,
                                               **view_kwargs)
        else:
            self.assertCountEqual(map(str, obj_found_ids),
                                  map(str, obj_to_find_ids))

    def check_retrieve_case(self, case: RetrieveCase):
        request = self.factory.get(
            path=case.url or self.objects_url,
            data=[] if case.url else case.params)
        force_authenticate(request, case.user)
        response = self.__class__.retrieve_view(request, **case.view_params)
        response.render()
        self.assertEqual(
            response.status_code, case.status,
            msg=(f"{case.title}: "
                 + prettify_json(response.content) if response.content else ""),
        )
        res: dict = response.data

        if case.success:
            if case.to_find is not None:
                self.assertEqual(str(case.to_find.pk),
                                 str(res.get(self.model._meta.pk.name)),
                                 case.description)
            else:
                self.assertEqual(len(res), 0, case.description)


class ViewSetTestsWithBasicPerims(ViewSetTests, SimplePerimSetup):
    def setUp(self):
        super(ViewSetTestsWithBasicPerims, self).setUp()
        SimplePerimSetup.setUp(self)


class ViewSetTestsWithNumerousPerims(ViewSetTests, NumerousPerimSetup):
    def setUp(self):
        super(ViewSetTestsWithNumerousPerims, self).setUp()
        NumerousPerimSetup.setUp(self)


def random_str(length, include_pattern: str = '', with_space: bool = True):
    letters = string.ascii_lowercase + (" " if with_space else "")
    res = ''.join(random.choice(letters) for i in range(length))
    if include_pattern:
        h = int(length / 2)
        res = f"{res[:h]}{include_pattern}{res[h:]}"
    return res
