from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from inti.galat import AturanBisnisError
from inti.izin import PEMILIK

from .models import Pengguna, Peran


class SesiPenggunaSerializer(serializers.ModelSerializer):
    peran_nama = serializers.CharField(source="peran.nama", read_only=True, allow_null=True)
    izin = serializers.SerializerMethodField()
    wajib_2fa = serializers.BooleanField(read_only=True)
    punya_2fa = serializers.BooleanField(read_only=True)

    class Meta:
        model = Pengguna
        fields = ["id", "username", "nama", "peran", "peran_nama", "izin", "wajib_2fa", "punya_2fa"]

    def get_izin(self, obj: Pengguna) -> list[str]:
        return sorted(obj.izin)


class SesiSerializer(serializers.Serializer):
    terautentikasi = serializers.BooleanField()
    pengguna = SesiPenggunaSerializer(allow_null=True)


class PenggunaSerializer(serializers.ModelSerializer):
    peran_nama = serializers.CharField(source="peran.nama", read_only=True, allow_null=True)
    punya_2fa = serializers.BooleanField(read_only=True)
    aktif = serializers.BooleanField(source="is_active", required=False)
    terakhir_login = serializers.DateTimeField(source="last_login", read_only=True)

    class Meta:
        model = Pengguna
        fields = [
            "id",
            "username",
            "nama",
            "peran",
            "peran_nama",
            "aktif",
            "punya_2fa",
            "terakhir_login",
        ]
        extra_kwargs = {"peran": {"required": True, "allow_null": False}}

    def validate(self, attrs):
        akun = self.instance
        if akun and akun.peran_id == PEMILIK:
            turun = attrs.get("peran", akun.peran).pk != PEMILIK
            nonaktif = not attrs.get("is_active", True)
            if turun or nonaktif:
                self._pastikan_bukan_pemilik_terakhir(akun)
        return attrs

    @staticmethod
    def _pastikan_bukan_pemilik_terakhir(akun: Pengguna) -> None:
        lain = (
            Pengguna.objects.select_for_update()
            .filter(peran_id=PEMILIK, is_active=True)
            .exclude(pk=akun.pk)
        )
        with transaction.atomic():
            if not lain.exists():
                raise AturanBisnisError(
                    "Harus ada minimal satu pemilik aktif.", kode="pemilik_terakhir"
                )


class PenggunaBuatSerializer(PenggunaSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta(PenggunaSerializer.Meta):
        fields = [*PenggunaSerializer.Meta.fields, "password"]

    def validate_password(self, nilai: str) -> str:
        validate_password(nilai)
        return nilai

    def create(self, validated_data):
        password = validated_data.pop("password")
        pengguna = Pengguna(**validated_data)
        pengguna.set_password(password)
        pengguna.save()
        return pengguna


class AturPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)

    def validate_password(self, nilai: str) -> str:
        validate_password(nilai)
        return nilai


class PeranSerializer(serializers.ModelSerializer):
    izin = serializers.SerializerMethodField()

    class Meta:
        model = Peran
        fields = ["kode", "nama", "izin"]

    def get_izin(self, obj: Peran) -> list[str]:
        from inti.izin import IZIN_PERAN

        return sorted(IZIN_PERAN.get(obj.kode, set()))


class LogAktivitasSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    waktu = serializers.DateTimeField(source="timestamp")
    pengguna = serializers.CharField(source="actor.username", default=None, allow_null=True)
    aksi = serializers.CharField(source="get_action_display")
    objek = serializers.CharField(source="content_type.name")
    keterangan = serializers.CharField(source="object_repr")
    perubahan = serializers.JSONField(source="changes")
