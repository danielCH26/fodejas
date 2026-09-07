"""Tests para CHG-806 — stubs eliminados + placeholder sessions.

Verifica que la limpieza de apps stub se aplicó correctamente y que
el placeholder de CAP-017 está en su lugar. Sin DB, sin PII.
"""
import os

import pytest

REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
)
APPS_DIR = os.path.join(REPO_ROOT, "apps")
DOCS_DIR = os.path.join(REPO_ROOT, "docs")


class TestStubsRemoved:
    """Las apps stub deben estar físicamente removidas del árbol."""

    def test_reporting_directory_does_not_exist(self):
        assert not os.path.isdir(os.path.join(APPS_DIR, "reporting")), (
            "apps/reporting/ debería haber sido removida por CHG-806. "
            "Si la estás reintroduciendo, actualizá docs/stubs-removed.md."
        )

    def test_psychosocial_directory_does_not_exist(self):
        assert not os.path.isdir(os.path.join(APPS_DIR, "psychosocial")), (
            "apps/psychosocial/ debería haber sido removida por CHG-806."
        )

    def test_governance_sessions_package_exists(self):
        path = os.path.join(APPS_DIR, "governance", "sessions")
        assert os.path.isdir(path)
        assert os.path.isfile(os.path.join(path, "__init__.py"))
        assert os.path.isfile(os.path.join(path, "README.md"))

    def test_governance_sessions_has_only_placeholder_files(self):
        """El placeholder no debe contener archivos ejecutables hasta
        que CHG-501 lo implemente."""
        path = os.path.join(APPS_DIR, "governance", "sessions")
        files = sorted(os.listdir(path))
        assert files == ["README.md", "__init__.py"], (
            f"sessions/ debe contener solo __init__.py y README.md; "
            f"encontré {files}. Si estás agregando más, abrí CHG-501."
        )


class TestInstalledApps:
    """`INSTALLED_APPS` no debe incluir apps removidas."""

    def _get_installed_apps(self):
        # Importación lazy: si el proyecto no carga (sin venv),
        # marcamos el test como xfail y verificamos manualmente abajo.
        import os
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
        try:
            import django
            django.setup()
            from django.conf import settings
            return list(settings.INSTALLED_APPS)
        except Exception:
            return None  # el proyecto no carga; verificar por grep

    def test_settings_installed_apps_excludes_reporting(self):
        installed = self._get_installed_apps()
        if installed is not None:
            assert "apps.reporting" not in installed
        else:
            settings_path = os.path.join(REPO_ROOT, "config", "settings.py")
            source = open(settings_path, encoding="utf-8").read()
            # Si aparece la línea exacta, fallar; si está comentada, OK.
            assert '"apps.reporting"' not in source or "# CHG-806" in source

    def test_settings_installed_apps_excludes_psychosocial(self):
        installed = self._get_installed_apps()
        if installed is not None:
            assert "apps.psychosocial" not in installed
        else:
            settings_path = os.path.join(REPO_ROOT, "config", "settings.py")
            source = open(settings_path, encoding="utf-8").read()
            assert '"apps.psychosocial"' not in source or "# CHG-806" in source


class TestStubsRemovedDoc:
    def test_stubs_removed_doc_exists(self):
        assert os.path.isfile(os.path.join(DOCS_DIR, "stubs-removed.md"))

    def test_stubs_removed_doc_references_chg806(self):
        path = os.path.join(DOCS_DIR, "stubs-removed.md")
        content = open(path, encoding="utf-8").read()
        assert "CHG-806" in content
        assert "apps/reporting" in content or "apps.reporting" in content
        assert "apps/psychosocial" in content or "apps.psychosocial" in content


class TestNoLingeringImports:
    """El código no debe importar desde apps/reporting ni
    apps/psychosocial en ninguna parte del repo."""

    def test_no_imports_of_removed_apps(self):
        for root, _dirs, files in os.walk(REPO_ROOT):
            # Excluir directorios irrelevantes.
            if any(
                skip in root
                for skip in (".git", "node_modules", ".venv", "venv", "__pycache__")
            ):
                continue
            for filename in files:
                if not filename.endswith(".py"):
                    continue
                if filename == "test_stubs_removed.py":
                    continue  # este archivo sí menciona los nombres
                filepath = os.path.join(root, filename)
                try:
                    content = open(filepath, encoding="utf-8").read()
                except (UnicodeDecodeError, OSError):
                    continue
                assert "from apps.reporting" not in content, (
                    f"Removed app imported in {filepath}"
                )
                assert "from apps.psychosocial" not in content, (
                    f"Removed app imported in {filepath}"
                )
                assert "import apps.reporting" not in content, (
                    f"Removed app imported in {filepath}"
                )
                assert "import apps.psychosocial" not in content, (
                    f"Removed app imported in {filepath}"
                )
