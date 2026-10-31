from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import IntegerField, Min, OuterRef, QuerySet, Subquery, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from inti.format import stok_teks
from stok.models import BatchProduk

from .models import HargaProduk, Kategori, Produk, SatuanProduk


def dengan_stok(qs: QuerySet[Produk]) -> QuerySet[Produk]:
    """Stok tersedia hanya menghitung batch yang masih layak jual."""
    hari_ini = timezone.localdate()
    per_produk = (
        BatchProduk.objects.filter(produk=OuterRef("pk"), sisa__gt=0).order_by().values("produk")
    )
    layak = per_produk.filter(kedaluwarsa__gte=hari_ini)
    return qs.annotate(
        stok_tersedia=Coalesce(
            Subquery(layak.annotate(t=Sum("sisa")).values("t"), output_field=IntegerField()), 0
        ),
        stok_kedaluwarsa=Coalesce(
            Subquery(
                per_produk.filter(kedaluwarsa__lt=hari_ini).annotate(t=Sum("sisa")).values("t"),
                output_field=IntegerField(),
            ),
            0,
        ),
        kedaluwarsa_terdekat=Subquery(layak.annotate(t=Min("kedaluwarsa")).values("t")),
    )


def status_stok(tersedia: int, minimum: int) -> str:
    if tersedia <= 0:
        return "habis"
    return "menipis" if tersedia <= minimum else "aman"


def satuan_terbesar(satuan: list[SatuanProduk]) -> tuple[int, str]:
    if not satuan:
        return 1, "botol"
    besar = max(satuan, key=lambda s: s.isi_botol)
    return besar.isi_botol, besar.nama


def teks_stok_produk(botol: int, satuan: list[SatuanProduk]) -> str:
    isi, nama = satuan_terbesar(satuan)
    return stok_teks(botol, isi, nama)


def catat_harga(satuan: SatuanProduk, harga: Decimal, berlaku_mulai: date, pengguna) -> HargaProduk:
    return HargaProduk.objects.create(
        satuan=satuan, harga=harga, berlaku_mulai=berlaku_mulai, dibuat_oleh=pengguna
    )


@transaction.atomic
def buat_produk(
    pengguna,
    *,
    sku: str,
    nama: str,
    kategori: Kategori,
    harga_botol: Decimal,
    ukuran_ml: int | None = None,
    kemasan: str = "",
    stok_minimum: int = 0,
    isi_dus: int | None = None,
    harga_dus: Decimal | None = None,
) -> Produk:
    produk = Produk.objects.create(
        sku=sku,
        nama=nama,
        kategori=kategori,
        ukuran_ml=ukuran_ml,
        kemasan=kemasan,
        stok_minimum=stok_minimum,
    )
    hari_ini = timezone.localdate()
    botol = SatuanProduk.objects.create(produk=produk, nama="botol", isi_botol=1)
    catat_harga(botol, harga_botol, hari_ini, pengguna)
    if isi_dus and harga_dus is not None:
        dus = SatuanProduk.objects.create(produk=produk, nama="dus", isi_botol=isi_dus)
        catat_harga(dus, harga_dus, hari_ini, pengguna)
    return produk
