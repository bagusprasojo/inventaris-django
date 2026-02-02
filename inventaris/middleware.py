from __future__ import annotations

import threading

_thread_local = threading.local()


def set_current_user(user):
    _thread_local.user = user


def get_current_user():
    return getattr(_thread_local, "user", None)


class CurrentUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_current_user(getattr(request, "user", None))
        response = self.get_response(request)
        set_current_user(None)
        return response
