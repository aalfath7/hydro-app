from django.db import models


class NomorUrut(models.Model):
    kunci = models.CharField(max_length=40, primary_key=True)
    terakhir = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "nomor_urut"


def nomor_berikutnya(awalan: str, lebar: int = 4) -> str:
    """Nomor dokumen berurutan per awalan. Harus dipanggil di dalam transaksi database."""
    NomorUrut.objects.get_or_create(kunci=awalan)
    baris = NomorUrut.objects.select_for_update().get(kunci=awalan)
    baris.terakhir += 1
    baris.save(update_fields=["terakhir"])
    return f"{awalan}-{baris.terakhir:0{lebar}d}"
