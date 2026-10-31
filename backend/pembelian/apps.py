from django.apps import AppConfig


class PembelianConfig(AppConfig):
    name = "pembelian"

    def ready(self) -> None:
        from auditlog.registry import auditlog

        from .models import Pelanggan, Pembayaran, Retur, Transaksi

        auditlog.register(Pelanggan)
        auditlog.register(Transaksi, exclude_fields=["sisa_tagihan", "kunci_idempoten"])
        auditlog.register(Pembayaran)
        auditlog.register(Retur)
