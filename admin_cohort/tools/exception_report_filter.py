from django.views.debug import SafeExceptionReporterFilter


SENSITIVE_PARAMS = ["password"]


class CustomExceptionReporterFilter(SafeExceptionReporterFilter):

    def get_safe_settings(self):
        """ hide settings within the error report """
        return {"hidden": f"Override {self.__class__.__name__} to show settings"}

    def get_safe_request_meta(self, request):
        """ hide request META within the error report """
        return {"hidden": f"Override {self.__class__.__name__} to show request META"}

    def get_post_parameters(self, request):
        immutable_post_params = super().get_post_parameters(request)
        post_params = immutable_post_params.copy()
        for param_name in SENSITIVE_PARAMS:
            if param_name in post_params:
                post_params[param_name] = self.cleansed_substitute
        return post_params

    def get_traceback_frame_variables(self, request, tb_frame):
        cleansed = dict(super().get_traceback_frame_variables(request, tb_frame))
        for element in cleansed:
            if element in SENSITIVE_PARAMS:
                cleansed[element] = self.cleansed_substitute
        return cleansed.items()
