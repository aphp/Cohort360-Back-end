import os

from hdfs import HdfsError
from hdfs.ext.kerberos import KerberosClient

from exports.types import HdfsServerUnreachable

env = os.environ

HDFS_SERVERS = env.get("HDFS_SERVERS").split(',')
HDFS_CLIENTS = {'current': HDFS_SERVERS[0],
                HDFS_SERVERS[0]: KerberosClient(HDFS_SERVERS[0])
                }


class HdfsClientService:

    def __init__(self, **kwargs):
        self.client = self.get_client()

    def get_client(self) -> KerberosClient:
        client = HDFS_CLIENTS.get(HDFS_CLIENTS['current'])
        try:
            client.status('/')
        except HdfsError:
            return self.try_other_hdfs_servers()
        else:
            return client

    @staticmethod
    def try_other_hdfs_servers():
        for server in [s for s in HDFS_SERVERS if s != HDFS_CLIENTS['current']]:
            client = KerberosClient(server)
            try:
                client.status('/')
            except HdfsError:
                continue
            else:
                HDFS_CLIENTS[server] = KerberosClient(server)
                HDFS_CLIENTS['current'] = server
                return client
        raise HdfsServerUnreachable("HDFS servers are unreachable or in stand-by")

    def stream_gen(self, file_name: str):
        with self.get_client().read(hdfs_path=file_name,
                                    offset=0,
                                    length=None,
                                    encoding=None,
                                    chunk_size=1000000,
                                    delimiter=None,
                                    progress=None) as f:
            for chunk in f:
                yield chunk

    def get_file_size(self, file_name: str) -> int:
        return self.get_client().status(hdfs_path=file_name).get("length")

    def delete_file(self, file_name: str):
        self.get_client().delete(hdfs_path=file_name)


hdfs_client_service = HdfsClientService()
