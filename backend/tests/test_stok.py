from datetime import timedelta

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from stok.models import BatchProduk, MutasiStok

from .conftest import stok_masuk
from .test_pembelian import jual


def test_barang_masuk_dalam_dus_disimpan_sebagai_botol(klien_gudang, produk, dus):
    hari_ini = timezone.localdate()
    r = klien_gudang.post(
        "/api/barang-masuk/",
        {
            "produk": produk.id,
            "satuan": dus.id,
            "jumlah": 10,
            "nomor_batch": "B1",
            "kedaluwarsa": (hari_ini + timedelta(days=90)).isoformat(),
        },
        format="json",
    )
    assert r.status_code == 201, r.data
    assert r.data["jumlah_botol"] == 240
    batch = BatchProduk.objects.get(nomor_batch="B1")
    assert batch.sisa == 240
    assert MutasiStok.objects.filter(batch=batch, jenis="masuk", jumlah=240).exists()

    p = klien_gudang.get(f"/api/produk/{produk.id}/")
    assert p.data["stok_tersedia"] == 240
    assert p.data["stok_teks"] == "10 dus"


def test_barang_masuk_validasi(klien_gudang, produk, dus):
    hari_ini = timezone.localdate()
    dasar = {"produk": produk.id, "satuan": dus.id, "jumlah": 1, "nomor_batch": "B"}
    lewat = klien_gudang.post(
        "/api/barang-masuk/", {**dasar, "kedaluwarsa": hari_ini.isoformat()}, format="json"
    )
    assert lewat.status_code == 400
    assert "kedaluwarsa" in lewat.data["rincian"]

    baik = {**dasar, "kedaluwarsa": (hari_ini + timedelta(days=9)).isoformat()}
    assert klien_gudang.post("/api/barang-masuk/", baik, format="json").status_code == 201
    ganda = klien_gudang.post("/api/barang-masuk/", baik, format="json")
    assert ganda.status_code == 400
    assert "nomor_batch" in ganda.data["rincian"]


def test_stok_teks_dus_dan_botol(klien_gudang, pemilik, produk):
    stok_masuk(pemilik, produk, 2888, "A")
    p = klien_gudang.get(f"/api/produk/{produk.id}/")
    assert p.data["stok_teks"] == "120 dus 8 botol"


def test_status_stok_filter(klien_gudang, pemilik, produk):
    stok_masuk(pemilik, produk, 10, "A")
    assert klien_gudang.get("/api/produk/", {"status": "menipis"}).data["count"] == 1
    assert klien_gudang.get("/api/produk/", {"status": "aman"}).data["count"] == 0
    assert klien_gudang.get("/api/produk/").data["results"][0]["status_stok"] == "menipis"


def test_database_menolak_sisa_minus(pemilik, produk):
    batch = stok_masuk(pemilik, produk, 1, "A")
    with pytest.raises(IntegrityError), transaction.atomic():
        BatchProduk.objects.filter(pk=batch.pk).update(sisa=-1)


def test_kurangi_rusak_tercatat_tersendiri(klien_gudang, pemilik, produk):
    batch = stok_masuk(pemilik, produk, 5, "A")
    r = klien_gudang.post(
        f"/api/batch/{batch.id}/kurangi/",
        {"jenis": "rusak", "jumlah": 2, "catatan": "Pecah"},
        format="json",
    )
    assert r.status_code == 200
    assert r.data["sisa"] == 3
    assert MutasiStok.objects.filter(batch=batch, jenis="rusak", jumlah=-2).exists()

    lebih = klien_gudang.post(
        f"/api/batch/{batch.id}/kurangi/",
        {"jenis": "kedaluwarsa", "jumlah": 9, "catatan": "x"},
        format="json",
    )
    assert lebih.status_code == 409


def test_opname_menerapkan_selisih_saat_disetujui(klien_gudang, klien_pemilik, pemilik, produk):
    batch = stok_masuk(pemilik, produk, 10, "A")
    r = klien_gudang.post(
        "/api/opname/", {"items": [{"batch": batch.id, "stok_fisik": 7}]}, format="json"
    )
    assert r.status_code == 201
    assert r.data["items"][0]["selisih"] == -3
    batch.refresh_from_db()
    assert batch.sisa == 10

    assert klien_gudang.post(f"/api/opname/{r.data['id']}/setujui/").status_code == 403

    s = klien_pemilik.post(f"/api/opname/{r.data['id']}/setujui/")
    assert s.data["status"] == "disetujui"
    batch.refresh_from_db()
    assert batch.sisa == 7
    assert MutasiStok.objects.filter(batch=batch, jenis="opname", jumlah=-3).exists()

    ulang = klien_pemilik.post(f"/api/opname/{r.data['id']}/setujui/")
    assert ulang.status_code == 409
    batch.refresh_from_db()
    assert batch.sisa == 7


def test_opname_memperhitungkan_penjualan_setelah_hitung(
    klien_gudang, klien_pemilik, klien_admin, pemilik, pelanggan, produk, botol
):
    batch = stok_masuk(pemilik, produk, 10, "A")
    r = klien_gudang.post(
        "/api/opname/", {"items": [{"batch": batch.id, "stok_fisik": 9}]}, format="json"
    )
    jual(klien_admin, pelanggan, [{"satuan": botol.id, "jumlah": 4}])

    klien_pemilik.post(f"/api/opname/{r.data['id']}/setujui/")

    batch.refresh_from_db()
    assert batch.sisa == 5


def test_opname_ditolak_tidak_mengubah_stok(klien_gudang, klien_pemilik, pemilik, produk):
    batch = stok_masuk(pemilik, produk, 10, "A")
    r = klien_gudang.post(
        "/api/opname/", {"items": [{"batch": batch.id, "stok_fisik": 1}]}, format="json"
    )
    klien_pemilik.post(f"/api/opname/{r.data['id']}/tolak/")
    batch.refresh_from_db()
    assert batch.sisa == 10


def test_opname_ganda_pada_batch_yang_sama_ditolak(klien_gudang, pemilik, produk):
    batch = stok_masuk(pemilik, produk, 10, "A")
    data = {"items": [{"batch": batch.id, "stok_fisik": 9}]}
    assert klien_gudang.post("/api/opname/", data, format="json").status_code == 201
    kedua = klien_gudang.post("/api/opname/", data, format="json")
    assert kedua.status_code == 409
    assert kedua.data["kode"] == "opname_bentrok"
