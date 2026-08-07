"""URL configuration for scoring HTML views."""
from django.urls import path

from apps.scoring.views import (
    ScoringListView,
    ScoringDetailView,
    ScoringEvaluateView,
    ScoringCalculateView,
    RankingView,
    RankingGenerateView,
    ScoringExportView,
)

app_name = "scoring"

urlpatterns = [
    # Scoring views
    path("", ScoringListView.as_view(), name="list"),
    path("<uuid:solicitud_pk>/", ScoringDetailView.as_view(), name="detail"),
    path("<uuid:solicitud_pk>/evaluar/<int:evaluacion_pk>/", ScoringEvaluateView.as_view(), name="evaluate"),
    path("<uuid:solicitud_pk>/calcular/", ScoringCalculateView.as_view(), name="calculate"),
    
    # Ranking views
    path("ranking/", RankingView.as_view(), name="ranking"),
    path("ranking/generar/", RankingGenerateView.as_view(), name="ranking_generate"),
    path("ranking/exportar/", ScoringExportView.as_view(), name="export"),
]
