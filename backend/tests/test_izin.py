import pytest
from django.urls import URLPattern, URLResolver, get_resolver
from rest_framework.test import APIClient

from inti.izin import IZIN_PERAN, PEMILIK, SEMUA_IZIN, PunyaIzin

from .conftest import buat_pengguna, klien_untuk

A, G, P = "admin_penjualan", "staf_gudang", "pemilik"

# (metode, url, peran yang boleh). Id 1 tidak ada: lolos izin berarti 404, ditolak berarti 403.
MATRIKS = [
    ("get", "/api/produk/", {A, G, P}),
    ("get", "/api/produk/1/", {A, G, P}),
    ("get", "/api/produk/1/foto/", {A, G, P}),
    ("post", "/api/produk/", {P}),
    ("patch", "/api/produk/1/", {P}),
    ("post", "/api/produk/1/foto/", {P}),
    ("post", "/api/produk/impor/", {P}),
    ("get", "/api/produk/template-impor/", {P}),
    ("get", "/api/kategori/", {A, G, P}),
    ("post", "/api/kategori/", {P}),
    ("patch", "/api/kategori/1/", {P}),
    ("post", "/api/satuan/", {P}),
    ("patch", "/api/satuan/1/", {P}),
    ("get", "/api/harga/", {A, G, P}),
    ("post", "/api/harga/", {P}),
    ("get", "/api/batch/", {A, G, P}),
    ("get", "/api/batch/1/", {A, G, P}),
    ("post", "/api/batch/1/kurangi/", {G, P}),
    ("get", "/api/mutasi/", {A, G, P}),
    ("get", "/api/barang-masuk/", {G, P}),
    ("post", "/api/barang-masuk/", {G, P}),
    ("get", "/api/opname/", {G, P}),
    ("get", "/api/opname/1/", {G, P}),
    ("post", "/api/opname/", {G, P}),
    ("post", "/api/opname/1/setujui/", {P}),
    ("post", "/api/opname/1/tolak/", {P}),
    ("get", "/api/pelanggan/", {A, P}),
    ("get", "/api/pelanggan/1/", {A, P}),
    ("post", "/api/pelanggan/", {A, P}),
    ("patch", "/api/pelanggan/1/", {A, P}),
    ("get", "/api/transaksi/", {A, P}),
    ("get", "/api/transaksi/1/", {A, P}),
    ("post", "/api/transaksi/", {A, P}),
    ("post", "/api/transaksi/1/bayar/", {A, P}),
    ("get", "/api/transaksi/1/nota/", {A, P}),
    ("post", "/api/transaksi/1/ajukan-batal/", {A, P}),
    ("post", "/api/transaksi/1/setujui-batal/", {P}),
    ("post", "/api/transaksi/1/tolak-batal/", {P}),
    ("get", "/api/retur/", {A, P}),
    ("get", "/api/retur/1/", {A, P}),
    ("post", "/api/retur/", {A, P}),
    ("get", "/api/laporan/penjualan/", {P}),
    ("get", "/api/laporan/produk-terlaris/", {P}),
    ("get", "/api/laporan/stok/", {P}),
    ("get", "/api/laporan/piutang/", {P}),
    ("get", "/api/dasbor/", {A, G, P}),
    ("get", "/api/pengguna/", {P}),
    ("get", "/api/pengguna/999/", {P}),
    ("post", "/api/pengguna/", {P}),
    ("patch", "/api/pengguna/999/", {P}),
    ("post", "/api/pengguna/999/atur-password/", {P}),
    ("post", "/api/pengguna/999/reset-2fa/", {P}),
    ("get", "/api/peran/", {P}),
    ("get", "/api/log-aktivitas/", {P}),
]


@pytest.fixture
def klien_peran(db):
    return {p: klien_untuk(buat_pengguna(p, p)) for p in (A, G, P)}


@pytest.mark.parametrize("metode,url,boleh", MATRIKS, ids=[f"{m[0]} {m[1]}" for m in MATRIKS])
def test_matriks_izin_setiap_peran(klien_peran, metode, url, boleh):
    for peran, klien in klien_peran.items():
        kode = getattr(klien, metode)(url, {}, format="json").status_code
        if peran in boleh:
            assert kode != 403, f"{peran} seharusnya boleh {metode} {url}"
        else:
            assert kode == 403, f"{peran} seharusnya ditolak {metode} {url}, dapat {kode}"


def test_tabel_izin_sesuai_plan():
    assert IZIN_PERAN[A] == {"lihat_produk", "kelola_transaksi"}
    assert IZIN_PERAN[G] == {"lihat_produk", "kelola_stok"}
    assert IZIN_PERAN[P] == set(SEMUA_IZIN)


def _semua_pola(pola=None, awalan=""):
    for p in pola if pola is not None else get_resolver().url_patterns:
        if isinstance(p, URLResolver):
            yield from _semua_pola(p.url_patterns, awalan + str(p.pattern))
        elif isinstance(p, URLPattern):
            yield awalan + str(p.pattern), p.callback


PUBLIK = {"api/kesehatan/", "api/auth/sesi/"}


def _url_contoh(pola: str) -> str:
    import re

    return "/" + re.sub(r"\(\?P<[^>]+>[^)]*\)", "1", pola).replace("^", "").replace("$", "")


@pytest.mark.django_db
def test_semua_endpoint_kita_wajib_login():
    klien = APIClient()
    diperiksa = 0
    for pola, _ in _semua_pola():
        if not pola.startswith("api/") or pola.startswith("api/_allauth") or pola in PUBLIK:
            continue
        kode = {
            getattr(klien, m)(_url_contoh(pola), {}).status_code for m in ("get", "post", "patch")
        }
        assert kode <= {401, 405}, f"{pola} terbuka: {kode}"
        diperiksa += 1
    assert diperiksa > 25


def test_view_baru_tanpa_deklarasi_izin_ditolak(admin):
    class ViewLupa:
        action = "list"

    class Permintaan:
        user = admin
        method = "GET"

    assert PunyaIzin().has_permission(Permintaan(), ViewLupa()) is False


def test_pengguna_tanpa_peran_tidak_punya_akses(db):
    klien = klien_untuk(buat_pengguna("kosong", None))
    assert klien.get("/api/produk/").status_code == 403


def test_pemilik_tanpa_2fa_diarahkan_mengaktifkan(db):
    pengguna = buat_pengguna("p2", PEMILIK)
    pengguna.authenticator_set.all().delete()
    klien = klien_untuk(pengguna)

    r = klien.get("/api/produk/")

    assert r.status_code == 403
    assert r.data["kode"] == "wajib_2fa"
    sesi = klien.get("/api/auth/sesi/")
    assert sesi.data["pengguna"]["punya_2fa"] is False


def test_pemilik_terakhir_tidak_bisa_diturunkan(klien_pemilik, pemilik):
    r = klien_pemilik.patch(f"/api/pengguna/{pemilik.id}/", {"aktif": False}, format="json")
    assert r.status_code == 409
    r = klien_pemilik.patch(f"/api/pengguna/{pemilik.id}/", {"peran": A}, format="json")
    assert r.status_code == 409


def test_buat_pengguna_validasi_password_dan_tidak_membocorkan(klien_pemilik):
    lemah = klien_pemilik.post(
        "/api/pengguna/",
        {"username": "baru", "password": "123", "peran": A},
        format="json",
    )
    assert lemah.status_code == 400
    r = klien_pemilik.post(
        "/api/pengguna/",
        {"username": "baru", "password": "kata-sandi-kuat-99", "peran": A},
        format="json",
    )
    assert r.status_code == 201
    assert "password" not in r.data


def test_log_aktivitas_mencatat_pelaku_tanpa_password(klien_pemilik):
    klien_pemilik.post(
        "/api/pengguna/",
        {"username": "baru", "password": "kata-sandi-kuat-99", "peran": A},
        format="json",
    )
    klien_pemilik.post("/api/kategori/", {"nama": "Gelas"}, format="json")
    r = klien_pemilik.get("/api/log-aktivitas/")
    assert r.status_code == 200
    teks = str(r.data)
    assert "pbkdf2" not in teks
    baris = next(b for b in r.data["results"] if b["keterangan"] == "Gelas")
    assert baris["pengguna"] == "pemilik"
