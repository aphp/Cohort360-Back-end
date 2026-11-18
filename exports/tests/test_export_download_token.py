from unittest import mock

from django.core import signing
from django.http import StreamingHttpResponse
from django.test.utils import override_settings
from rest_framework import status
from rest_framework.test import force_authenticate
from rest_framework_tracking.models import APIRequestLog

from admin_cohort.types import JobStatus
from exports.exceptions import BadRequestError, FilesNoLongerAvailable, HdfsServerUnreachable, StorageProviderException
from exports.models import Export
from exports.services.export import export_service
from exports.services.export_download_token import (
    ExportDownloadToken,
    create_export_download_token,
    read_export_download_token,
)
from exports.tests.base_test import ExportsTestBase
from exports.views import ExportViewSet


class ExportDownloadTokenTest(ExportsTestBase):
    view_set = ExportViewSet
    view_root = "exports:exports"
    model = Export

    def setUp(self):
        super().setUp()
        self.export = Export.objects.create(
            output_format=self.export_type,
            owner=self.exporter_user,
            target_name="12345_09092023_151500",
            request_job_status=JobStatus.finished,
        )
        self.other_export = Export.objects.create(
            output_format=self.export_type,
            owner=self.exporter_user,
            target_name="67890_09092023_151500",
            request_job_status=JobStatus.finished,
        )
        self.download_token_view = self.view_set.as_view({"post": "download_token"})
        self.download_view = self.view_set.as_view({"get": "download"})
        self.download_token_url = f"/exports/{self.export.uuid}/download-token/"
        self.download_url = f"/exports/{self.export.uuid}/download/"

    def call_download_token_view(self, request_user, export=None):
        export = export or self.export
        request = self.make_request(url=f"/exports/{export.uuid}/download-token/", http_verb="post", request_user=request_user)
        return self.download_token_view(request, uuid=export.uuid)

    def call_download_view_with_token(self, token: str, export=None):
        # no force_authenticate: the request is authenticated by the token only, as in the browser
        export = export or self.export
        request = self.factory.get(f"/exports/{export.uuid}/download/", {"token": token})
        with mock.patch.object(export_service, "download", return_value=StreamingHttpResponse(streaming_content=iter([b"chunk"]))):
            return self.download_view(request, uuid=export.uuid)

    # token

    def test_read_token_returns_user_and_export(self):
        token = create_export_download_token(user=self.exporter_user, export=self.export)
        self.assertEqual(
            read_export_download_token(token),
            ExportDownloadToken(username=self.exporter_user.pk, export_uuid=str(self.export.uuid)),
        )

    @override_settings(EXPORT_DOWNLOAD_TOKEN_MAX_AGE=-1)
    def test_read_expired_token_fails(self):
        token = create_export_download_token(user=self.exporter_user, export=self.export)
        with self.assertRaises(signing.SignatureExpired):
            read_export_download_token(token)

    def test_read_token_signed_with_another_salt_fails(self):
        token = signing.TimestampSigner(salt="another.salt").sign_object({"user": self.exporter_user.pk, "export": str(self.export.uuid)})
        with self.assertRaises(signing.BadSignature):
            read_export_download_token(token)

    # POST download-token

    @mock.patch("exports.services.export.ExportDownloader")
    def test_owner_gets_a_token(self, mock_downloader):
        mock_downloader.return_value.check_downloadable.return_value = 11111
        response = self.call_download_token_view(request_user=self.exporter_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            read_export_download_token(response.data["token"]),
            ExportDownloadToken(username=self.exporter_user.pk, export_uuid=str(self.export.uuid)),
        )

    @mock.patch("exports.services.export.ExportDownloader")
    def test_non_owner_gets_no_token(self, mock_downloader):
        response = self.call_download_token_view(request_user=self.user_without_rights)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        mock_downloader.return_value.check_downloadable.assert_not_called()

    @mock.patch("exports.services.export.ExportDownloader")
    def test_no_token_when_export_not_downloadable(self, mock_downloader):
        cases = [
            (BadRequestError("not downloadable"), status.HTTP_400_BAD_REQUEST),
            (FilesNoLongerAvailable("files were cleaned"), status.HTTP_400_BAD_REQUEST),
            (HdfsServerUnreachable("No HDFS servers available: namenode-01"), status.HTTP_503_SERVICE_UNAVAILABLE),
            (StorageProviderException("file not found on namenode-01"), status.HTTP_500_INTERNAL_SERVER_ERROR),
        ]
        for error, expected_status in cases:
            with self.subTest(error=type(error).__name__):
                mock_downloader.return_value.check_downloadable.side_effect = error
                response = self.call_download_token_view(request_user=self.exporter_user)
                self.assertEqual(response.status_code, expected_status)
                self.assertNotIn("token", response.data)
                self.assertNotIn("namenode-01", response.data)

    # GET download?token=

    def test_download_with_valid_token(self):
        token = create_export_download_token(user=self.exporter_user, export=self.export)
        response = self.call_download_view_with_token(token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @override_settings(EXPORT_DOWNLOAD_TOKEN_MAX_AGE=-1)
    def test_download_with_expired_token(self):
        token = create_export_download_token(user=self.exporter_user, export=self.export)
        response = self.call_download_view_with_token(token)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_download_with_tampered_token(self):
        token = create_export_download_token(user=self.exporter_user, export=self.export)
        response = self.call_download_view_with_token(f"{token[:-1]}{'A' if token[-1] != 'A' else 'B'}")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_download_with_token_of_another_export(self):
        token = create_export_download_token(user=self.exporter_user, export=self.other_export)
        response = self.call_download_view_with_token(token, export=self.export)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_download_with_token_of_a_non_owner(self):
        token = create_export_download_token(user=self.user_without_rights, export=self.export)
        response = self.call_download_view_with_token(token)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_token_does_not_open_other_actions(self):
        token = create_export_download_token(user=self.exporter_user, export=self.export)
        request = self.factory.get(f"/exports/{self.export.uuid}/", {"token": token})
        response = self.retrieve_view(request, uuid=self.export.uuid)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_download_without_token_nor_bearer(self):
        request = self.factory.get(self.download_url)
        response = self.download_view(request, uuid=self.export.uuid)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_download_with_bearer_still_works(self):
        request = self.factory.get(self.download_url)
        force_authenticate(request, self.exporter_user)
        with mock.patch.object(export_service, "download", return_value=StreamingHttpResponse(streaming_content=iter([b"chunk"]))):
            response = self.download_view(request, uuid=self.export.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_download_log_masks_token_and_keeps_username(self):
        token = create_export_download_token(user=self.exporter_user, export=self.export)
        self.call_download_view_with_token(token)
        log = APIRequestLog.objects.filter(path=self.download_url).latest("requested_at")
        self.assertEqual(log.user, self.exporter_user)
        self.assertNotIn(token, str(log.query_params))
        self.assertIn("token", str(log.query_params))
