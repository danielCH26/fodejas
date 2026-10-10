"""Forms for accounts app."""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)

from .models import Role

User = get_user_model()


class FodejasLoginForm(AuthenticationForm):
    """Login form with email field."""

    username = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "correo@ejemplo.com",
                "autofocus": True,
            }
        ),
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ingrese su contraseña",
            }
        ),
    )


class FodejasRegistrationForm(UserCreationForm):
    """Registration form for aspirants."""

    email = forms.EmailField(
        label="Correo electrónico",
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "correo@ejemplo.com",
            }
        ),
    )
    documento = forms.CharField(
        label="Número de documento",
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Número de documento de identidad",
            }
        ),
    )
    telefono = forms.CharField(
        label="Teléfono",
        max_length=20,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Número de teléfono",
            }
        ),
    )
    first_name = forms.CharField(
        label="Nombres",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Nombres completos",
            }
        ),
    )
    last_name = forms.CharField(
        label="Apellidos",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Apellidos completos",
            }
        ),
    )
    fecha_nacimiento = forms.DateField(
        label="Fecha de nacimiento",
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
            raise forms.ValidationError("Ya existe una cuenta con este correo electrónico.")
        return email

    def clean_documento(self):
        """Validate documento is unique."""
        documento = self.cleaned_data.get("documento")
        if User.objects.filter(documento=documento).exists():
            raise forms.ValidationError("Ya existe una cuenta con este número de documento.")
        return documento


class FodejasPasswordResetForm(PasswordResetForm):
    """Password reset form."""

    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "correo@ejemplo.com",
            }
        ),
    )


class FodejasSetPasswordForm(SetPasswordForm):
    """Set new password form."""

    new_password1 = forms.CharField(
        label="Nueva contraseña",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Nueva contraseña",
            }
        ),
    )
    new_password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Confirmar contraseña",
            }
        ),
    )


class UserRoleForm(forms.Form):
    """Form for assigning roles to users."""

    role = forms.ModelChoiceField(
        label="Rol",
        queryset=Role.objects.all(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    convocation_scope = forms.IntegerField(
        label="Convocatoria (opcional)",
        required=False,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "ID de convocatoria"}
        ),
    )
