from json import JSONDecodeError
from unittest.mock import patch, Mock

from django.test import TestCase
from rest_framework import status
from rest_framework.exceptions import APIException

from admin_cohort.tools.hooks import check_user_identity


class HooksTests(TestCase):

    @patch('admin_cohort.tools.hooks.requests.post')
    def test_check_user_identity_success(self, mock_post):
        test_username = "1234567"
        mock_response = Mock()
        mock_response.status_code = status.HTTP_200_OK
        mock_response.json.return_value = {
            "data": {
                "attributes": {
                    "givenName": "Firstname",
                    "sn": "LASTNAME",
                    "cn": test_username,
                    "mail": "email.test@backend.com"
                }
            }
        }
        mock_post.return_value = mock_response
        res = check_user_identity(username=test_username)
        self.assertIsNotNone(res)
        self.assertEqual(res["username"], test_username)
        self.assertTrue("firstname" in res)
        self.assertTrue("lastname" in res)
        self.assertTrue("email" in res)

    @patch('admin_cohort.tools.hooks.requests.post')
    def test_check_user_identity_not_found(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = status.HTTP_404_NOT_FOUND
        mock_post.return_value = mock_response
        res = check_user_identity(username="1234567")
        self.assertIsNone(res)

    @patch('admin_cohort.tools.hooks.requests.post')
    def test_check_user_identity_error(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        mock_post.return_value = mock_response
        with self.assertRaises(APIException):
            _ = check_user_identity(username="1234567")

    @patch('admin_cohort.tools.hooks.requests.post')
    def test_check_user_identity_json_error(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = status.HTTP_200_OK
        mock_response.json.side_effect = JSONDecodeError("","",0)
        mock_post.return_value = mock_response
        with self.assertRaises(APIException):
            _ = check_user_identity(username="1234567")

    @patch('admin_cohort.tools.hooks.requests.post')
    def test_check_user_identity_key_error(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = status.HTTP_200_OK
        mock_response.json.return_value = {
            "data": {
                "attributes": {}    # missing keys
            }
        }
        mock_post.return_value = mock_response
        with self.assertRaises(APIException):
            _ = check_user_identity(username="1234567")
