import getpass
import os

from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError

from akun.models import Pengguna
from inti.izin import PEMILIK


class Command(BaseCommand):
    help = "Membuat akun pemilik pertama. Password dibaca dari HYDRO_PASSWORD atau ditanyakan."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("--nama", default="")

    def handle(self, *args, username, nama, **options):
        if Pengguna.objects.filter(username=username).exists():
            raise CommandError(f"Pengguna {username} sudah ada.")
        password = os.environ.get("HYDRO_PASSWORD") or getpass.getpass("Password: ")
        pengguna = Pengguna(username=username, nama=nama, peran_id=PEMILIK)
        validate_password(password, pengguna)
        pengguna.set_password(password)
        pengguna.save()
        self.stdout.write(self.style.SUCCESS(f"Pemilik {username} dibuat."))
