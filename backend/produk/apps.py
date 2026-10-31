from django.apps import AppConfig


class ProdukConfig(AppConfig):
    name = "produk"

    def ready(self) -> None:
        from auditlog.registry import auditlog

        from .models import HargaProduk, Kategori, Produk, SatuanProduk

        for model in (Kategori, Produk, SatuanProduk, HargaProduk):
            auditlog.register(model)
