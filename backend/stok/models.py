from django.conf import settings
from django.db import models
from django.utils import timezone

from produk.models import Produk, SatuanProduk


class BarangMasuk(models.Model):
    nomor = models.CharField(max_length=30, unique=True)
    produk = models.ForeignKey(Produk, on_delete=models.PROTECT, related_name="barang_masuk")
    satuan = models.ForeignKey(SatuanProduk, on_delete=models.PROTECT)
    jumlah = models.PositiveIntegerField()
    isi_botol = models.PositiveIntegerField()
    jumlah_botol = models.PositiveIntegerField()
    tanggal = models.DateField()
    sumber = models.CharField(max_length=160, blank=True)
    catatan = models.TextField(blank=True)
    dibuat_oleh = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "barang_masuk"
        ordering = ["-dibuat_pada", "-id"]

    def __str__(self) -> str:
        return self.nomor


class BatchQuerySet(models.QuerySet):
    def layak_jual(self) -> "BatchQuerySet":
        return self.filter(sisa__gt=0, kedaluwarsa__gte=timezone.localdate())


class BatchProduk(models.Model):
    produk = models.ForeignKey(Produk, on_delete=models.PROTECT, related_name="batch")
    barang_masuk = models.OneToOneField(BarangMasuk, on_delete=models.PROTECT, related_name="batch")
    nomor_batch = models.CharField(max_length=60)
    kedaluwarsa = models.DateField()
    jumlah_awal = models.PositiveIntegerField()
    sisa = models.IntegerField()

    objects = BatchQuerySet.as_manager()

    class Meta:
        db_table = "batch_produk"
        ordering = ["kedaluwarsa", "id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(sisa__gte=0), name="sisa_tidak_minus"),
            models.UniqueConstraint(fields=["produk", "nomor_batch"], name="batch_unik_per_produk"),
        ]
        indexes = [models.Index(fields=["produk", "kedaluwarsa"], name="batch_produk_exp_idx")]

    def __str__(self) -> str:
        return self.nomor_batch


class JenisMutasi(models.TextChoices):
    MASUK = "masuk", "Barang masuk"
    PENJUALAN = "penjualan", "Penjualan"
    RETUR = "retur", "Retur pelanggan"
    RUSAK = "rusak", "Barang rusak"
    KEDALUWARSA = "kedaluwarsa", "Kedaluwarsa"
    OPNAME = "opname", "Stok opname"
    BATAL = "batal", "Pembatalan transaksi"


class MutasiStok(models.Model):
    batch = models.ForeignKey(BatchProduk, on_delete=models.PROTECT, related_name="mutasi")
    jenis = models.CharField(max_length=20, choices=JenisMutasi.choices)
    jumlah = models.IntegerField(help_text="Positif masuk, negatif keluar, dalam botol")
    sisa_sesudah = models.IntegerField()
    referensi = models.CharField(max_length=40, blank=True)
    catatan = models.CharField(max_length=255, blank=True)
    dibuat_oleh = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mutasi_stok"
        ordering = ["-dibuat_pada", "-id"]


class StatusOpname(models.TextChoices):
    MENUNGGU = "menunggu", "Menunggu persetujuan"
    DISETUJUI = "disetujui", "Disetujui"
    DITOLAK = "ditolak", "Ditolak"


class StokOpname(models.Model):
    nomor = models.CharField(max_length=30, unique=True)
    status = models.CharField(
        max_length=12, choices=StatusOpname.choices, default=StatusOpname.MENUNGGU
    )
    catatan = models.TextField(blank=True)
    dibuat_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="opname_dibuat"
    )
    dibuat_pada = models.DateTimeField(auto_now_add=True)
    diputuskan_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="opname_diputuskan",
    )
    diputuskan_pada = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "stok_opname"
        ordering = ["-dibuat_pada", "-id"]

    def __str__(self) -> str:
        return self.nomor


class StokOpnameItem(models.Model):
    opname = models.ForeignKey(StokOpname, on_delete=models.CASCADE, related_name="items")
    batch = models.ForeignKey(BatchProduk, on_delete=models.PROTECT)
    stok_tercatat = models.IntegerField()
    stok_fisik = models.PositiveIntegerField()
    selisih = models.IntegerField()

    class Meta:
        db_table = "stok_opname_item"
        constraints = [
            models.UniqueConstraint(fields=["opname", "batch"], name="batch_unik_per_opname")
        ]
