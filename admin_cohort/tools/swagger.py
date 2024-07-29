import os

from drf_spectacular.extensions import OpenApiAuthenticationExtension

env = os.environ


class SwaggerOIDCAuthScheme(OpenApiAuthenticationExtension):
    target_class = 'admin_cohort.auth.auth_class.Authentication'
    name = 'OIDC Auth'
    match_subclasses = True
    priority = 10

    def get_security_definition(self, auto_schema):
        return {"type": "oauth2",
                "flows": {
                    "authorizationCode": {
                        "authorizationUrl": "http://localhost:9090/auth/realms/AP-HP/protocol/openid-connect/auth",
                        "tokenUrl": "http://localhost:9090/auth/realms/AP-HP/protocol/openid-connect/token",
                        "scopes": {}
                     }
                   }
                }
