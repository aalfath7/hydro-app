from django.db import migrations

PERAN = [
    ("admin_penjualan", "Admin penjualan"),
    ("staf_gudang", "Staf gudang"),
    ("pemilik", "Pemilik/manajer"),
]


def isi_peran(apps, schema_editor):
    Peran = apps.get_model("akun", "Peran")
    for kode, nama in PERAN:
        Peran.objects.update_or_create(kode=kode, defaults={"nama": nama})


class Migration(migrations.Migration):
    dependencies = [("akun", "0001_initial")]

    operations = [migrations.RunPython(isi_peran, migrations.RunPython.noop)]
