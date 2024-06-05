import functools
from typing import List

from hdfs import HdfsError
from hdfs.ext.kerberos import KerberosClient

from exports.exceptions import HdfsServerUnreachable, StorageProviderException


class StorageProvider:
    name = None

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
        for server in self.servers_urls:
            client = KerberosClient(server)
            try:
                client.status('/')
            except HdfsError:
                continue
            return client
        raise HdfsServerUnreachable("No HDFS servers available")

    @staticmethod
    def catch_hdfs_error(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except HdfsError as e:
                raise StorageProviderException(e.message)
        return wrapper

    @catch_hdfs_error
    def get_file_size(self, file_name: str) -> int:
        return self.client.status(hdfs_path=file_name).get("length")

    @catch_hdfs_error
    def stream_file(self, file_name: str):
        return self.client.read(hdfs_path=file_name,
                                offset=0,
                                length=None,
                                encoding=None,
                                chunk_size=1000000,
                                delimiter=None,
                                progress=None)

    @catch_hdfs_error
    def delete_file(self, file_name: str):
        self.client.delete(hdfs_path=file_name)
