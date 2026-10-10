"""URLs for accounts API."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenObtainPairView,
    TokenRefreshView,
)

from apps.accounts.api.views import (
    ConsentimientoViewSet,
    MeView,
    NotificationViewSet,
    SolicitudHabeasDataViewSet,
)

router = DefaultRouter()
router.register(r"consentimientos", ConsentimientoViewSet, basename="consentimiento")
router.register(r"habeas-data/solicitudes", SolicitudHabeasDataViewSet, basename="solicitud-habeas-data")
router.register(r"notifications", NotificationViewSet, basename="notification")

urlpatterns = [
    # JWT authentication endpoints (API).
    # Mounted at /api/auth/ so that tests using /api/auth/token/ work.
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/blacklist/", TokenBlacklistView.as_view(), name="token_blacklist"),
    # GET /api/auth/me/ — authenticated user with roles.
    # Reuses the logic from accounts_views.CurrentUserAPIView.
    path("me/", MeView.as_view(), name="me"),
    path("", include(router.urls)),
]
