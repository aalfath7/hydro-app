from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

LIHAT_PRODUK = "lihat_produk"
KELOLA_TRANSAKSI = "kelola_transaksi"
KELOLA_STOK = "kelola_stok"
UBAH_PRODUK = "ubah_produk"
SETUJUI_PEMBATALAN = "setujui_pembatalan"
SETUJUI_OPNAME = "setujui_opname"
LIHAT_LAPORAN = "lihat_laporan"
KELOLA_PENGGUNA = "kelola_pengguna"

# Penanda endpoint yang cukup login, tanpa izin khusus.
HANYA_LOGIN = "hanya_login"

ADMIN_PENJUALAN = "admin_penjualan"
STAF_GUDANG = "staf_gudang"
PEMILIK = "pemilik"

SEMUA_IZIN = [
    LIHAT_PRODUK,
    KELOLA_TRANSAKSI,
    KELOLA_STOK,
    UBAH_PRODUK,
    SETUJUI_PEMBATALAN,
    SETUJUI_OPNAME,
    LIHAT_LAPORAN,
    KELOLA_PENGGUNA,
]

IZIN_PERAN: dict[str, set[str]] = {
    ADMIN_PENJUALAN: {LIHAT_PRODUK, KELOLA_TRANSAKSI},
    STAF_GUDANG: {LIHAT_PRODUK, KELOLA_STOK},
    PEMILIK: set(SEMUA_IZIN),
}


class Wajib2FA(PermissionDenied):
    default_code = "wajib_2fa"
    default_detail = "Aktifkan 2FA terlebih dahulu untuk melanjutkan."


def izin_untuk(view, request) -> str | None:
    """Izin yang dibutuhkan view. None berarti belum dideklarasikan, jadi ditolak."""
    deklarasi = getattr(view, "izin", None)
    if isinstance(deklarasi, dict):
        kunci = getattr(view, "action", None) or request.method.lower()
        return deklarasi.get(kunci)
    return deklarasi


class PunyaIzin(BasePermission):
    """Izin bawaan semua endpoint. Endpoint tanpa deklarasi `izin` selalu ditolak."""

    def has_permission(self, request, view) -> bool:
        pengguna = request.user
        if not pengguna or not pengguna.is_authenticated:
            return False
        if pengguna.belum_aktifkan_2fa and not getattr(view, "lewati_2fa", False):
            raise Wajib2FA()
        izin = izin_untuk(view, request)
        if izin is None:
            return False
        return izin == HANYA_LOGIN or izin in pengguna.izin
