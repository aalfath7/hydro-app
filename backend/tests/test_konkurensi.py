import threading
import uuid

import pytest
from django.db import connection

from inti.galat import AturanBisnisError
from pembelian.layanan import buat_transaksi
from pembelian.models import Pelanggan, Transaksi
from produk.layanan import buat_produk
from produk.models import Kategori
from stok.models import BatchProduk

from .conftest import buat_pengguna, stok_masuk

pytestmark = pytest.mark.django_db(transaction=True)


def _siapkan():
    pengguna = buat_pengguna("admin", "admin_penjualan")
    produk = buat_produk(
        pengguna, sku="X", nama="X", kategori=Kategori.objects.create(nama="K"), harga_botol=1000
    )
    batch = stok_masuk(pengguna, produk, 1, "A", hari=100)
    return pengguna, produk, batch, Pelanggan.objects.create(nama="P")


def _jalankan_bersamaan(n, kerja):
    gerbang = threading.Barrier(n)
    hasil = []

    def jalan(i):
        try:
            gerbang.wait()
            hasil.append(kerja(i))
        except AturanBisnisError as exc:
            hasil.append(exc.kode)
        finally:
            connection.close()

    utas = [threading.Thread(target=jalan, args=(i,)) for i in range(n)]
    for u in utas:
        u.start()
    for u in utas:
        u.join(30)
    return hasil


def test_stok_terakhir_tidak_terjual_dua_kali():
    pengguna, produk, batch, pelanggan = _siapkan()
    satuan = produk.satuan.get()

    hasil = _jalankan_bersamaan(
        8,
        lambda i: (
            buat_transaksi(
                pengguna,
                kunci_idempoten=uuid.uuid4(),
                pelanggan=pelanggan,
                items=[{"satuan": satuan.id, "jumlah": 1}],
                metode="tunai",
            ).nomor
        ),
    )

    assert hasil.count("stok_tidak_cukup") == 7
    assert Transaksi.objects.count() == 1
    assert BatchProduk.objects.get(pk=batch.pk).sisa == 0


def test_kunci_idempoten_sama_bersamaan_hanya_satu_nota():
    pengguna, produk, batch, pelanggan = _siapkan()
    BatchProduk.objects.filter(pk=batch.pk).update(sisa=50)
    satuan = produk.satuan.get()
    kunci = uuid.uuid4()

    hasil = _jalankan_bersamaan(
        6,
        lambda i: (
            buat_transaksi(
                pengguna,
                kunci_idempoten=kunci,
                pelanggan=pelanggan,
                items=[{"satuan": satuan.id, "jumlah": 1}],
                metode="tunai",
            ).nomor
        ),
    )

    assert len(set(hasil)) == 1
    assert Transaksi.objects.count() == 1
    assert BatchProduk.objects.get(pk=batch.pk).sisa == 49


def test_nomor_nota_unik_saat_bersamaan():
    pengguna, produk, batch, pelanggan = _siapkan()
    BatchProduk.objects.filter(pk=batch.pk).update(sisa=50)
    satuan = produk.satuan.get()

    hasil = _jalankan_bersamaan(
        6,
        lambda i: (
            buat_transaksi(
                pengguna,
                kunci_idempoten=uuid.uuid4(),
                pelanggan=pelanggan,
                items=[{"satuan": satuan.id, "jumlah": 1}],
                metode="tunai",
            ).nomor
        ),
    )

    assert len(set(hasil)) == 6
