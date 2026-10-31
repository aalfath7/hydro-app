from datetime import timedelta
from decimal import Decimal
from io import BytesIO

import pytest
from django.utils import timezone
from openpyxl import Workbook, load_workbook

from .conftest import stok_masuk
from .test_pembelian import _alokasi, jual


def test_laporan_penjualan_neto_retur_dan_batal(
    klien_admin, klien_pemilik, pemilik, pelanggan, produk, botol
):
    stok_masuk(pemilik, produk, 20, "A")
    a = jual(klien_admin, pelanggan, [{"satuan": botol.id, "jumlah": 4}])
    b = jual(klien_admin, pelanggan, [{"satuan": botol.id, "jumlah": 2}])
    klien_admin.post(
        "/api/retur/",
        {
            "transaksi": a.data["id"],
            "alasan": "x",
            "items": [{"alokasi": _alokasi(a), "jumlah_botol": 1, "kondisi": "layak"}],
        },
        format="json",
    )
    klien_admin.post(f"/api/transaksi/{b.data['id']}/ajukan-batal/", {"alasan": "x"}, format="json")
    klien_pemilik.post(f"/api/transaksi/{b.data['id']}/setujui-batal/", {}, format="json")

    r = klien_pemilik.get("/api/laporan/penjualan/")

    assert len(r.data) == 1
    baris = r.data[0]
    assert baris["periode"] == timezone.localdate().isoformat()
    assert baris["jumlah_transaksi"] == 1
    assert baris["bruto"] == "14000.00"
    assert baris["retur"] == "3500.00"
    assert baris["neto"] == "10500.00"

    terlaris = klien_pemilik.get("/api/laporan/produk-terlaris/")
    assert terlaris.data[0]["botol_terjual"] == 3
    assert terlaris.data[0]["nilai"] == "10500.00"


def test_laporan_per_bulan(klien_admin, klien_pemilik, pemilik, pelanggan, produk, botol):
    stok_masuk(pemilik, produk, 20, "A")
    jual(klien_admin, pelanggan, [{"satuan": botol.id, "jumlah": 1}])
    r = klien_pemilik.get("/api/laporan/penjualan/", {"per": "bulan"})
    assert r.data[0]["periode"] == timezone.localdate().replace(day=1).isoformat()


def test_periode_terbalik_ditolak(klien_pemilik):
    r = klien_pemilik.get("/api/laporan/penjualan/", {"dari": "2026-02-01", "sampai": "2026-01-01"})
    assert r.status_code == 400


def test_laporan_piutang_dan_terlambat(
    klien_admin, klien_pemilik, pemilik, pelanggan, produk, botol
):
    stok_masuk(pemilik, produk, 20, "A")
    r = jual(
        klien_admin,
        pelanggan,
        [{"satuan": botol.id, "jumlah": 2}],
        tempo=True,
        jatuh_tempo=timezone.localdate().isoformat(),
    )
    from pembelian.models import Transaksi

    Transaksi.objects.filter(pk=r.data["id"]).update(
        jatuh_tempo=timezone.localdate() - timedelta(days=3)
    )

    baris = klien_pemilik.get("/api/laporan/piutang/").data[0]

    assert baris["sisa"] == "7000.00"
    assert baris["terlambat_hari"] == 3


def test_ekspor_excel_tidak_menjalankan_rumus(klien_admin, klien_pemilik, pemilik, produk, botol):
    from pembelian.models import Pelanggan

    jahat = Pelanggan.objects.create(nama='=HYPERLINK("http://x","y")')
    stok_masuk(pemilik, produk, 5, "A")
    jual(
        klien_admin,
        jahat,
        [{"satuan": botol.id, "jumlah": 1}],
        tempo=True,
        jatuh_tempo=timezone.localdate().isoformat(),
    )

    r = klien_pemilik.get("/api/laporan/piutang/", {"ekspor": "xlsx"})

    assert r.status_code == 200
    lembar = load_workbook(BytesIO(r.content)).active
    sel = lembar.cell(row=2, column=2)
    assert sel.data_type == "s"
    assert sel.value.startswith("=HYPERLINK")


def test_dasbor_mengikuti_izin(
    klien_admin, klien_gudang, klien_pemilik, pemilik, pelanggan, produk, botol
):
    stok_masuk(pemilik, produk, 5, "A", hari=10)
    jual(klien_admin, pelanggan, [{"satuan": botol.id, "jumlah": 1}])

    g = klien_gudang.get("/api/dasbor/").data
    assert g["penjualan_hari_ini"] is None
    assert g["jumlah_transaksi_hari_ini"] is None
    assert g["tren"] is None
    assert g["stok_menipis"][0]["stok_teks"] == "4 botol"
    assert g["hampir_kedaluwarsa"][0]["nomor_batch"] == "A"

    a = klien_admin.get("/api/dasbor/").data
    assert a["jumlah_transaksi_hari_ini"] == 1
    assert a["penjualan_hari_ini"] is None

    p = klien_pemilik.get("/api/dasbor/").data
    assert Decimal(p["penjualan_hari_ini"]) == Decimal("3500")
    assert len(p["tren"]) == 14


def test_nota_dan_laporan_pdf(klien_admin, klien_pemilik, pemilik, pelanggan, produk, botol):
    try:
        import weasyprint  # noqa: F401
    except OSError:
        pytest.skip("Pustaka Pango tidak tersedia di mesin ini")
    stok_masuk(pemilik, produk, 5, "A")
    r = jual(klien_admin, pelanggan, [{"satuan": botol.id, "jumlah": 1}])

    nota = klien_admin.get(f"/api/transaksi/{r.data['id']}/nota/")
    assert nota.headers["Content-Type"] == "application/pdf"
    assert nota.content.startswith(b"%PDF")

    laporan = klien_pemilik.get("/api/laporan/penjualan/", {"ekspor": "pdf"})
    assert laporan.content.startswith(b"%PDF")


def _berkas_impor(baris):
    buku = Workbook()
    lembar = buku.active
    lembar.append(
        [
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
    )
    for b in baris:
        lembar.append(b)
    keluaran = BytesIO()
    buku.save(keluaran)
    keluaran.seek(0)
    keluaran.name = "produk.xlsx"
    return keluaran


def test_impor_produk(klien_pemilik):
    r = klien_pemilik.post(
        "/api/produk/impor/",
        {"berkas": _berkas_impor([["S1", "Air", "Botol", 600, "Botol", 10, 3500, 24, 78000]])},
        format="multipart",
    )
    assert r.status_code == 200, r.data
    assert r.data == {"dibuat": 1, "dilewati": 0}
    ulang = klien_pemilik.post(
        "/api/produk/impor/",
        {"berkas": _berkas_impor([["S1", "Air", "Botol", 600, "Botol", 10, 3500, 24, 78000]])},
        format="multipart",
    )
    assert ulang.data == {"dibuat": 0, "dilewati": 1}
    p = klien_pemilik.get("/api/produk/", {"q": "S1"}).data["results"][0]
    assert [(s["nama"], s["harga"]) for s in p["satuan"]] == [
        ("botol", "3500.00"),
        ("dus", "78000.00"),
    ]


def test_impor_galat_tidak_menyimpan_sebagian(klien_pemilik):
    r = klien_pemilik.post(
        "/api/produk/impor/",
        {
            "berkas": _berkas_impor(
                [
                    ["S1", "Air", "Botol", 600, "Botol", 10, 3500, None, None],
                    ["S2", "Air", "Botol", 600, "Botol", 10, "abc", None, None],
                ]
            )
        },
        format="multipart",
    )
    assert r.status_code == 400
    assert klien_pemilik.get("/api/produk/").data["count"] == 0


def test_foto_produk(klien_pemilik, produk, settings, tmp_path):
    from PIL import Image

    settings.MEDIA_ROOT = tmp_path
    keluaran = BytesIO()
    Image.new("RGB", (4, 4), "blue").save(keluaran, "PNG")
    keluaran.seek(0)
    keluaran.name = "foto.png"

    r = klien_pemilik.post(f"/api/produk/{produk.id}/foto/", {"foto": keluaran}, format="multipart")
    assert r.status_code == 204

    produk.refresh_from_db()
    assert produk.foto.name.endswith(".png")

    html = BytesIO()
    Image.new("RGB", (4, 4), "red").save(html, "PNG")
    html.seek(0)
    html.name = "serangan.html"
    r = klien_pemilik.post(f"/api/produk/{produk.id}/foto/", {"foto": html}, format="multipart")
    assert r.status_code == 400

    jpg = BytesIO()
    Image.new("RGB", (4, 4), "red").save(jpg, "JPEG")
    jpg.seek(0)
    jpg.name = "salah.png"
    r = klien_pemilik.post(f"/api/produk/{produk.id}/foto/", {"foto": jpg}, format="multipart")
    assert r.status_code == 204
    produk.refresh_from_db()
    assert produk.foto.name.endswith(".jpg")

    gif = BytesIO()
    Image.new("RGB", (4, 4), "red").save(gif, "GIF")
    gif.seek(0)
    gif.name = "x.gif"
    r = klien_pemilik.post(f"/api/produk/{produk.id}/foto/", {"foto": gif}, format="multipart")
    assert r.status_code == 400

    palsu = BytesIO(b"<svg onload=alert(1)>")
    palsu.name = "x.png"
    assert (
        klien_pemilik.post(
            f"/api/produk/{produk.id}/foto/", {"foto": palsu}, format="multipart"
        ).status_code
        == 400
    )

    # Diperiksa terakhir: di Windows file yang sedang dibaca tidak bisa ditimpa.
    assert klien_pemilik.get(f"/api/produk/{produk.id}/foto/").status_code == 200


@pytest.mark.parametrize("url", ["/api/laporan/stok/", "/api/laporan/piutang/"])
def test_ekspor_format_lain_tetap_json(klien_pemilik, url):
    assert klien_pemilik.get(url, {"ekspor": "csv"}).status_code == 200
