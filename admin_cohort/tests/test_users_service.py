from unittest.mock import patch

from django.test import TestCase
from rest_framework.exceptions import APIException

from admin_cohort.apps import AdminCohortConfig
from admin_cohort.services.users import users_service


class UsersServiceTests(TestCase):


    def test_hash_password_success(self):
        hashed = users_service.hash_password("<PASSWORD>")
        self.assertIsNotNone(hashed)

    def test_hash_password_error(self):
        with self.assertRaises(ValueError):
            _ = users_service.hash_password(None)

    @patch.object(AdminCohortConfig, attribute="HOOKS", new={})
    @patch('admin_cohort.services.users._logger.error')
    def test_try_hooks_no_hooks_configured(self, mock_logger):
        res = users_service.try_hooks(username="1234567")
        mock_logger.assert_called_once()
        self.assertIsNone(res)

    @patch.object(AdminCohortConfig, attribute="HOOKS", new={"USER_IDENTITY": ["some.bad.path.to.hook"]})
    @patch('admin_cohort.services.users._logger.error')
    def test_try_hooks_hook_improperly_configured(self, mock_logger):
        res = users_service.try_hooks(username="1234567")
        mock_logger.assert_called()
        self.assertEqual(mock_logger.call_count, 2)
        self.assertIsNone(res)

    @patch.object(AdminCohortConfig, attribute="HOOKS", new={"USER_IDENTITY": ["path.to.some.hook"]})
    @patch('admin_cohort.services.users.import_string')
    @patch('admin_cohort.services.users._logger.error')
    def test_try_hooks_hook_raises_error(self, mock_logger, mock_import_string):
        def raise_error(username: str):
            raise APIException()
        mock_import_string.return_value = raise_error
        res = users_service.try_hooks(username="1234567")
        mock_logger.assert_called()
        self.assertEqual(mock_logger.call_count, 2)
        self.assertIsNone(res)

    @patch.object(AdminCohortConfig, attribute="HOOKS", new={"USER_IDENTITY": ["path.to.some.hook"]})
    @patch('admin_cohort.services.users.import_string')
    @patch('admin_cohort.services.users._logger.error')
    def test_try_hooks_return_none(self, mock_logger, mock_import_string):
        mock_import_string.return_value = lambda username: None
        res = users_service.try_hooks(username="1234567")
        mock_logger.assert_called_once()
        self.assertIsNone(res)

    @patch.object(AdminCohortConfig, attribute="HOOKS", new={"USER_IDENTITY": ["path.to.some.valid.hook"]})
    @patch('admin_cohort.services.users.import_string')
    @patch('admin_cohort.services.users._logger.error')
    def test_try_hooks_return_value(self, mock_logger, mock_import_string):
        test_username = "1234567"
        mock_import_string.return_value = lambda username: {"username": test_username}
        res = users_service.try_hooks(username=test_username)
        mock_logger.assert_not_called()
        self.assertTrue(type(res) is dict)
        self.assertEqual(res["username"], test_username)

