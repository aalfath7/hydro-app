from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.db.models import Count, F, Sum
from django.db.models.functions import TruncDay, TruncMonth
from django.utils import timezone

from pembelian.models import ItemTransaksi, Retur, ReturItem, StatusTransaksi, Transaksi
from produk.layanan import dengan_stok, status_stok, teks_stok_produk
from produk.models import Produk
from stok.models import BatchProduk

NOL = Decimal("0")


def _transaksi_sah():
    return Transaksi.objects.exclude(status=StatusTransaksi.DIBATALKAN)


def penjualan(dari: date, sampai: date, per: str = "hari") -> list[dict[str, Any]]:
    """Retur mengurangi penjualan pada tanggal returnya, bukan tanggal nota."""
    potong = TruncMonth if per == "bulan" else TruncDay
    jual = (
        _transaksi_sah()
        .filter(tanggal__date__range=(dari, sampai))
        .annotate(periode=potong("tanggal"))
        .values("periode")
        .annotate(jumlah=Count("id"), bruto=Sum("total"))
        .order_by("periode")
    )
    retur = (
        Retur.objects.exclude(transaksi__status=StatusTransaksi.DIBATALKAN)
        .filter(tanggal__date__range=(dari, sampai))
        .annotate(periode=potong("tanggal"))
        .values("periode")
        .annotate(nilai=Sum("total"))
        .order_by("periode")
    )
    baris: dict[date, dict[str, Any]] = {}
    for r in jual:
        kunci = timezone.localtime(r["periode"]).date()
        baris[kunci] = {
            "periode": kunci,
            "jumlah_transaksi": r["jumlah"],
            "bruto": r["bruto"],
            "retur": NOL,
            "neto": r["bruto"],
        }
    for r in retur:
        kunci = timezone.localtime(r["periode"]).date()
        data = baris.setdefault(
            kunci,
            {"periode": kunci, "jumlah_transaksi": 0, "bruto": NOL, "retur": NOL, "neto": NOL},
        )
        data["retur"] = r["nilai"]
        data["neto"] = data["bruto"] - r["nilai"]
    return [baris[k] for k in sorted(baris)]


def produk_terlaris(dari: date, sampai: date, batas: int | None = None) -> list[dict[str, Any]]:
    jual = (
        ItemTransaksi.objects.exclude(transaksi__status=StatusTransaksi.DIBATALKAN)
        .filter(transaksi__tanggal__date__range=(dari, sampai))
        .values("produk_id", "produk__sku", "produk__nama")
        .annotate(botol=Sum(F("jumlah") * F("isi_botol")), nilai=Sum("subtotal"))
    )
    retur = (
        ReturItem.objects.exclude(retur__transaksi__status=StatusTransaksi.DIBATALKAN)
        .filter(retur__tanggal__date__range=(dari, sampai))
        .values("alokasi__item__produk_id")
        .annotate(botol=Sum("jumlah_botol"), nilai=Sum("nilai"))
    )
    kurang: dict[int, Any] = defaultdict(lambda: {"botol": 0, "nilai": NOL})
    for r in retur:
        kurang[r["alokasi__item__produk_id"]] = r
    hasil = [
        {
            "produk": r["produk_id"],
            "sku": r["produk__sku"],
            "nama": r["produk__nama"],
            "botol_terjual": r["botol"] - kurang[r["produk_id"]]["botol"],
            "nilai": r["nilai"] - kurang[r["produk_id"]]["nilai"],
        }
        for r in jual
    ]
    hasil.sort(key=lambda r: r["botol_terjual"], reverse=True)
    return hasil[:batas] if batas else hasil


def stok() -> list[dict[str, Any]]:
    qs = dengan_stok(Produk.objects.filter(aktif=True).prefetch_related("satuan"))
    return [
        {
            "produk": p.id,
            "sku": p.sku,
            "nama": p.nama,
            "stok_botol": p.stok_tersedia,
            "stok_teks": teks_stok_produk(p.stok_tersedia, list(p.satuan.all())),
            "stok_minimum": p.stok_minimum,
            "stok_kedaluwarsa": p.stok_kedaluwarsa,
            "kedaluwarsa_terdekat": p.kedaluwarsa_terdekat,
            "status": status_stok(p.stok_tersedia, p.stok_minimum),
        }
        for p in qs
    ]


def piutang() -> list[dict[str, Any]]:
    hari_ini = timezone.localdate()
    qs = (
        _transaksi_sah()
        .filter(sisa_tagihan__gt=0)
        .select_related("pelanggan")
        .order_by("jatuh_tempo", "tanggal")
    )
    return [
        {
            "transaksi": t.id,
            "nomor": t.nomor,
            "pelanggan": t.pelanggan.nama,
            "tanggal": timezone.localtime(t.tanggal).date(),
            "jatuh_tempo": t.jatuh_tempo,
            "total": t.total,
            "retur": t.total_retur,
            "terbayar": t.terbayar,
            "sisa": t.sisa_tagihan,
            "terlambat_hari": max((hari_ini - t.jatuh_tempo).days, 0) if t.jatuh_tempo else 0,
        }
        for t in qs
    ]


def batch_hampir_kedaluwarsa(batas: int = 10) -> list[BatchProduk]:
    tenggat = timezone.localdate() + timedelta(days=settings.HARI_HAMPIR_KEDALUWARSA)
    return list(
        BatchProduk.objects.select_related("produk")
        .prefetch_related("produk__satuan")
        .filter(sisa__gt=0, kedaluwarsa__lte=tenggat)
        .order_by("kedaluwarsa", "id")[:batas]
    )


def tren_penjualan(hari: int = 14) -> list[dict[str, Any]]:
    akhir = timezone.localdate()
    awal = akhir - timedelta(days=hari - 1)
    ada = {b["periode"]: b["neto"] for b in penjualan(awal, akhir)}
    return [
        {"tanggal": awal + timedelta(days=i), "neto": ada.get(awal + timedelta(days=i), NOL)}
        for i in range(hari)
    ]
