from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from admin_cohort.models import User
from admin_cohort.types import LoginError, ServerError


class AuthForm(AuthenticationForm):
    error_messages = {User.DoesNotExist: "Unregistered User",
                      LoginError: "Invalid Credentials",
                      ServerError: "JWT Server Error"
                      }

    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if username is not None and password:
            try:
                self.user_cache = authenticate(self.request, username=username, password=password)
            except (User.DoesNotExist, LoginError, ServerError) as e:
                raise ValidationError(message=f"{self.error_messages.get(e.__class__)} - {e}")
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data
