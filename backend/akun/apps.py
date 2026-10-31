from django.apps import AppConfig


class AkunConfig(AppConfig):
    name = "akun"

    def ready(self) -> None:
        from auditlog.registry import auditlog

        from .models import Pengguna

        auditlog.register(Pengguna, exclude_fields=["password", "last_login"])
