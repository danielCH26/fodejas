"""Views for the legalization API (CHG-301, CAP-029)."""

from django.utils.translation import gettext as _

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.accounts.permissions import HasAnyRole, has_any_role
from apps.legalization.models import LegalDocument, LegalizationProcess
from apps.legalization.services import sign_legal_document
from apps.legalization.signer import verify_document

from .serializers import (
    LegalDocumentSerializer,
    LegalDocumentSignResultSerializer,
    LegalizationProcessSerializer,
)


class LegalizationProcessViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for LegalizationProcess — list/retrieve (read-only for MVP)."""

    queryset = LegalizationProcess.objects.select_related(
        "beneficiary", "convocatoria"
    ).prefetch_related("documents")
    serializer_class = LegalizationProcessSerializer

    def get_permissions(self):
        return [IsAuthenticated(), HasAnyRole(["R-JUNTA", "R-ADMIN", "R-ASPIRANTE"])]


class LegalDocumentViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for LegalDocument — list/retrieve/sign/verify."""

    queryset = LegalDocument.objects.select_related(
        "process", "process__beneficiary", "process__convocatoria"
    )
    serializer_class = LegalDocumentSerializer

    def get_permissions(self):
        return [IsAuthenticated(), HasAnyRole(["R-JUNTA", "R-ADMIN", "R-ASPIRANTE"])]

    def get_queryset(self):
        """Filter: Aspirantes only see their own documents."""
        qs = super().get_queryset()
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return qs
        # R-JUNTA / R-ADMIN see all; R-ASPIRANTE sees only their own.
        from apps.accounts.permissions import has_any_role

        if has_any_role(user, ["R-JUNTA", "R-ADMIN"]):
            return qs
        return qs.filter(process__beneficiary=user)

    @action(
        detail=True,
        methods=["post"],
        url_path="sign",
    )
    def sign(self, request: Request, pk=None) -> Response:
        """POST /api/legalization/documents/<pk>/sign/

        Signs the document using the configured signer (SIGNATURE_PROVIDER).
        Idempotent: re-signing an already-signed document is a no-op.

        Returns 200 with signature result, or 400/403/404 on error.
        """
        document: LegalDocument = self.get_object()

        # Aspirantes may only sign their own documents. R-JUNTA / R-ADMIN can sign any.
        user = request.user
        if (
            not user.is_staff
            and not user.is_superuser
            and not has_any_role(user, ["R-JUNTA", "R-ADMIN"])
            and document.process.beneficiary_id != user.id
        ):
            return Response(
                {"detail": _("No tienes permiso para firmar este documento.")},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Idempotent: if already signed, return current state.
        if document.status == LegalDocument.Status.FIRMADO and document.post_sign_hash:
            serializer = LegalDocumentSignResultSerializer(document, context={"request": request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        if not document.pdf:
            return Response(
                {"detail": _("El documento no tiene PDF cargado; cargue el archivo primero.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            sign_legal_document(document, actor=user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        # Refresh to get persisted timestamps
        document.refresh_from_db()
        serializer = LegalDocumentSignResultSerializer(document, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["get"],
        url_path="verify",
    )
    def verify(self, request: Request, pk=None) -> Response:
        """GET /api/legalization/documents/<pk>/verify/

        Verifies the document integrity against its stored pre_sign_hash.
        Returns 200 with verification result.
        """
        document: LegalDocument = self.get_object()

        if not document.pre_sign_hash:
            return Response(
                {"detail": _("El documento no ha sido firmado aún.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not document.pdf:
            return Response(
                {"detail": _("El documento no tiene PDF para verificar.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        document.pdf.seek(0)
        pdf_bytes = document.pdf.read()
        is_valid = verify_document(pdf_bytes, document.pre_sign_hash)

        return Response(
            {
                "id": str(document.id),
                "document_type": document.document_type,
                "pre_sign_hash": document.pre_sign_hash,
                "is_integral": is_valid,
                "provider": (document.changes or {}).get("provider", "unknown"),
            },
            status=status.HTTP_200_OK,
        )
