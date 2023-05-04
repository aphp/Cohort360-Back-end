
from rest_framework import status
from rest_framework.test import APITestCase


class LoginTests(APITestCase):

    def setUp(self):
        self.login_url = '/accounts/login/'
        self.login_data = {"username": "userx", "password": "psswd"}

    def test_login_with_wrong_credentials(self):
        response = self.client.post(path=self.login_url, data=self.login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # WIP
    # @mock.patch("admin_cohort.views.LoginView.post")
    # def test_login_unavailable_jwt(self, mock_super_post: MagicMock):
    #     mock_super_post.side_effect = ServerError("JWT server unavailable")
    #     response = self.client.post(path=self.login_url, data=self.login_data, format='json')
    #     mock_super_post.assert_called()
    #     self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
