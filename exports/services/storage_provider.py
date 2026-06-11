import functools
import os
import re
from contextlib import contextmanager
from typing import List

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from hdfs import HdfsError
from hdfs.ext.kerberos import KerberosClient

from exports.exceptions import HdfsServerUnreachable, StorageProviderException

S3_PATH_PREFIXES = ("s3://", "s3a://")
# An S3 URI is s3a://<bucket>/<key>: the bucket is the first path segment.
S3_URI_PATTERN = re.compile(r"^s3a?://(?P<bucket>[^/]+)/(?P<key>.+)$")


class StorageProvider:
    name: str | None = None

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

    def __init__(self, servers_urls: List[str]):
        self.servers_urls = servers_urls
        self.client = self.get_client()

    def get_client(self):
        for server in self.servers_urls:
            client = KerberosClient(server)
            try:
                client.status("/")
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
        return self.client.read(hdfs_path=file_name, offset=0, length=None, encoding=None, chunk_size=1000000, delimiter=None, progress=None)

    @catch_hdfs_error
    def delete_file(self, file_name: str):
        self.client.delete(hdfs_path=file_name)


class S3StorageProvider(StorageProvider):
    name = "S3"
    chunk_size = 1000000

    def __init__(
        self,
        endpoint_url: str | None,
        access_key: str | None,
        secret_key: str | None,
        bucket: str | None,
        region_name: str | None = None,
        addressing_style: str = "path",
        verify: bool | str | None = None,
    ):
        self.endpoint_url = endpoint_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket
        self.region_name = region_name
        self.addressing_style = addressing_style
        self.verify = verify
        self.client = self.get_client()

    def get_client(self):
        return boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region_name,
            verify=self.verify,
            config=Config(s3={"addressing_style": self.addressing_style}),
        )

    def object_key(self, file_name: str) -> str:
        """
        Return the object key from a `s3a://<bucket>/<key>` path. The bucket must match
        the configured one, and traversal segments (`..`, `//`) are not allowed.
        """
        if not self.bucket:
            raise StorageProviderException("S3 bucket is not configured")
        match = S3_URI_PATTERN.match(file_name)
        if not match:
            raise StorageProviderException(f"Invalid S3 path: `{file_name}`")
        bucket, key = match.group("bucket"), match.group("key")
        if bucket != self.bucket:
            raise StorageProviderException(f"S3 bucket mismatch: path targets `{bucket}` but `{self.bucket}` is configured")
        if "//" in key or ".." in key.split("/"):
            raise StorageProviderException(f"Invalid S3 object key: `{key}`")
        return key

    @staticmethod
    def catch_s3_error(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except (BotoCoreError, ClientError) as e:
                raise StorageProviderException(str(e))

        return wrapper

    @catch_s3_error
    def get_file_size(self, file_name: str) -> int:
        return self.client.head_object(Bucket=self.bucket, Key=self.object_key(file_name))["ContentLength"]

    @contextmanager
    def stream_file(self, file_name: str):
        key = self.object_key(file_name)
        try:
            body = self.client.get_object(Bucket=self.bucket, Key=key)["Body"]
        except (BotoCoreError, ClientError) as e:
            raise StorageProviderException(str(e))
        try:
            yield body.iter_chunks(chunk_size=self.chunk_size)
        finally:
            body.close()

    @catch_s3_error
    def delete_file(self, file_name: str):
        self.client.delete_object(Bucket=self.bucket, Key=self.object_key(file_name))


def is_s3_path(file_name: str) -> bool:
    return file_name.startswith(S3_PATH_PREFIXES)


def storage_scheme(file_name: str) -> str:
    return "s3" if is_s3_path(file_name) else "hdfs"


def s3_verify() -> bool | str | None:
    """
    Resolve the boto3 `verify` argument for on-prem TLS: a CA bundle path
    (`S3_CA_BUNDLE`), `False` to disable verification (`S3_VERIFY_SSL=false`), or
    `None` to use the system trust store.
    """
    ca_bundle = os.environ.get("S3_CA_BUNDLE")
    if ca_bundle:
        return ca_bundle
    if os.environ.get("S3_VERIFY_SSL", "true").lower() in ("false", "0", "no"):
        return False
    return None


def get_storage_provider(file_name: str) -> StorageProvider:
    """
    Return the storage provider matching the file path scheme, mirroring the
    data-exporter convention: an `s3a://` (or `s3://`) prefix targets S3,
    anything else falls back to HDFS.
    """
    if is_s3_path(file_name):
        return S3StorageProvider(
            endpoint_url=os.environ.get("S3_ENDPOINT_URL"),
            access_key=os.environ.get("S3_ACCESS_KEY"),
            secret_key=os.environ.get("S3_SECRET_KEY"),
            bucket=os.environ.get("S3_BUCKET"),
            region_name=os.environ.get("S3_REGION_NAME"),
            addressing_style=os.environ.get("S3_ADDRESSING_STYLE", "path"),
            verify=s3_verify(),
        )
    return HDFSStorageProvider(servers_urls=os.environ.get("STORAGE_PROVIDERS", "").split(","))
