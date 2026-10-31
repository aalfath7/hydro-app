from django.urls import include, path
from rest_framework.routers import SimpleRouter

from akun.views import (
    LogAktivitasViewSet,
    PenggunaViewSet,
    PeranViewSet,
    SesiView,
    kesehatan,
)
from laporan.views import (
    DasborView,
    LaporanPenjualanView,
    LaporanPiutangView,
    LaporanStokView,
    LaporanTerlarisView,
)
from pembelian.views import PelangganViewSet, ReturViewSet, TransaksiViewSet
from produk.views import HargaViewSet, KategoriViewSet, ProdukViewSet, SatuanViewSet
from stok.views import BarangMasukViewSet, BatchViewSet, MutasiViewSet, OpnameViewSet

router = SimpleRouter()
router.register("kategori", KategoriViewSet, basename="kategori")
router.register("produk", ProdukViewSet, basename="produk")
router.register("satuan", SatuanViewSet, basename="satuan")
router.register("harga", HargaViewSet, basename="harga")
router.register("batch", BatchViewSet, basename="batch")
router.register("mutasi", MutasiViewSet, basename="mutasi")
router.register("barang-masuk", BarangMasukViewSet, basename="barang-masuk")
router.register("opname", OpnameViewSet, basename="opname")
router.register("pelanggan", PelangganViewSet, basename="pelanggan")
router.register("transaksi", TransaksiViewSet, basename="transaksi")
router.register("retur", ReturViewSet, basename="retur")
router.register("pengguna", PenggunaViewSet, basename="pengguna")
router.register("peran", PeranViewSet, basename="peran")
router.register("log-aktivitas", LogAktivitasViewSet, basename="log-aktivitas")

urlpatterns = [
    path("api/kesehatan/", kesehatan),
    path("api/_allauth/", include("allauth.headless.urls")),
    path("api/auth/sesi/", SesiView.as_view()),
    path("api/dasbor/", DasborView.as_view()),
    path("api/laporan/penjualan/", LaporanPenjualanView.as_view()),
    path("api/laporan/produk-terlaris/", LaporanTerlarisView.as_view()),
    path("api/laporan/stok/", LaporanStokView.as_view()),
    path("api/laporan/piutang/", LaporanPiutangView.as_view()),
    path("api/", include(router.urls)),
]
