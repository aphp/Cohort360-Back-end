class BadRequestError(Exception):
    pass


class FilesNoLongerAvailable(Exception):
    pass


class StorageProviderException(Exception):
    pass


class HdfsServerUnreachable(Exception):
    pass
