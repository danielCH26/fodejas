"""Forms for accounts app."""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)
from django.utils.translation import gettext_lazy as _

from .models import Role

User = get_user_model()


class FodejasLoginForm(AuthenticationForm):
    """Login form with email field."""

    username = forms.EmailField(
        label=_("Correo electrónico"),
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": _("correo@ejemplo.com"),
                "autofocus": True,
            }
        ),
    )
    password = forms.CharField(
        label=_("Contraseña"),
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Ingrese su contraseña"),
            }
        ),
    )


class FodejasRegistrationForm(UserCreationForm):
    """Registration form for aspirants."""

    email = forms.EmailField(
        label=_("Correo electrónico"),
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": _("correo@ejemplo.com"),
            }
        ),
    )
    documento = forms.CharField(
        label=_("Número de documento"),
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Número de documento de identidad"),
            }
        ),
    )
    telefono = forms.CharField(
        label=_("Teléfono"),
        max_length=20,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Número de teléfono"),
            }
        ),
    )
    first_name = forms.CharField(
        label=_("Nombres"),
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Nombres completos"),
            }
        ),
    )
    last_name = forms.CharField(
        label=_("Apellidos"),
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Apellidos completos"),
            }
        ),
    )
    fecha_nacimiento = forms.DateField(
        label=_("Fecha de nacimiento"),
        required=False,
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
            }
        ),
    )

    class Meta:
        model = User
        fields = (
            "email",
            "documento",
            "first_name",
            "last_name",
            "telefono",
            "fecha_nacimiento",
            "password1",
            "password2",
        )

    def clean_email(self):
        """Validate email is unique."""
        email = self.cleaned_data.get("email")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("Ya existe una cuenta con este correo electrónico."))
        return email

    def clean_documento(self):
        """Validate documento is unique."""
        documento = self.cleaned_data.get("documento")
        if User.objects.filter(documento=documento).exists():
            raise forms.ValidationError(_("Ya existe una cuenta con este número de documento."))
        return documento


class FodejasPasswordResetForm(PasswordResetForm):
    """Password reset form."""

    email = forms.EmailField(
        label=_("Correo electrónico"),
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": _("correo@ejemplo.com"),
            }
        ),
    )


class FodejasSetPasswordForm(SetPasswordForm):
    """Set new password form."""

    new_password1 = forms.CharField(
        label=_("Nueva contraseña"),
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Nueva contraseña"),
            }
        ),
    )
    new_password2 = forms.CharField(
        label=_("Confirmar contraseña"),
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Confirmar contraseña"),
            }
        ),
    )


class UserRoleForm(forms.Form):
    """Form for assigning roles to users."""

    role = forms.ModelChoiceField(
        label=_("Rol"),
        queryset=Role.objects.all(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    convocation_scope = forms.IntegerField(
        label=_("Convocatoria (opcional)"),
        required=False,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": _("ID de convocatoria")}
        ),
    )
