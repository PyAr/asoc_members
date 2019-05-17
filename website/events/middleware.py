from django.utils.deprecation import MiddlewareMixin
from threading import local

_thread = local()

class CurrentUserMiddleware(MiddlewareMixin):
    """Middleware class to persist current user on local thread."""
    def process_request(self, request):
        _thread.user = request.user

def get_current_user():
    """Function to access from the model layer to the current user."""
    return _thread.user