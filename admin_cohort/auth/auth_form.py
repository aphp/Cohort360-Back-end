from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from admin_cohort.models import User
from admin_cohort.types import LoginError, ServerError


class CustomAuthenticationForm(AuthenticationForm):
    error_messages = {"user_not_found": "This user has no account DB",
                      "invalid_credentials": "Invalid username and/or password",
                      "auth_server_error": "An error occurred in the auth server"
                      }

    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if username is not None and password:
            try:
                self.user_cache = authenticate(self.request, username=username, password=password)
            except User.DoesNotExist:
                raise ValidationError(self.error_messages["user_not_found"])
            except LoginError:
                raise ValidationError(self.error_messages["invalid_credentials"])
            except ServerError:
                raise ValidationError(self.error_messages["auth_server_error"])
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data
