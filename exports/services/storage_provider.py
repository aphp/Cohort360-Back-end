import functools
from typing import List

from hdfs import HdfsError
from hdfs.ext.kerberos import KerberosClient
from requests.exceptions import RequestException

from exports.exceptions import HdfsServerUnreachable, StorageProviderException

HDFS_CONNECT_TIMEOUT = 5
HDFS_READ_TIMEOUT = 60


class StorageProvider:
    name: str | None = None

    def __init__(self, servers_urls: List[str]):
        self.servers_urls = servers_urls
        self.client = self.get_client()

    def get_client(self):
        """
        return a client connection to the storage provider
        """
        raise NotImplementedError

    def get_file_size(self, file_name: str) -> int:
        """
        get the file size
        @param file_name:
        @return: file size
        """
        raise NotImplementedError

    def stream_file(self, file_name: str):
        """
        read and stream a file from the storage provider
        @param file_name: file to be streamed
        @return: chunk of the file
        """
        raise NotImplementedError

    def delete_file(self, file_name: str):
        """
        delete file from the storage provider
        @param file_name: file to be deleted
        @return: None
        """
        raise NotImplementedError


class HDFSStorageProvider(StorageProvider):
    name = "HDFS"

    def get_client(self):
        servers = [url for url in self.servers_urls if url]
        if not servers:
            raise HdfsServerUnreachable("No HDFS server is configured")
        # the client rotates over the servers on each request, an unreachable namenode no longer aborts the operation
        client = KerberosClient(";".join(servers), timeout=(HDFS_CONNECT_TIMEOUT, HDFS_READ_TIMEOUT))
        try:
            client.status("/")
        except (HdfsError, RequestException) as e:
            raise HdfsServerUnreachable(f"No HDFS servers available: {e}")
        return client

    @staticmethod
    def catch_hdfs_error(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except HdfsError as e:
                raise StorageProviderException(e.message)
            except RequestException as e:
                raise StorageProviderException(str(e))

        return wrapper

    @catch_hdfs_error
    def get_file_size(self, file_name: str) -> int:
        return self.client.status(hdfs_path=file_name).get("length")

    @catch_hdfs_error
    def stream_file(self, file_name: str):
        return self.client.read(hdfs_path=file_name, offset=0, length=None, encoding=None, chunk_size=1000000, delimiter=None, progress=None)

    @catch_hdfs_error
    def delete_file(self, file_name: str):
        self.client.delete(hdfs_path=file_name)
