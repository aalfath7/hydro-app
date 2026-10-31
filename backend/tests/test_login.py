import pyotp
import pytest
from allauth.mfa.adapter import get_adapter
from allauth.mfa.models import Authenticator
from django.test import Client, override_settings

from .conftest import buat_pengguna

BASIS = "/api/_allauth/browser/v1"


def login(klien, username, password="sandi-uji-12345"):
    return klien.post(
        f"{BASIS}/auth/login",
        {"username": username, "password": password},
        content_type="application/json",
    )


def aktifkan_totp(pengguna) -> str:
    rahasia = pyotp.random_base32()
    Authenticator.objects.filter(user=pengguna).delete()
    Authenticator.objects.create(
        user=pengguna,
        type=Authenticator.Type.TOTP,
        data={"secret": get_adapter().encrypt(rahasia)},
    )
    return rahasia


@pytest.mark.django_db
def test_login_biasa_lalu_logout():
    buat_pengguna("admin", "admin_penjualan")
    klien = Client()
    assert klien.get("/api/produk/").status_code == 401
    assert login(klien, "admin").status_code == 200
    assert klien.get("/api/produk/").status_code == 200
    klien.delete(f"{BASIS}/auth/session")
    assert klien.get("/api/produk/").status_code == 401


@pytest.mark.django_db
def test_password_salah_ditolak():
    buat_pengguna("admin", "admin_penjualan")
    klien = Client()
    assert login(klien, "admin", "salah-salah").status_code == 400
    assert klien.get("/api/produk/").status_code == 401


@pytest.mark.django_db
def test_login_dengan_2fa_belum_memberi_akses_sebelum_kode():
    pengguna = buat_pengguna("p", "pemilik")
    rahasia = aktifkan_totp(pengguna)
    klien = Client()

    r = login(klien, "p")

    assert r.status_code == 401
    assert any(f["id"] == "mfa_authenticate" for f in r.json()["data"]["flows"])
    assert klien.get("/api/produk/").status_code == 401

    salah = klien.post(
        f"{BASIS}/auth/2fa/authenticate", {"code": "000000"}, content_type="application/json"
    )
    assert salah.status_code == 400

    benar = klien.post(
        f"{BASIS}/auth/2fa/authenticate",
        {"code": pyotp.TOTP(rahasia).now()},
        content_type="application/json",
    )
    assert benar.status_code == 200
    assert klien.get("/api/produk/").status_code == 200


@pytest.mark.django_db
def test_pendaftaran_publik_tertutup():
    r = Client().post(
        f"{BASIS}/auth/signup",
        {"username": "tamu", "password": "kata-sandi-kuat-99"},
        content_type="application/json",
    )
    assert r.status_code in (403, 404)


@pytest.mark.django_db
@override_settings(AXES_ENABLED=True)
def test_percobaan_login_dibatasi():
    buat_pengguna("admin", "admin_penjualan")
    klien = Client()
    for _ in range(5):
        login(klien, "admin", "salah-salah")
    assert login(Client(), "admin").status_code != 200
