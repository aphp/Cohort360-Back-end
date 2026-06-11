from unittest import TestCase, mock
from unittest.mock import MagicMock

from botocore.exceptions import ClientError

from exports.exceptions import HdfsServerUnreachable, StorageProviderException
from exports.services.storage_provider import (
    S3StorageProvider,
    get_storage_provider,
    is_s3_path,
    storage_scheme,
)


class TestS3PathHelpers(TestCase):
    def test_is_s3_path(self):
        self.assertTrue(is_s3_path("s3a://bucket/key.zip"))
        self.assertTrue(is_s3_path("s3://bucket/key.zip"))
        self.assertFalse(is_s3_path("hdfs://namenode/user/exports/file.zip"))
        self.assertFalse(is_s3_path("/user/exports/file.zip"))

    def test_storage_scheme(self):
        self.assertEqual(storage_scheme("s3a://bucket/key.zip"), "s3")
        self.assertEqual(storage_scheme("/user/exports/file.zip"), "hdfs")

    def test_hdfs_unreachable_is_a_storage_provider_exception(self):
        # ensures the view / services that catch StorageProviderException also handle it
        self.assertTrue(issubclass(HdfsServerUnreachable, StorageProviderException))


@mock.patch("exports.services.storage_provider.boto3")
class TestS3StorageProvider(TestCase):
    def _build_provider(self, mock_boto3, bucket="bucket"):
        client = MagicMock()
        mock_boto3.client.return_value = client
        provider = S3StorageProvider(endpoint_url="http://s3", access_key="ak", secret_key="sk", bucket=bucket)
        return provider, client

    @staticmethod
    def _client_error(operation):
        return ClientError({"Error": {"Code": "NoSuchKey", "Message": "missing"}}, operation)

    def test_object_key(self, mock_boto3):
        provider, _ = self._build_provider(mock_boto3)
        self.assertEqual(provider.object_key("s3a://bucket/exports/123.zip"), "exports/123.zip")
        self.assertEqual(provider.object_key("s3://bucket/exports/123.zip"), "exports/123.zip")
        # a key segment that happens to equal the bucket name is preserved
        self.assertEqual(provider.object_key("s3a://bucket/bucket/123.zip"), "bucket/123.zip")

    def test_object_key_requires_bucket(self, mock_boto3):
        provider, _ = self._build_provider(mock_boto3, bucket=None)
        with self.assertRaises(StorageProviderException):
            provider.object_key("s3a://bucket/exports/123.zip")

    def test_object_key_rejects_bucket_mismatch(self, mock_boto3):
        provider, _ = self._build_provider(mock_boto3, bucket="bucket")
        with self.assertRaises(StorageProviderException):
            provider.object_key("s3a://other-bucket/exports/123.zip")

    def test_object_key_rejects_malformed_path(self, mock_boto3):
        provider, _ = self._build_provider(mock_boto3)
        for bad in ("s3a://bucket", "s3a://bucket/", "s3a://"):
            with self.assertRaises(StorageProviderException):
                provider.object_key(bad)

    def test_object_key_rejects_traversal(self, mock_boto3):
        provider, _ = self._build_provider(mock_boto3)
        for bad in ("s3a://bucket/../secret.zip", "s3a://bucket/exports//123.zip", "s3a://bucket/a/../../b.zip"):
            with self.assertRaises(StorageProviderException):
                provider.object_key(bad)

    def test_get_file_size(self, mock_boto3):
        provider, client = self._build_provider(mock_boto3)
        client.head_object.return_value = {"ContentLength": 4242}
        size = provider.get_file_size("s3a://bucket/exports/123.zip")
        self.assertEqual(size, 4242)
        client.head_object.assert_called_once_with(Bucket="bucket", Key="exports/123.zip")

    def test_get_file_size_wraps_client_error(self, mock_boto3):
        provider, client = self._build_provider(mock_boto3)
        client.head_object.side_effect = self._client_error("HeadObject")
        with self.assertRaises(StorageProviderException):
            provider.get_file_size("s3a://bucket/exports/123.zip")

    def test_stream_file(self, mock_boto3):
        provider, client = self._build_provider(mock_boto3)
        body = MagicMock()
        body.iter_chunks.return_value = iter([b"a", b"b"])
        client.get_object.return_value = {"Body": body}
        with provider.stream_file("s3a://bucket/key.zip") as chunks:
            self.assertEqual(list(chunks), [b"a", b"b"])
        client.get_object.assert_called_once_with(Bucket="bucket", Key="key.zip")
        body.close.assert_called_once()

    def test_stream_file_wraps_client_error(self, mock_boto3):
        provider, client = self._build_provider(mock_boto3)
        client.get_object.side_effect = self._client_error("GetObject")
        with self.assertRaises(StorageProviderException):
            with provider.stream_file("s3a://bucket/key.zip"):
                pass

    def test_stream_file_wraps_mid_stream_error(self, mock_boto3):
        provider, client = self._build_provider(mock_boto3)
        body = MagicMock()

        def chunks(chunk_size):
            yield b"a"
            raise self._client_error("GetObject")

        body.iter_chunks.side_effect = chunks
        client.get_object.return_value = {"Body": body}
        with self.assertRaises(StorageProviderException):
            with provider.stream_file("s3a://bucket/key.zip") as stream:
                list(stream)
        body.close.assert_called_once()

    def test_delete_file(self, mock_boto3):
        provider, client = self._build_provider(mock_boto3)
        provider.delete_file("s3a://bucket/key.zip")
        client.delete_object.assert_called_once_with(Bucket="bucket", Key="key.zip")

    def test_delete_file_wraps_client_error(self, mock_boto3):
        provider, client = self._build_provider(mock_boto3)
        client.delete_object.side_effect = self._client_error("DeleteObject")
        with self.assertRaises(StorageProviderException):
            provider.delete_file("s3a://bucket/key.zip")

    def test_uses_path_addressing_style(self, mock_boto3):
        self._build_provider(mock_boto3)
        _, kwargs = mock_boto3.client.call_args
        self.assertEqual(kwargs["config"].s3["addressing_style"], "path")


class TestGetStorageProvider(TestCase):
    @mock.patch.dict(
        "os.environ",
        {"S3_ENDPOINT_URL": "http://s3", "S3_ACCESS_KEY": "ak", "S3_SECRET_KEY": "sk", "S3_BUCKET": "bucket"},
    )
    @mock.patch("exports.services.storage_provider.boto3")
    def test_returns_s3_provider_for_s3_path(self, mock_boto3):
        provider = get_storage_provider("s3a://bucket/key.zip")
        self.assertIsInstance(provider, S3StorageProvider)
        self.assertEqual(provider.name, "S3")
        self.assertEqual(provider.bucket, "bucket")

    @mock.patch.dict("os.environ", {"S3_BUCKET": "bucket", "S3_VERIFY_SSL": "false", "S3_CA_BUNDLE": ""})
    @mock.patch("exports.services.storage_provider.boto3")
    def test_verify_disabled_via_env(self, mock_boto3):
        get_storage_provider("s3a://bucket/key.zip")
        _, kwargs = mock_boto3.client.call_args
        self.assertIs(kwargs["verify"], False)

    @mock.patch.dict("os.environ", {"S3_BUCKET": "bucket", "S3_CA_BUNDLE": "/etc/ssl/internal-ca.pem"})
    @mock.patch("exports.services.storage_provider.boto3")
    def test_verify_uses_ca_bundle(self, mock_boto3):
        get_storage_provider("s3a://bucket/key.zip")
        _, kwargs = mock_boto3.client.call_args
        self.assertEqual(kwargs["verify"], "/etc/ssl/internal-ca.pem")

    @mock.patch.dict("os.environ", {"S3_BUCKET": "bucket", "S3_CA_BUNDLE": "", "S3_VERIFY_SSL": "true"})
    @mock.patch("exports.services.storage_provider.boto3")
    def test_verify_defaults_to_system_trust_store(self, mock_boto3):
        get_storage_provider("s3a://bucket/key.zip")
        _, kwargs = mock_boto3.client.call_args
        self.assertIsNone(kwargs["verify"])

    @mock.patch.dict("os.environ", {"STORAGE_PROVIDERS": "http://namenode"})
    @mock.patch("exports.services.storage_provider.HDFSStorageProvider")
    def test_returns_hdfs_provider_for_non_s3_path(self, mock_hdfs):
        get_storage_provider("hdfs://namenode/user/exports/file.zip")
        mock_hdfs.assert_called_once_with(servers_urls=["http://namenode"])
