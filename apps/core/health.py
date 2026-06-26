import socket
from contextlib import contextmanager

from django.http import JsonResponse
from django.views import View


@contextmanager
def _timeout(seconds: int):
    old_timeout = socket.socket.getdefaulttimeout()
    socket.setdefaulttimeout(seconds)
    try:
        yield
    finally:
        socket.setdefaulttimeout(old_timeout)


class LivenessView(View):
    def get(self, request):
        return JsonResponse({"status": "ok"})


class ReadinessView(View):
    def get(self, request):
        checks = {}
        all_healthy = True

        with _timeout(5):
            if self._check_database():
                checks["database"] = "ok"
            else:
                checks["database"] = "failed"
                all_healthy = False

        if self._check_redis():
            checks["redis"] = "ok"
        else:
            checks["redis"] = "failed"
            all_healthy = False

        if all_healthy:
            return JsonResponse({"status": "ok", "checks": checks})
        return JsonResponse({"status": "unhealthy", "checks": checks}, status=503)

    def _check_database(self) -> bool:
        try:
            from django.db import connection

            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return True
        except Exception:
            return False

    def _check_redis(self) -> bool:
        try:
            import redis
            from django.conf import settings

            r = redis.from_url(settings.REDIS_URL)
            r.ping()
            return True
        except Exception:
            return False


liveness = LivenessView.as_view()
readiness = ReadinessView.as_view()
