from django.utils.deprecation import MiddlewareMixin
from threading import local

_thread = local()


class CurrentUserMiddleware(MiddlewareMixin):
    """Middleware class to persist current user on local thread."""
    def process_request(self, request):
        set_current_user(request.user)


def get_current_user():
    """Function to access from the model layer to the current user."""
    if hasattr(_thread, 'user'):
        return _thread.user
    else:
        return None


def set_current_user(user):
    """Function to set the current user. Usefull to test and not logged things"""
    _thread.user = user
