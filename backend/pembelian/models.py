import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import F, Q

from produk.models import Produk, SatuanProduk
from stok.models import BatchProduk


class Pelanggan(models.Model):
    nama = models.CharField(max_length=160)
    telepon = models.CharField(max_length=30, blank=True)
    alamat = models.TextField(blank=True)
    catatan = models.TextField(blank=True)
    aktif = models.BooleanField(default=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pelanggan"
        ordering = ["nama"]

    def __str__(self) -> str:
        return self.nama


class MetodeBayar(models.TextChoices):
    TUNAI = "tunai", "Tunai"
    TRANSFER = "transfer", "Transfer"
    QRIS = "qris", "QRIS"


class StatusTransaksi(models.TextChoices):
    SELESAI = "selesai", "Selesai"
    MENUNGGU_BATAL = "menunggu_batal", "Menunggu pembatalan"
    DIBATALKAN = "dibatalkan", "Dibatalkan"


class Transaksi(models.Model):
    nomor = models.CharField(max_length=30, unique=True)
    kunci_idempoten = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    pelanggan = models.ForeignKey(Pelanggan, on_delete=models.PROTECT, related_name="transaksi")
    tanggal = models.DateTimeField(auto_now_add=True, db_index=True)
    status = models.CharField(
        max_length=16, choices=StatusTransaksi.choices, default=StatusTransaksi.SELESAI
    )
    tempo = models.BooleanField(default=False)
    jatuh_tempo = models.DateField(null=True, blank=True)
    total = models.DecimalField(max_digits=18, decimal_places=2)
    total_retur = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    terbayar = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal("0"))
    sisa_tagihan = models.GeneratedField(
        expression=F("total") - F("total_retur") - F("terbayar"),
        output_field=models.DecimalField(max_digits=18, decimal_places=2),
        db_persist=True,
    )
    catatan = models.TextField(blank=True)
    dibuat_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="transaksi_dibuat"
    )
    alasan_batal = models.CharField(max_length=255, blank=True)
    batal_diajukan_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="batal_diajukan",
    )
    batal_diputuskan_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="batal_diputuskan",
    )
    dibatalkan_pada = models.DateTimeField(null=True, blank=True)
    alasan_tolak_batal = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "transaksi"
        ordering = ["-tanggal", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(total__gte=F("total_retur") + F("terbayar")),
                name="tagihan_tidak_minus",
            ),
            models.CheckConstraint(condition=Q(terbayar__gte=0), name="terbayar_tidak_minus"),
        ]

    def __str__(self) -> str:
        return self.nomor

    @property
    def sisa(self) -> Decimal:
        """Sisa tagihan dari nilai di memori, aman dipakai setelah objek diubah."""
        return self.total - self.total_retur - self.terbayar


class ItemTransaksi(models.Model):
    transaksi = models.ForeignKey(Transaksi, on_delete=models.PROTECT, related_name="items")
    produk = models.ForeignKey(Produk, on_delete=models.PROTECT)
    satuan = models.ForeignKey(SatuanProduk, on_delete=models.PROTECT)
    nama_produk = models.CharField(max_length=160)
    nama_satuan = models.CharField(max_length=30)
    isi_botol = models.PositiveIntegerField()
    jumlah = models.PositiveIntegerField()
    harga_satuan = models.DecimalField(max_digits=18, decimal_places=2)
    subtotal = models.DecimalField(max_digits=18, decimal_places=2)

    class Meta:
        db_table = "item_transaksi"
        ordering = ["id"]

    @property
    def total_botol(self) -> int:
        return self.jumlah * self.isi_botol


class ItemTransaksiBatch(models.Model):
    item = models.ForeignKey(ItemTransaksi, on_delete=models.PROTECT, related_name="alokasi")
    batch = models.ForeignKey(BatchProduk, on_delete=models.PROTECT, related_name="alokasi")
    jumlah_botol = models.PositiveIntegerField()
    jumlah_diretur = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "item_transaksi_batch"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["item", "batch"], name="alokasi_unik"),
            models.CheckConstraint(
                condition=Q(jumlah_diretur__lte=F("jumlah_botol")),
                name="retur_tidak_melebihi_alokasi",
            ),
        ]


class JenisPembayaran(models.TextChoices):
    BAYAR = "bayar", "Pembayaran"
    KEMBALI = "kembali", "Pengembalian uang"


class Pembayaran(models.Model):
    transaksi = models.ForeignKey(Transaksi, on_delete=models.PROTECT, related_name="pembayaran")
    jenis = models.CharField(
        max_length=10, choices=JenisPembayaran.choices, default=JenisPembayaran.BAYAR
    )
    metode = models.CharField(max_length=10, choices=MetodeBayar.choices)
    jumlah = models.DecimalField(max_digits=18, decimal_places=2)
    referensi = models.CharField(max_length=80, blank=True)
    catatan = models.CharField(max_length=255, blank=True)
    dibuat_oleh = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pembayaran"
        ordering = ["dibuat_pada", "id"]
        constraints = [models.CheckConstraint(condition=Q(jumlah__gt=0), name="pembayaran_positif")]

    def __str__(self) -> str:
        return f"{self.get_jenis_display()} {self.jumlah}"


class Retur(models.Model):
    nomor = models.CharField(max_length=30, unique=True)
    transaksi = models.ForeignKey(Transaksi, on_delete=models.PROTECT, related_name="retur")
    tanggal = models.DateTimeField(auto_now_add=True, db_index=True)
    alasan = models.CharField(max_length=255)
    total = models.DecimalField(max_digits=18, decimal_places=2)
    potong_piutang = models.DecimalField(max_digits=18, decimal_places=2)
    pengembalian_uang = models.DecimalField(max_digits=18, decimal_places=2)
    dibuat_oleh = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        db_table = "retur"
        ordering = ["-tanggal", "-id"]

    def __str__(self) -> str:
        return self.nomor


class KondisiRetur(models.TextChoices):
    LAYAK = "layak", "Layak jual"
    RUSAK = "rusak", "Rusak"


class ReturItem(models.Model):
    retur = models.ForeignKey(Retur, on_delete=models.PROTECT, related_name="items")
    alokasi = models.ForeignKey(ItemTransaksiBatch, on_delete=models.PROTECT, related_name="retur")
    jumlah_botol = models.PositiveIntegerField()
    kondisi = models.CharField(max_length=8, choices=KondisiRetur.choices)
    nilai = models.DecimalField(max_digits=18, decimal_places=2)

    class Meta:
        db_table = "retur_item"
        ordering = ["id"]
