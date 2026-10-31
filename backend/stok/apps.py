from django.apps import AppConfig


class StokConfig(AppConfig):
    name = "stok"

    def ready(self) -> None:
        from auditlog.registry import auditlog

        from .models import BarangMasuk, StokOpname

        auditlog.register(BarangMasuk)
        auditlog.register(StokOpname)
