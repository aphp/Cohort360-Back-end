import random
from datetime import timedelta
from os import environ
from pathlib import Path
from typing import List
from unittest.mock import patch

from django.core.mail import EmailMessage
from django.utils import timezone
from rest_framework import status
from rest_framework.test import force_authenticate

from admin_cohort.models import User
from admin_cohort.settings import SHARED_FOLDER_NAME
from admin_cohort.tools import prettify_json
from admin_cohort.tools.tests_tools import CaseRetrieveFilter, CreateCase, random_str, ListCase, RetrieveCase, \
    DeleteCase, PatchCase
from cohort.models import RequestQuerySnapshot, Request, Folder
from cohort.tests.tests_view_requests import RequestsTests, ShareCase
from cohort.views import RequestQuerySnapshotViewSet, NestedRqsViewSet


class RqsCaseRetrieveFilter(CaseRetrieveFilter):
    def __init__(self, serialized_query: str = "", **kwargs):
        self.serialized_query = serialized_query
        super(RqsCaseRetrieveFilter, self).__init__(**kwargs)


class RqsCreateCase(CreateCase):
    def __init__(self, **kwargs):
        super(RqsCreateCase, self).__init__(**kwargs)


class RqsTests(RequestsTests):
    unupdatable_fields = ["owner", "request", "uuid", "previous_snapshot",
                          "shared_by",
                          "created_at", "modified_at", "deleted"]
    unsettable_default_fields = dict()
    unsettable_fields = ["owner", "uuid", "shared_by",
                         "created_at", "modified_at", "deleted", ]
    manual_dupplicated_fields = []

    objects_url = "cohort/request-query-snapshots"
    retrieve_view = RequestQuerySnapshotViewSet.as_view({'get': 'retrieve'})
    list_view = RequestQuerySnapshotViewSet.as_view({'get': 'list'})
    create_view = RequestQuerySnapshotViewSet.as_view({'post': 'create'})
    delete_view = RequestQuerySnapshotViewSet.as_view({'delete': 'destroy'})
    update_view = RequestQuerySnapshotViewSet.as_view(
        {'patch': 'partial_update'})
    share_view = RequestQuerySnapshotViewSet.as_view({'post': 'share'})
    model = RequestQuerySnapshot
    model_objects = RequestQuerySnapshot.objects
    model_fields = RequestQuerySnapshot._meta.fields

    def setUp(self):
        super(RqsTests, self).setUp()
        self.user1_req1 = Request.objects.create(
            owner=self.user1,
            name="Request 1",
            description="Request 1 from user 1",
            parent_folder=self.user1_folder1
        )
        self.user1_req2 = Request.objects.create(
            owner=self.user1,
            name="Request 2",
            description="Request 2 from user 1",
            parent_folder=self.user1_folder2
        )
        self.user2_req1 = Request.objects.create(
            owner=self.user2,
            name="Request 1",
            description="Request 1 from user 2",
            parent_folder=self.user2_folder1
        )
        self.user2_req2 = Request.objects.create(
            owner=self.user2,
            name="Request 2",
            description="Request 2 from user 2",
            parent_folder=self.user2_folder2
        )
        self.requests = [self.user1_req1, self.user1_req2,
                         self.user2_req1, self.user2_req2]


class RqsGetTests(RqsTests):
    def setUp(self):
        super(RqsGetTests, self).setUp()
        self.str_pattern = "aAa"
        self.folders: List[Folder] = sum((list(u.folders.all())
                                          for u in self.users), [])
        base_rqss: List[RequestQuerySnapshot] = []

        def random_json():
            return (f'{"{"}"{random_str(5)}": "'
                    + random_str(20, random.random() > .5 and self.str_pattern)
                    + '"}')

        for r in self.requests:
            base_rqss.append(RequestQuerySnapshot(
                owner=r.owner,
                request=r,
                serialized_query=random_json(),
                shared_by=(next(u for u in self.users if u != r.owner)
                           if random.random() > .5 else None),
            ))
        RequestQuerySnapshot.objects.bulk_create(base_rqss)

        new_rqss: List[RequestQuerySnapshot] = []
        for i in range(300):
            prev = random.choice(base_rqss)
            new_rqss.append(RequestQuerySnapshot(
                owner=prev.owner,
                request=prev.request,
                serialized_query=random_json(),
                shared_by=(next(u for u in self.users if u != prev.owner)
                           if random.random() > .5 else None),
            ))
        RequestQuerySnapshot.objects.bulk_create(new_rqss)
        self.rqss = base_rqss + new_rqss

    def test_list(self):
        # As a user, I can list the RQS I own
        case = ListCase(
            to_find=[r for r in self.rqss if r.owner == self.user1],
            user=self.user1,
            success=True,
            status=status.HTTP_200_OK
        )
        self.check_get_paged_list_case(case)

    def test_retrieve(self):
        # As a user, I can retrieve a single RQS I own
        to_find = [f for f in self.rqss if f.owner == self.user1][0]
        case = RetrieveCase(
            to_find=to_find,
            view_params=dict(uuid=to_find.pk),
            user=self.user1,
            success=True,
            status=status.HTTP_200_OK
        )
        self.check_retrieve_case(case)

    def test_error_get_not_owned(self):
        # As a user, I cannot retrieve a single RQS I do not own
        to_find = [f for f in self.rqss if f.owner == self.user2][0]
        case = RetrieveCase(
            to_find=to_find,
            view_params=dict(uuid=to_find.pk),
            user=self.user1,
            success=False,
            status=status.HTTP_404_NOT_FOUND
        )
        self.check_retrieve_case(case)

    def test_list_with_filters(self):
        # As a user, I can list the RQSs I own applying filters
        basic_case = ListCase(user=self.user1, success=True,
                              status=status.HTTP_200_OK)
        user1_rqss = [f for f in self.rqss if f.owner == self.user1]
        folder = self.user1.folders.first()
        req = folder.requests.first()
        prev_rqs = req.query_snapshots.first()
        cases = [
            basic_case.clone(
                params=dict(shared_by=self.user2.pk),
                to_find=[rqs for rqs in user1_rqss
                         if rqs.shared_by == self.user2],
            ),
            basic_case.clone(
                params=dict(search=self.str_pattern),
                to_find=[rqs for rqs in user1_rqss
                         if self.str_pattern.lower()
                         in rqs.serialized_query.lower()],
            ),
            basic_case.clone(
                params=dict(previous_snapshot=prev_rqs.pk),
                to_find=list(prev_rqs.next_snapshots.all()),
            ),
            basic_case.clone(
                params=dict(request=req.pk),
                to_find=list(req.query_snapshots.all()),
            ),
            basic_case.clone(
                params=dict(request__parent_folder=folder.pk),
                to_find=sum((list(r.query_snapshots.all())
                             for r in folder.requests.all()), []),
            ),
        ]
        [self.check_get_paged_list_case(case) for case in cases]

    def test_rest_get_list_from_request(self):
        # As a user, I can get the list of RQSs from the request they are
        # bound to
        req = self.user1.folders.first().requests.first()

        self.check_get_paged_list_case(ListCase(status=status.HTTP_200_OK,
                                                success=True,
                                                user=self.user1,
                                                to_find=list(req.query_snapshots.all())),
                                       other_view=NestedRqsViewSet.as_view({'get': 'list'}),
                                       request_id=req.pk)

    def test_rest_get_list_from_previous_rqs(self):
        # As a user, I can get the list of RQSs from the previous RQS they are
        # bound to
        prev_rqs = self.user1.folders.first().requests.first() \
            .query_snapshots.first()

        self.check_get_paged_list_case(ListCase(status=status.HTTP_200_OK,
                                                success=True,
                                                user=self.user1,
                                                to_find=list(prev_rqs.next_snapshots.all())),
                                       other_view=NestedRqsViewSet.as_view({'get': 'list'}),
                                       previous_snapshot=prev_rqs.pk)


class RqsCreateTests(RqsTests):

    def check_create_case_with_mock(self, case: RqsCreateCase, other_view: any, view_kwargs: dict):

        super(RqsCreateTests, self).check_create_case(
            case, other_view, **(view_kwargs or {}))

    def check_create_case(self, case: RqsCreateCase, other_view: any = None,
                          **view_kwargs):
        return self.check_create_case_with_mock(
            case, other_view=other_view or None, view_kwargs=view_kwargs)

    def setUp(self):
        super(RqsCreateTests, self).setUp()
        #          user1_snap1
        #           /       \
        # user1_b1_snap2  user1_b2_snap2 (active) (saved)
        #                         |
        #                 user1_b2_snap3 (active)

        self.user1_req1_snap1 = RequestQuerySnapshot.objects.create(
            owner=self.user1,
            request=self.user1_req1,
        )
        self.user1_req1_branch1_snap2 = RequestQuerySnapshot.objects.create(
            owner=self.user1,
            request=self.user1_req1,
            previous_snapshot=self.user1_req1_snap1,
            serialized_query='{"perimeter": "Terra"}',
        )

        self.test_query = '{"test": "query", "sourcePopulation": {"caresiteCohortList": ["1", "2", "3"]}}'
        self.basic_data = dict(
            request=self.user1_req2.pk,
            serialized_query=self.test_query,
        )
        self.basic_case = RqsCreateCase(
            success=True,
            status=status.HTTP_201_CREATED,
            user=self.user1,
            data=self.basic_data,
            retrieve_filter=RqsCaseRetrieveFilter(
                serialized_query=self.test_query),
        )
        self.basic_err_case = self.basic_case.clone(
            success=False,
            status=status.HTTP_400_BAD_REQUEST,
        )

    def test_create(self):
        # As a user, I can create a RQS
        self.check_create_case(self.basic_case)

    def test_create_from_request(self):
        # As a user, I can create a RQS
        self.check_create_case(self.basic_case.clone(
            data={**self.basic_data, 'request': None}
        ), NestedRqsViewSet.as_view({'post': 'create'}),
            request_id=self.user1_req2.pk)

    def test_create_with_unread_fields(self):
        # As a user, I can create a request
        self.check_create_case(self.basic_case.clone(
            data={**self.basic_data,
                  'created_at': timezone.now() + timedelta(hours=1),
                  'modified_at': timezone.now() + timedelta(hours=1),
                  'deleted': timezone.now() + timedelta(hours=1),
                  'shared_by': self.user2.pk},
        ))

    def test_create_on_previous(self):
        # As a user, I can create a RQS specifying a previous snapshot
        self.check_create_case(self.basic_case.clone(
            data={'serialized_query': self.test_query,
                  'previous_snapshot': self.user1_req1_snap1.pk},
        ))

    def test_create_from_previous(self):
        # As a user, I can create a RQS specifying a previous snapshot
        # using nestedViewSet
        self.check_create_case(case=self.basic_case.clone(data={'serialized_query': self.test_query}),
                               other_view=NestedRqsViewSet.as_view({'post': 'create'}),
                               previous_snapshot=self.user1_req1_snap1.pk)

    def test_error_create_missing_field(self):
        # As a user, I cannot create a RQS if some fields are missing
        case = self.basic_err_case.clone(data={**self.basic_data, 'serialized_query': None})
        self.check_create_case(case)

    def test_error_create_missing_both_request_previous(self):
        # As a user, I cannot create a RQS not specifying either
        # previous snapshot or request
        self.check_create_case(self.basic_err_case.clone(
            data=dict(serialized_query=self.test_query),
        ))

    def test_error_create_with_other_owner(self):
        # As a user, I cannot create a RQS providing another user as owner
        self.check_create_case(self.basic_err_case.clone(
            data={**self.basic_data, 'owner': self.user2.pk},
        ))

    def test_error_create_with_not_owned_request(self):
        # As a user, I cannot create a RQS providing a request I don't own
        self.check_create_case(self.basic_err_case.clone(
            data={**self.basic_data, 'request': self.user2_req1.pk},
        ))

    def test_error_create_unmatching_request_previous(self):
        # As a user, I cannot create a RQS providing both request
        # and previous_snapshot if thei are not bound to each other
        self.check_create_case(self.basic_err_case.clone(
            data={**self.basic_data,
                  'previous_snapshot': self.user1_req1_snap1.pk},
        ))

    def test_error_create_missing_previous_if_request_not_empty(self):
        # As a user, I cannot create a RQS not specifying either
        # previous snapshot if the request alreay has query_snapshots
        self.check_create_case(self.basic_err_case.clone(
            data={**self.basic_data, 'request': self.user1_req1.pk},
        ))

    # def test_error_create_unvalid_query(self):
    #     # As a user, I cannot create a RQS if the query server deny the query
    #     # or the query is not a json
    #     case = self.basic_err_case.clone(data={**self.basic_data,
    #                                            'serialized_query': "not_json"},
    #                                      retrieve_filter=RqsCaseRetrieveFilter(serialized_query="not_json"))
    #     self.check_create_case(case)

    # def test_error_create_with_forbidden_field(self):
    #     # As a user, I cannot create a request with some forbidden field/value
    #     cases = (self.basic_case.clone(
    #         title=f"with '{k}': {v}",
    #         data={**self.basic_data, k: v},
    #         success=False,
    #         status=status.HTTP_400_BAD_REQUEST,
    #     ) for (k, v) in dict(
    #         parent_folder=self.user2_folder1.pk,
    #     ).items())
    #     [self.check_create_case(case) for case in cases]


class RqsShareTests(RqsTests):
    def setUp(self):
        super(RqsShareTests, self).setUp()
        self.user1_req1_snapshot1 = RequestQuerySnapshot.objects.create(
            owner=self.user1,
            request=self.user1_req1,
            serialized_query="{}",
        )

        self.basic_case = ShareCase(
            initial_data=dict(
                owner=self.user1, request=self.user1_req1,
                previous_snapshot=self.user1_req1_snapshot1,
                serialized_query='{"test": "success"}',
            ),
            success=True,
            status=status.HTTP_201_CREATED,
            user=self.user1,
            recipients=[self.user2, self.user1],
        )

    def check_share_case(self, case: ShareCase, ):
        obj = RequestQuerySnapshot.objects.create(**case.initial_data)

        data = dict(recipients=",".join([u.pk for u in case.recipients or []]))
        if case.new_name:
            data['name'] = case.new_name

        request = self.factory.post(f"{self.objects_url}/{obj.pk}/share",
                                    data=data, format='json')
        if case.user:
            force_authenticate(request, case.user)

        response = self.__class__.share_view(request, uuid=obj.pk)
        response.render()

        msg = (f"{case.description}"
               + (f" -> {prettify_json(response.content)}"
                  if response.content else ""))
        self.assertEqual(response.status_code, case.status, msg=msg)

        if case.success:
            for u in case.recipients:
                rqs = RequestQuerySnapshot.objects.filter(
                    request__parent_folder__name=SHARED_FOLDER_NAME,
                    request__name=case.new_name or obj.request.name,
                    request__shared_by=case.user,
                    previous_snapshot__isnull=True,
                    owner=u,
                    shared_by=case.user
                ).first()
                self.assertIsNotNone(rqs, msg=f"Recipient: {u} - {msg}")
        else:
            if case.recipients is not None:
                self.assertIsNone(RequestQuerySnapshot.objects.filter(
                    owner__in=case.recipients,
                    shared_by=case.user
                ).first(), msg=msg)

    def test_share_rqs(self):
        # As a user, I can share a request query snapshot to other users
        # (including myself). It will create new requests,
        # with RQSs, all with shared_by=me
        self.check_share_case(self.basic_case)

    def test_share_rqs_with_new_name(self):
        # As a user, I can share a request query snapshot to other users
        # providing a new name
        self.check_share_case(self.basic_case.clone(
            new_name="new_request",
        ))

    def check_mail(self, from_email: str, to_emails: List[str], body: str):
        def check_mail_sent(me):
            self.assertEqual(me.body, body)
            self.assertEqual(me.from_email, from_email)
            self.assertEqual(me.to, to_emails)

        return check_mail_sent

    def test_mail_sending(self):
        with open(Path(__file__).resolve().parent.joinpath("resources/email_shared_request.txt"), "r") as fh:
            email_content = fh.read()
        with patch.object(EmailMessage, 'send', self.check_mail(
                from_email=environ.get("EMAIL_SENDER_ADDRESS"),
                to_emails=[self.user2.email],
                body=email_content
        )):
            self.check_share_case(self.basic_case.clone(
                recipients=[self.user2]
            ))

    def test_error_share_unknown_users(self):
        # As a user, I cannot share a RQS with not existing recipients
        self.check_share_case(self.basic_case.clone(
            status=status.HTTP_400_BAD_REQUEST,
            success=False,
            recipients=[self.user2, User(pk="wrong", email="n@aphp.fr",
                                         firstname="not", lastname="existing")]
        ))

    def test_error_missing_recipients(self):
        # As a user, I cannot share a RQS without recipients
        self.check_share_case(self.basic_case.clone(status=status.HTTP_400_BAD_REQUEST,
                                                    success=False,
                                                    recipients=None))


class RqsDeleteTests(RqsTests):
    def test_error_delete_rqs(self):
        # As a user, I cannot delete a rqs, even if I own it
        self.check_delete_case(DeleteCase(
            data_to_delete=dict(
                request=self.user1_req2,
                serialized_query="{}",
                owner=self.user1,
            ),
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
            success=False,
            user=self.user1,
        ))


class RqsUpdateTests(RqsTests):
    def test_error_update_rqs(self):
        # As a user, I cannot update a rqs, even if I own it
        self.check_patch_case(PatchCase(
            initial_data=dict(
                request=self.user1_req2,
                serialized_query="{}",
                owner=self.user1,
            ),
            data_to_update=dict(serialized_query="{}"),
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
            success=False,
            user=self.user1,
        ))
