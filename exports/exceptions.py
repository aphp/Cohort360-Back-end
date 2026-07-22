class BadRequestError(Exception):
    pass


class FilesNoLongerAvailable(Exception):
    pass


class StorageProviderException(Exception):
    pass


class InvalidDownloadTicket(Exception):
    pass


class DownloadTicketUnavailable(Exception):
    pass


class InvalidRangeError(Exception):
    pass


class HdfsServerUnreachable(Exception):
    pass
