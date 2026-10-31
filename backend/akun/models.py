from allauth.mfa.models import Authenticator
from django.contrib.auth.models import AbstractUser
from django.db import models

from inti.izin import IZIN_PERAN, PEMILIK


class Peran(models.Model):
    kode = models.CharField(max_length=30, primary_key=True)
    nama = models.CharField(max_length=60)

    class Meta:
        db_table = "peran"
        ordering = ["nama"]

    def __str__(self) -> str:
        return self.nama


class Pengguna(AbstractUser):
    nama = models.CharField(max_length=120, blank=True)
    peran = models.ForeignKey(Peran, null=True, blank=True, on_delete=models.PROTECT)

    class Meta:
        db_table = "pengguna"
        ordering = ["username"]

    @property
    def izin(self) -> set[str]:
        return IZIN_PERAN.get(self.peran_id or "", set())

    @property
    def punya_2fa(self) -> bool:
        return Authenticator.objects.filter(user=self, type=Authenticator.Type.TOTP).exists()

    @property
    def wajib_2fa(self) -> bool:
        return self.peran_id == PEMILIK

    @property
    def belum_aktifkan_2fa(self) -> bool:
        return self.wajib_2fa and not self.punya_2fa
