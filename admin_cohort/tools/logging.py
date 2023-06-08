import json
import struct
from logging.handlers import SocketHandler


class CustomSocketHandler(SocketHandler):

    def makePickle(self, record):
        """
        Pickles the record in binary format with a length prefix, and
        returns it ready for transmission across the socket.
        """
        record.exc_info and self.format(record)
        # See issue #14436: If msg or args are objects, they may not be
        # available on the receiving end. So we convert the msg % args
        # to a string, save it as msg and zap the args.
        d = dict(record.__dict__)
        d['msg'] = record.getMessage()
        d['args'] = None
        d['exc_info'] = None
        # Issue #25685: delete 'message' if present: redundant with 'msg'
        d.pop('message', None)
        d.pop('request', None)  # as request is not serializable
        s = bytes(json.dumps(d), 'utf-8')
        # s = pickle.dumps(d, 1)
        slen = struct.pack(">L", len(s))
        return slen + s
