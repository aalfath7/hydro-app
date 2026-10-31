from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Any

from django.db import transaction
from openpyxl import Workbook, load_workbook

from .layanan import buat_produk
from .models import Kategori, Produk

KOLOM = [
    "sku",
    "nama",
    "kategori",
    "ukuran_ml",
    "kemasan",
    "stok_minimum",
    "harga_botol",
    "isi_dus",
    "harga_dus",
]
MAKS_BARIS = 5000


def buat_template() -> bytes:
    buku = Workbook()
    lembar = buku.active
    lembar.title = "Produk"
    lembar.append(KOLOM)
    lembar.append(["AMK-600", "Air Mineral 600 ml", "Botol", 600, "Botol", 240, 3500, 24, 72000])
    keluaran = BytesIO()
    buku.save(keluaran)
    return keluaran.getvalue()


def _desimal(nilai: Any) -> Decimal | None:
    if nilai in (None, ""):
        return None
    return Decimal(str(nilai))


def _bulat(nilai: Any) -> int | None:
    angka = _desimal(nilai)
    if angka is None:
        return None
    if angka != angka.to_integral_value() or angka < 0:
        raise InvalidOperation
    return int(angka)


def baca_baris(berkas) -> tuple[list[dict[str, Any]], list[str]]:
    lembar = load_workbook(berkas, read_only=True, data_only=True).worksheets[0]
    baris_iter = lembar.iter_rows(values_only=True)
    kepala = [str(k).strip().lower() if k else "" for k in next(baris_iter, ())]
    if kepala[: len(KOLOM)] != KOLOM:
        return [], ["Kolom tidak sesuai template: " + ", ".join(KOLOM)]

    hasil: list[dict[str, Any]] = []
    galat: list[str] = []
    sku_terlihat: set[str] = set()
    for nomor, nilai in enumerate(baris_iter, start=2):
        if nomor > MAKS_BARIS + 1:
            galat.append(f"Berkas melebihi {MAKS_BARIS} baris.")
            break
        data = dict(zip(KOLOM, nilai, strict=False))
        if not any(v not in (None, "") for v in data.values()):
            continue
        sku = str(data["sku"] or "").strip()
        nama = str(data["nama"] or "").strip()
        kategori = str(data["kategori"] or "").strip()
        try:
            harga_botol = _desimal(data["harga_botol"])
            harga_dus = _desimal(data["harga_dus"])
            isi_dus = _bulat(data["isi_dus"])
            ukuran = _bulat(data["ukuran_ml"])
            minimum = _bulat(data["stok_minimum"]) or 0
        except (InvalidOperation, ValueError):
            galat.append(f"Baris {nomor}: angka tidak valid.")
            continue
        if not sku or not nama or not kategori or harga_botol is None:
            galat.append(f"Baris {nomor}: sku, nama, kategori, dan harga_botol wajib diisi.")
        elif sku in sku_terlihat:
            galat.append(f"Baris {nomor}: SKU {sku} ganda di berkas.")
        elif harga_botol < 0 or (harga_dus is not None and harga_dus < 0):
            galat.append(f"Baris {nomor}: harga tidak boleh negatif.")
        elif bool(isi_dus) != (harga_dus is not None):
            galat.append(f"Baris {nomor}: isi_dus dan harga_dus harus diisi bersamaan.")
        else:
            sku_terlihat.add(sku)
            hasil.append(
                {
                    "sku": sku,
                    "nama": nama,
                    "kategori": kategori,
                    "ukuran_ml": ukuran,
                    "kemasan": str(data["kemasan"] or "").strip(),
                    "stok_minimum": minimum,
                    "harga_botol": harga_botol,
                    "isi_dus": isi_dus,
                    "harga_dus": harga_dus,
                }
            )
    return hasil, galat


@transaction.atomic
def simpan_baris(pengguna, baris: list[dict[str, Any]]) -> dict[str, int]:
    """SKU yang sudah ada dilewati, jadi berkas yang sama aman diimpor ulang."""
    sudah_ada = set(
        Produk.objects.filter(sku__in=[b["sku"] for b in baris]).values_list("sku", flat=True)
    )
    dibuat = 0
    for data in baris:
        if data["sku"] in sudah_ada:
            continue
        kategori, _ = Kategori.objects.get_or_create(nama=data["kategori"])
        buat_produk(pengguna, **{**data, "kategori": kategori})
        dibuat += 1
    return {"dibuat": dibuat, "dilewati": len(sudah_ada)}
