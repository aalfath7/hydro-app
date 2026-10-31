from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from akun.models import Pengguna
from inti.izin import ADMIN_PENJUALAN, PEMILIK, STAF_GUDANG
from pembelian.models import Pelanggan
from produk.layanan import buat_produk
from produk.models import Kategori, Produk
from stok.layanan import catat_barang_masuk


class Command(BaseCommand):
    help = "Mengisi data contoh untuk development. Ditolak kalau DEBUG mati."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("isi_demo hanya untuk development.")
        for username, peran in [
            ("pemilik", PEMILIK),
            ("admin", ADMIN_PENJUALAN),
            ("gudang", STAF_GUDANG),
        ]:
            if not Pengguna.objects.filter(username=username).exists():
                akun = Pengguna(username=username, nama=username.title(), peran_id=peran)
                akun.set_password("hydro-demo-123")
                akun.save()

        pemilik = Pengguna.objects.get(username="pemilik")
        kategori, _ = Kategori.objects.get_or_create(nama="Botol")
        galon, _ = Kategori.objects.get_or_create(nama="Galon")
        hari_ini = timezone.localdate()
        daftar = [
            ("AMK-330", "Air Mineral 330 ml", kategori, 330, 2500, 24, 54000, 480, 1200, 300),
            ("AMK-600", "Air Mineral 600 ml", kategori, 600, 3500, 24, 78000, 480, 960, 240),
            ("AMK-1500", "Air Mineral 1500 ml", kategori, 1500, 6000, 12, 66000, 120, 96, 30),
            ("GLN-19L", "Galon 19 L", galon, 19000, 20000, None, None, 50, 40, 400),
        ]
        for sku, nama, kat, ml, h_botol, isi, h_dus, minimum, jumlah, umur in daftar:
            if Produk.objects.filter(sku=sku).exists():
                continue
            produk = buat_produk(
                pemilik,
                sku=sku,
                nama=nama,
                kategori=kat,
                ukuran_ml=ml,
                kemasan="Galon" if isi is None else "Botol",
                stok_minimum=minimum,
                harga_botol=Decimal(h_botol),
                isi_dus=isi,
                harga_dus=Decimal(h_dus) if h_dus else None,
            )
            catat_barang_masuk(
                pemilik,
                produk=produk,
                satuan=produk.satuan.get(isi_botol=1),
                jumlah=jumlah,
                nomor_batch=f"{sku}-A",
                kedaluwarsa=hari_ini + timedelta(days=umur),
                tanggal=hari_ini,
                sumber="Produksi",
            )
        for nama, telepon in [("Pelanggan Umum", ""), ("Toko Berkah", "081234567890")]:
            Pelanggan.objects.get_or_create(nama=nama, defaults={"telepon": telepon})
        self.stdout.write(self.style.SUCCESS("Data contoh siap. Password: hydro-demo-123"))
