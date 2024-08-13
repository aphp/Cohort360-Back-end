from admin_cohort.urls import DOCS_ENDPOINT


class SwaggerHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        referer = request.headers.get("Referer")
        if referer is not None and referer.endswith(f"/{DOCS_ENDPOINT}"):
            request.META["HTTP_AUTHORIZATIONMETHOD"] = "OIDC"
        return self.get_response(request)
