from django.conf import settings
from rest_framework import parsers
from rest_framework.exceptions import ParseError


# Rétroportage de DRF 3.18.2 (GHSA-3547-9m27-7rxg), à retirer avec la montée de DRF.
class TextCharsetMixin:
    def parse(self, stream, media_type=None, parser_context=None):
        encoding = (parser_context or {}).get("encoding", settings.DEFAULT_CHARSET)
        try:
            "".encode(encoding)
        except (LookupError, UnicodeError):
            raise ParseError(f'Unsupported charset "{encoding}" in request Content-Type header.')
        return super().parse(stream, media_type, parser_context)


class JSONParser(TextCharsetMixin, parsers.JSONParser):
    pass


class FormParser(TextCharsetMixin, parsers.FormParser):
    pass


class MultiPartParser(TextCharsetMixin, parsers.MultiPartParser):
    pass
