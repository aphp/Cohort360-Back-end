import json
import zlib

from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from admin_cohort.tools.negotiation import ContentNegotiation


class EchoView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"ok": True})

    def post(self, request):
        return Response(request.data)


class RequestParsingTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = EchoView.as_view()

    def post(self, body, content_type):
        return self.view(self.factory.post("/echo/", data=body, content_type=content_type))

    def test_json_body_is_parsed(self):
        response = self.post(json.dumps({"a": 1}), "application/json; charset=utf-8")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"a": 1})

    def test_json_with_bytes_codec_charset_is_rejected(self):
        body = zlib.compress(json.dumps({"a": "x" * 100_000}).encode())
        response = self.post(body, "application/json; charset=zlib_codec")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_form_with_bytes_codec_charset_is_rejected(self):
        response = self.post(zlib.compress(b"a=1"), "application/x-www-form-urlencoded; charset=zlib_codec")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_oversized_content_type_is_unsupported(self):
        response = self.post("{}", "application/json; x=" + "a" * 300)
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_accept_header_is_bounded(self):
        junk = ", ".join(f'text/x{i}; q="{";" * 300}"' for i in range(100))
        request = self.factory.get("/echo/", HTTP_ACCEPT=f"application/json, {junk}, " + "text/y, " * 2000)
        tokens = ContentNegotiation().get_accept_list(request)
        self.assertEqual(tokens[0], "application/json")
        self.assertLessEqual(len(tokens), ContentNegotiation.max_accept_tokens)
        self.assertTrue(all(len(token) <= ContentNegotiation.max_media_type_length for token in tokens))
        self.assertEqual(self.view(request).status_code, status.HTTP_200_OK)
