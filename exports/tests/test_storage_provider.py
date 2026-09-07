from unittest import mock

from django.test import SimpleTestCase
from hdfs import HdfsError
from requests.exceptions import ConnectTimeout

from exports.exceptions import HdfsServerUnreachable, StorageProviderException
from exports.services.storage_provider import HDFSStorageProvider

SERVERS = ["http://namenode-01:50070", "http://namenode-02:50070"]


class TestHDFSStorageProvider(SimpleTestCase):
    @mock.patch("exports.services.storage_provider.KerberosClient")
    def test_client_is_built_with_all_servers_and_a_timeout(self, mock_client):
        provider = HDFSStorageProvider(servers_urls=SERVERS)
        url, kwargs = mock_client.call_args.args[0], mock_client.call_args.kwargs
        self.assertEqual(url, "http://namenode-01:50070;http://namenode-02:50070")
        self.assertIsNotNone(kwargs.get("timeout"))
        self.assertEqual(provider.client, mock_client.return_value)

    @mock.patch("exports.services.storage_provider.KerberosClient")
    def test_client_ignores_empty_server_urls(self, mock_client):
        HDFSStorageProvider(servers_urls=["", "http://namenode-01:50070"])
        self.assertEqual(mock_client.call_args.args[0], "http://namenode-01:50070")

    def test_no_configured_server_is_reported(self):
        with self.assertRaises(HdfsServerUnreachable):
            HDFSStorageProvider(servers_urls=[""])

    @mock.patch("exports.services.storage_provider.KerberosClient")
    def test_unreachable_servers_are_reported(self, mock_client):
        # ref #3493: a connection timeout used to escape as is, leaving the caller with an opaque 500
        mock_client.return_value.status.side_effect = ConnectTimeout("connection timed out")
        with self.assertRaises(HdfsServerUnreachable):
            HDFSStorageProvider(servers_urls=SERVERS)

    @mock.patch("exports.services.storage_provider.KerberosClient")
    def test_hdfs_errors_are_reported(self, mock_client):
        mock_client.return_value.status.side_effect = HdfsError("namenode is in safe mode")
        with self.assertRaises(HdfsServerUnreachable):
            HDFSStorageProvider(servers_urls=SERVERS)

    @mock.patch("exports.services.storage_provider.KerberosClient")
    def test_request_errors_are_wrapped_on_read_operations(self, mock_client):
        provider = HDFSStorageProvider(servers_urls=SERVERS)
        mock_client.return_value.status.side_effect = ConnectTimeout("connection timed out")
        with self.assertRaises(StorageProviderException):
            provider.get_file_size(file_name="/exports/an_export.zip")

    @mock.patch("exports.services.storage_provider.KerberosClient")
    def test_file_size_is_read_from_the_client(self, mock_client):
        mock_client.return_value.status.return_value = {"length": 1113943064}
        provider = HDFSStorageProvider(servers_urls=SERVERS)
        self.assertEqual(provider.get_file_size(file_name="/exports/an_export.zip"), 1113943064)
