from rest_framework.negotiation import DefaultContentNegotiation


# Rétroportage de DRF 3.18.2 (GHSA-33wh-fxxf-88vv), à retirer avec la montée de DRF.
class ContentNegotiation(DefaultContentNegotiation):
    max_accept_header_length = 8192
    max_accept_tokens = 64
    max_media_type_length = 256

    def select_parser(self, request, parsers):
        content_type = request.content_type
        if content_type and len(content_type) > self.max_media_type_length:
            return None
        return super().select_parser(request, parsers)

    def get_accept_list(self, request):
        header = request.headers.get("accept", "*/*")
        if len(header) > self.max_accept_header_length:
            cut = header.rfind(",", 0, self.max_accept_header_length)
            header = header[: cut + 1] if cut != -1 else ""
        tokens = []
        for token in header.split(","):
            token = token.strip()
            if not token or len(token) > self.max_media_type_length:
                continue
            tokens.append(token)
            if len(tokens) >= self.max_accept_tokens:
                break
        return tokens
