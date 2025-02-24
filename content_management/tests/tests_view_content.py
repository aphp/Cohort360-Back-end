from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.test import APITestCase

from accesses.models import Perimeter, Access, Role
from accesses.tests.base import role_full_admin_data
from admin_cohort.tests.tests_tools import new_random_user, new_user_and_profile
from content_management.models import Content, MetadataName


class ContentViewSetTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_client = APIClient()
        self.user = new_random_user()
        self.admin_user, admin_profile = new_user_and_profile()

        # generate admin rights
        perimeter_aphp = Perimeter.objects.create(
            **{'id': 9999, 'name': 'APHP', 'source_value': 'APHP', 'short_name': 'AP-HP', 'local_id': 'Local APHP',
               'type_source_value': 'AP-HP',
               'parent_id': None, 'level': 1, 'above_levels_ids': '', 'inferior_levels_ids': '0,1,2',
               'cohort_id': '9999'})
        admin_role = Role.objects.create(**role_full_admin_data)
        Access.objects.create(profile=admin_profile,
                              role=admin_role,
                              perimeter=perimeter_aphp,
                              start_datetime=timezone.now(),
                              end_datetime=timezone.now() + timedelta(weeks=1))

        self.client.force_authenticate(user=self.user)
        self.admin_client.force_authenticate(user=self.admin_user)

        self.valid_content_data = {
            'title': 'Test Content',
            'content': 'Test Content Body',
            'page': 'test-page',
            'content_type': 'BANNER_INFO'
        }

        self.content_data_with_metadata = {
            **self.valid_content_data,
            'metadata': {
                MetadataName.ORDER.value: '1',
                MetadataName.STYLE.value: 'dark'
            }
        }

        self.content = Content.objects.create(**self.valid_content_data)
        self.list_url = reverse('webcontent:contents-list')
        self.detail_url = reverse('webcontent:contents-detail', kwargs={'pk': self.content.pk})

    def test_create_content(self):
        new_content_data = {
            'title': 'New Content',
            'content': 'New Content Body',
            'page': 'new-page',
            'content_type': 'BANNER_WARNING'
        }
        response = self.admin_client.post(self.list_url, new_content_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Content.objects.count(), 2)

    def test_unauthorized_create_content(self):
        new_content_data = {
            'title': 'New Content',
            'content': 'New Content Body',
            'page': 'new-page',
            'content_type': 'BANNER_WARNING'
        }
        response = self.client.post(self.list_url, new_content_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_content_with_metadata(self):
        new_content_data = {
            'title': 'New Content',
            'content': 'New Content Body',
            'page': 'new-page',
            'content_type': 'BANNER_WARNING',
            'metadata': {'order': '1'}
        }
        response = self.admin_client.post(self.list_url, new_content_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Content.objects.count(), 2)
        self.assertEqual(response.data['metadata'], {'order': '1'})

    def test_list_content(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_retrieve_content(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], self.valid_content_data['title'])

    def test_update_content(self):
        updated_data = {
            **self.valid_content_data,
            'title': 'Updated Title'
        }
        response = self.admin_client.put(self.detail_url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Title')

    def test_unauthorized_update_content(self):
        updated_data = {
            **self.valid_content_data,
            'title': 'Updated Title'
        }
        response = self.client.put(self.detail_url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_partial_update_content(self):
        response = self.admin_client.patch(
            self.detail_url,
            {'title': 'Partially Updated Title'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Partially Updated Title')

    def test_unauthorized_partial_update_content(self):
        response = self.client.patch(
            self.detail_url,
            {'title': 'Partially Updated Title'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_content_without_changing_metadata(self):
        # First create content with metadata
        response = self.admin_client.post(
            reverse('webcontent:contents-list'),
            self.content_data_with_metadata,
            format='json'
        )
        content_id = response.data['id']
        original_metadata = response.data['metadata']

        # Update only content fields
        update_data = {
            'title': 'Updated Title',
            'content': 'Updated Content Body',
            'page': 'test-page',
            'content_type': 'BANNER_INFO'
        }
        response = self.admin_client.patch(
            reverse('webcontent:contents-detail', kwargs={'pk': content_id}),
            update_data,
            format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['title'], 'Updated Title')
        self.assertEqual(response.data['metadata'], original_metadata)

    def test_update_content_clearing_metadata(self):
        # First create content with metadata
        response = self.admin_client.post(
            reverse('webcontent:contents-list'),
            self.content_data_with_metadata,
            format='json'
        )
        content_id = response.data['id']

        # Update with empty metadata
        update_data = {
            **self.valid_content_data,
            'metadata': {}
        }
        response = self.admin_client.put(
            reverse('webcontent:contents-detail', kwargs={'pk': content_id}),
            update_data,
            format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['metadata']), 0)

    def test_delete_content(self):
        response = self.admin_client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Check soft delete
        content = Content.objects.get(pk=self.content.pk)
        self.assertIsNotNone(content.deleted_at)

    def test_unauthorized_delete_content(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_by_content_type(self):
        Content.objects.create(
            title='Blog Post',
            content='Blog Content',
            page='blog',
            content_type='BANNER_ERROR'
        )

        response = self.client.get(f'{self.list_url}?content_type=BANNER_ERROR')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['content_type'], 'BANNER_ERROR')

    def test_filter_by_page(self):
        Content.objects.create(
            title='Blog Post',
            content='Blog Content',
            page='blog',
            content_type='BANNER_ERROR'
        )

        response = self.client.get(f'{self.list_url}?page_source=blog')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['page'], 'blog')

    def test_content_types_endpoint(self):
        response = self.client.get(reverse('webcontent:contents-content-types'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('BANNER_WARNING', response.data)
        self.assertIn('BANNER_INFO', response.data)
        self.assertIn('BANNER_ERROR', response.data)


class UnauthenticatedContentViewSetTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.valid_content_data = {
            'title': 'Test Content',
            'content': 'Test Content Body',
            'page': 'test-page',
            'content_type': 'BANNER_ERROR'
        }
        self.list_url = reverse('webcontent:contents-list')

    def test_unauthenticated_list(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_create(self):
        response = self.client.post(self.list_url, self.valid_content_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
