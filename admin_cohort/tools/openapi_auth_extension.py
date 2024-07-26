import os

from drf_spectacular.extensions import OpenApiAuthenticationExtension

env = os.environ


class OIDCAuthScheme(OpenApiAuthenticationExtension):
    target_class = 'admin_cohort.auth.auth_class.Authentication'
    name = 'oidcAuth'
    match_subclasses = True
    priority = 10

    def get_security_definition(self, auto_schema):
        return {"type": "oauth2",
                "flows": {
                    # "implicit": {
                    #     "authorizationUrl": "http://localhost:9090/auth/realms/AP-HP/protocol/openid-connect/auth",
                    #     "scopes": {}
                    # },
                    "authorizationCode": {
                        # "x-clientId": env.get("OIDC_CLIENT_ID"),
                        # "x-clientSecret": env.get("OIDC_CLIENT_SECRET"),
                        "authorizationUrl": "http://localhost:9090/auth/realms/AP-HP/protocol/openid-connect/auth",
                        "tokenUrl": "http://localhost:9090/auth/realms/AP-HP/protocol/openid-connect/token",
                        "scopes": {}
                     }
                   }
                }
