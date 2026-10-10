"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path

from apps.accounts.accounts_views import root_view
from apps.core.health import liveness, readiness

urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz", liveness, name="healthz"),
    path("readyz", readiness, name="readyz"),
    path("", include("django_prometheus.urls")),
    path("", root_view, name="root"),  # Redirect to login
    # HTML views for accounts (before API to avoid conflict)
    path("accounts/", include("apps.accounts.urls")),
    # APIs mantenidas (sin HTML equivalente)
    path("api/auth/", include("apps.accounts.api.urls")),  # JWT API endpoints
    path("api/audit/", include("apps.audit.urls")),  # Audit endpoints
    path("api/legalization/", include("apps.legalization.api.urls")),  # Legalization API (CHG-301)

    # HTML views
    path("convocatorias/", include("apps.convocatories.urls")),  # Convocatory HTML views
    path("applications/", include("apps.applications.urls")),  # Applications HTML views
    path("scoring/", include("apps.scoring.urls")),  # Scoring HTML views
    path("claims/", include("apps.claims.urls")),  # Claims HTML views (CHG-205)
    path("governance/", include("apps.governance.urls")),  # Governance HTML views (CHG-207)
    path("treasury/", include("apps.treasury.urls")),  # Treasury reconciliation (CHG-802)
    path("legalization/", include("apps.legalization.urls")),  # Legalization HTML views (CHG-301)
]
