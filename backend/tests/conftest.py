from datetime import timedelta
from decimal import Decimal

import pytest
from allauth.mfa.models import Authenticator
from django.utils import timezone
from rest_framework.test import APIClient

from akun.models import Pengguna, Peran
from inti.izin import ADMIN_PENJUALAN, PEMILIK, STAF_GUDANG
from pembelian.models import Pelanggan
from produk.layanan import buat_produk
from produk.models import Kategori
from stok.layanan import catat_barang_masuk


def buat_pengguna(username: str, peran: str | None) -> Pengguna:
    if peran:
        # Tes transactional mengosongkan tabel, termasuk data awal dari migrasi.
        Peran.objects.get_or_create(kode=peran, defaults={"nama": peran})
    pengguna = Pengguna(username=username, peran_id=peran)
    pengguna.set_password("sandi-uji-12345")
    pengguna.save()
    if peran == PEMILIK:
        Authenticator.objects.create(
            user=pengguna, type=Authenticator.Type.TOTP, data={"secret": "uji"}
        )
    return pengguna


@pytest.fixture
def admin(db):
    return buat_pengguna("admin", ADMIN_PENJUALAN)


@pytest.fixture
def gudang(db):
    return buat_pengguna("gudang", STAF_GUDANG)


@pytest.fixture
def pemilik(db):
    return buat_pengguna("pemilik", PEMILIK)


def klien_untuk(pengguna) -> APIClient:
    klien = APIClient()
    klien.force_login(pengguna, backend="django.contrib.auth.backends.ModelBackend")
    return klien


@pytest.fixture
def klien_admin(admin):
    return klien_untuk(admin)


@pytest.fixture
def klien_gudang(gudang):
    return klien_untuk(gudang)


@pytest.fixture
def klien_pemilik(pemilik):
    return klien_untuk(pemilik)


@pytest.fixture
def pelanggan(db):
    return Pelanggan.objects.create(nama="Toko Uji", telepon="0811")


def stok_masuk(pengguna, produk, jumlah, nomor, hari=100):
    hari_ini = timezone.localdate()
    return catat_barang_masuk(
        pengguna,
        produk=produk,
        satuan=produk.satuan.get(isi_botol=1),
        jumlah=jumlah,
        nomor_batch=nomor,
        kedaluwarsa=hari_ini + timedelta(days=hari),
        tanggal=hari_ini - timedelta(days=1) if hari < 0 else hari_ini,
    ).batch


@pytest.fixture
def produk(pemilik):
    kategori = Kategori.objects.create(nama="Botol")
    return buat_produk(
        pemilik,
        sku="AMK-600",
        nama="Air 600 ml",
        kategori=kategori,
        stok_minimum=10,
        harga_botol=Decimal("3500"),
        isi_dus=24,
        harga_dus=Decimal("78000"),
    )


@pytest.fixture
def botol(produk):
    return produk.satuan.get(isi_botol=1)


@pytest.fixture
def dus(produk):
    return produk.satuan.get(isi_botol=24)
