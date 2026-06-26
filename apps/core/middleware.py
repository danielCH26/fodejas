import re
import uuid

from django.http import HttpRequest, HttpResponse

from apps.core.logging_config import set_request_id, set_user_id

SENSITIVE_PATTERNS = [
    re.compile(r"/password", re.IGNORECASE),
    re.compile(r"/token", re.IGNORECASE),
    re.compile(r"/secret", re.IGNORECASE),
    re.compile(r"/credential", re.IGNORECASE),
]


class RequestIDMiddleware:
    HEADER_NAME = "X-Request-ID"

    def __init__(self, get_response):
        self.get_response = get_response

    def _redact_path(self, path: str) -> str:
        for pattern in SENSITIVE_PATTERNS:
            if pattern.search(path):
                return "[REDACTED]"
        return path

    def _redact_query(self, query_string: str) -> str:
        if not query_string:
            return ""
        return "[REDACTED]"

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = request.headers.get(self.HEADER_NAME)
        if not request_id:
            request_id = str(uuid.uuid4())
        set_request_id(request_id)
        request.request_id = request_id

        if hasattr(request, "user") and request.user.is_authenticated:
            set_user_id(str(request.user.id))
        else:
            set_user_id("")

        redacted_path = self._redact_path(request.path)
        redacted_query = self._redact_query(request.META.get("QUERY_STRING", ""))
        request._redacted_path = redacted_path
        request._redacted_query = redacted_query

        response = self.get_response(request)
        response[self.HEADER_NAME] = request_id
        return response
