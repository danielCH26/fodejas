"""Admin forms for user and role management."""

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.accounts.models import Role

User = get_user_model()


class UserAdminForm(forms.ModelForm):
    """Form for creating new users in admin interface."""

    confirm_email = forms.EmailField(
        label="Confirmar correo electrónico",
        help_text="Ingrese nuevamente el correo electrónico para confirmar.",
    )

    class Meta:
        model = User
        fields = [
            "email",
            "confirm_email",
            "documento",
            "first_name",
            "last_name",
            "telefono",
            "fecha_nacimiento",
        ]
        widgets = {
            "fecha_nacimiento": forms.DateInput(attrs={"type": "date"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        confirm_email = cleaned_data.get("confirm_email")
        documento = cleaned_data.get("documento")

        # Validate email confirmation
        if email and confirm_email and email != confirm_email:
            self.add_error("confirm_email", "Los correos electrónicos no coinciden.")

        # Check if email already exists
        if email and User.objects.filter(email=email).exists():
            self.add_error("email", "Este correo electrónico ya está registrado.")

        # Check if documento already exists
        if documento and User.objects.filter(documento=documento).exists():
            self.add_error("documento", "Este documento ya está registrado.")

        return cleaned_data

    def clean_documento(self):
        documento = self.cleaned_data.get("documento")
        if documento and len(documento) < 6:
            raise ValidationError("El documento debe tener al menos 6 caracteres.")
        return documento


class UserUpdateAdminForm(forms.ModelForm):
    """Form for updating existing users in admin interface."""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "telefono", "fecha_nacimiento", "is_active"]
        widgets = {
            "fecha_nacimiento": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Don't allow changing email or documento in update form
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True


class RoleAdminForm(forms.ModelForm):
    """Form for creating/updating roles in admin interface."""

    class Meta:
        model = Role
        fields = ["code", "name", "type", "description"]

    def clean_code(self):
        code = self.cleaned_data.get("code")

        # Validate code format
        if not code.startswith("R-"):
            raise ValidationError('El código debe comenzar con "R-" (ej: R-ADMIN).')

        # Check if code already exists (excluding current instance)
        existing = Role.objects.filter(code=code)
        if self.instance and self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)

        if existing.exists():
            raise ValidationError("Este código de rol ya existe.")

        return code

    def clean(self):
        cleaned_data = super().clean()

        # Validate that internal roles don't conflict with external ones
        code = cleaned_data.get("code")
        role_type = cleaned_data.get("type")

        if code and role_type:
            known_external_roles = ["R-ASPIRANTE", "R-BENEFICIARIO"]
            known_internal_roles = [
                "R-ADMIN",
                "R-COORD",
                "R-CT",
                "R-REVISOR",
                "R-COMITE",
                "R-TESOR",
            ]

            if role_type == "interno" and code in known_external_roles:
                self.add_error(
                    "type", f"El rol {code} está definido como rol externo en el proyecto."
                )
            elif role_type == "externo" and code in known_internal_roles:
                self.add_error(
                    "type", f"El rol {code} está definido como rol interno en el proyecto."
                )

        return cleaned_data


class UserRoleAssignForm(forms.Form):
    """Form for assigning roles to users."""

    role = forms.ModelChoiceField(
        queryset=Role.objects.all(),
        label="Rol",
        help_text="Seleccione el rol a asignar.",
    )

    convocation_scope_id = forms.CharField(
        max_length=20,
        required=False,
        label="ID de convocatoria (opcional)",
        help_text="ID de convocatoria específica para alcance limitado. "
        "Dejar vacío para alcance global.",
    )

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data.get("role")
        convocation_scope_id = cleaned_data.get("convocation_scope_id")

        # Validate convocation_scope_id format if provided
        if convocation_scope_id and not convocation_scope_id.strip():
            cleaned_data["convocation_scope_id"] = None

        return cleaned_data
