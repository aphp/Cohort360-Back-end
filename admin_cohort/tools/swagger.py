import inspect
import os

from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.utils import extend_schema_view, extend_schema

from admin_cohort.auth.auth_class import Authentication

env = os.environ


class JWTAuthScheme(OpenApiAuthenticationExtension):
    target_class = Authentication
    name = 'Token based authentication'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
            'description': "Use the **access_token** obtained after login.\n\n"
                           "Login at `/auth/login/`\n\n\n"
        }


class SchemaMeta(type):
    def __new__(cls, name, bases, dct):
        new_cls = super().__new__(cls, name, bases, dct)
        tags = getattr(new_cls, "swagger_tags", "")

        funcs = inspect.getmembers(new_cls, predicate=inspect.isfunction)
        action_funcs = map(lambda f: f[1],
                           filter(lambda f: "mapping" in f[1].__dict__, funcs))
        decorated_action_funcs = {f.__name__: extend_schema(tags=tags) for f in action_funcs}

        schema_decorator = extend_schema_view(
            list=extend_schema(tags=tags),
            retrieve=extend_schema(tags=tags),
            create=extend_schema(tags=tags),
            update=extend_schema(tags=tags),
            partial_update=extend_schema(tags=tags),
            destroy=extend_schema(tags=tags),
            **decorated_action_funcs)

        return schema_decorator(new_cls)
