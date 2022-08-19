from drf_yasg.inspectors import SwaggerAutoSchema


# Moved CustomAutoSchema class to a dedicated tools_drf.py file instead of tools.py to prevent circular dependency.

# seen on https://stackoverflow.com/a/64440802
class CustomAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        tags = self.overrides.get('tags', None) \
               or getattr(self.view, 'swagger_tags', [])
        if not tags:
            tags = [operation_keys[0]]

        return tags
