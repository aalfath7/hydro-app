from datetime import date

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import OuterRef, Subquery


class Kategori(models.Model):
    nama = models.CharField(max_length=80, unique=True)
    aktif = models.BooleanField(default=True)

    class Meta:
        db_table = "kategori"
        ordering = ["nama"]

    def __str__(self) -> str:
        return self.nama


def lokasi_foto(instance: "Produk", nama_file: str) -> str:
    ekstensi = nama_file.rsplit(".", 1)[-1].lower()
    return f"produk/{instance.pk}.{ekstensi}"


class Produk(models.Model):
    sku = models.CharField(max_length=40, unique=True)
    nama = models.CharField(max_length=160)
    kategori = models.ForeignKey(Kategori, on_delete=models.PROTECT, related_name="produk")
    ukuran_ml = models.PositiveIntegerField(null=True, blank=True)
    kemasan = models.CharField(max_length=60, blank=True)
    foto = models.ImageField(upload_to=lokasi_foto, blank=True)
    stok_minimum = models.PositiveIntegerField(default=0, help_text="Dalam satuan botol")
    aktif = models.BooleanField(default=True)
    dibuat_pada = models.DateTimeField(auto_now_add=True)
    diubah_pada = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "produk"
        ordering = ["nama"]

    def __str__(self) -> str:
        return f"{self.sku} {self.nama}"


class SatuanQuerySet(models.QuerySet):
    def dengan_harga(self, tanggal: date) -> "SatuanQuerySet":
        terbaru = (
            HargaProduk.objects.filter(satuan=OuterRef("pk"), berlaku_mulai__lte=tanggal)
            .order_by("-berlaku_mulai")
            .values("harga")[:1]
        )
        return self.annotate(harga=Subquery(terbaru))


class SatuanProduk(models.Model):
    produk = models.ForeignKey(Produk, on_delete=models.PROTECT, related_name="satuan")
    nama = models.CharField(max_length=30)
    isi_botol = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    aktif = models.BooleanField(default=True)

    objects = SatuanQuerySet.as_manager()

    class Meta:
        db_table = "satuan_produk"
        ordering = ["isi_botol"]
        constraints = [
            models.UniqueConstraint(fields=["produk", "nama"], name="satuan_unik_per_produk"),
            models.CheckConstraint(condition=models.Q(isi_botol__gte=1), name="isi_botol_positif"),
        ]

    def __str__(self) -> str:
        return f"{self.nama} ({self.isi_botol} botol)"


class HargaProduk(models.Model):
    satuan = models.ForeignKey(SatuanProduk, on_delete=models.PROTECT, related_name="riwayat_harga")
    harga = models.DecimalField(max_digits=18, decimal_places=2)
    berlaku_mulai = models.DateField()
    dibuat_oleh = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "harga_produk"
        ordering = ["-berlaku_mulai"]
        constraints = [
            models.UniqueConstraint(
                fields=["satuan", "berlaku_mulai"], name="harga_unik_per_tanggal"
            ),
            models.CheckConstraint(condition=models.Q(harga__gte=0), name="harga_tidak_negatif"),
        ]

    def __str__(self) -> str:
        return f"{self.harga} mulai {self.berlaku_mulai}"
