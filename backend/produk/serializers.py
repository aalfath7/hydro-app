from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from inti.format import stok_teks

from .layanan import buat_produk, catat_harga, satuan_terbesar, status_stok
from .models import HargaProduk, Kategori, Produk, SatuanProduk


class KategoriSerializer(serializers.ModelSerializer):
    class Meta:
        model = Kategori
        fields = ["id", "nama", "aktif"]


class SatuanSerializer(serializers.ModelSerializer):
    harga = serializers.DecimalField(
        max_digits=18, decimal_places=2, read_only=True, allow_null=True
    )

    class Meta:
        model = SatuanProduk
        fields = ["id", "nama", "isi_botol", "aktif", "harga"]


class SatuanBuatSerializer(serializers.ModelSerializer):
    harga = serializers.DecimalField(
        max_digits=18, decimal_places=2, min_value=Decimal("0"), write_only=True
    )

    class Meta:
        model = SatuanProduk
        fields = ["id", "produk", "nama", "isi_botol", "harga"]

    def create(self, validated_data):
        harga = validated_data.pop("harga")
        satuan = SatuanProduk.objects.create(**validated_data)
        catat_harga(satuan, harga, timezone.localdate(), self.context["request"].user)
        return satuan


class SatuanUbahSerializer(serializers.ModelSerializer):
    class Meta:
        model = SatuanProduk
        fields = ["id", "nama", "aktif"]


class HargaSerializer(serializers.ModelSerializer):
    dibuat_oleh_nama = serializers.CharField(source="dibuat_oleh.username", read_only=True)
    satuan_nama = serializers.CharField(source="satuan.nama", read_only=True)
    harga = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal("0"))

    class Meta:
        model = HargaProduk
        fields = [
            "id",
            "satuan",
            "satuan_nama",
            "harga",
            "berlaku_mulai",
            "dibuat_oleh_nama",
            "dibuat_pada",
        ]
        read_only_fields = ["dibuat_pada"]


class ProdukSerializer(serializers.ModelSerializer):
    kategori_nama = serializers.CharField(source="kategori.nama", read_only=True)
    satuan = SatuanSerializer(many=True, read_only=True)
    stok_tersedia = serializers.IntegerField(read_only=True)
    stok_kedaluwarsa = serializers.IntegerField(read_only=True)
    kedaluwarsa_terdekat = serializers.DateField(read_only=True, allow_null=True)
    stok_teks = serializers.SerializerMethodField()
    status_stok = serializers.SerializerMethodField()
    punya_foto = serializers.SerializerMethodField()

    class Meta:
        model = Produk
        fields = [
            "id",
            "sku",
            "nama",
            "kategori",
            "kategori_nama",
            "ukuran_ml",
            "kemasan",
            "stok_minimum",
            "aktif",
            "punya_foto",
            "satuan",
            "stok_tersedia",
            "stok_kedaluwarsa",
            "kedaluwarsa_terdekat",
            "stok_teks",
            "status_stok",
        ]

    def get_stok_teks(self, obj: Produk) -> str:
        isi, nama = satuan_terbesar(list(obj.satuan.all()))
        return stok_teks(obj.stok_tersedia, isi, nama)

    def get_status_stok(self, obj: Produk) -> str:
        return status_stok(obj.stok_tersedia, obj.stok_minimum)

    def get_punya_foto(self, obj: Produk) -> bool:
        return bool(obj.foto)


class ProdukBuatSerializer(serializers.ModelSerializer):
    harga_botol = serializers.DecimalField(
        max_digits=18, decimal_places=2, min_value=Decimal("0"), write_only=True
    )
    isi_dus = serializers.IntegerField(
        min_value=2, required=False, allow_null=True, write_only=True
    )
    harga_dus = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
        allow_null=True,
        write_only=True,
    )

    class Meta:
        model = Produk
        fields = [
            "id",
            "sku",
            "nama",
            "kategori",
            "ukuran_ml",
            "kemasan",
            "stok_minimum",
            "harga_botol",
            "isi_dus",
            "harga_dus",
        ]

    def validate(self, attrs):
        if bool(attrs.get("isi_dus")) != (attrs.get("harga_dus") is not None):
            raise serializers.ValidationError("Isi dus dan harga dus harus diisi bersamaan.")
        return attrs

    def create(self, validated_data):
        return buat_produk(self.context["request"].user, **validated_data)


class ProdukUbahSerializer(serializers.ModelSerializer):
    class Meta:
        model = Produk
        fields = ["id", "sku", "nama", "kategori", "ukuran_ml", "kemasan", "stok_minimum", "aktif"]


class FotoSerializer(serializers.Serializer):
    foto = serializers.ImageField()


class BerkasSerializer(serializers.Serializer):
    berkas = serializers.FileField()


class HasilImporSerializer(serializers.Serializer):
    dibuat = serializers.IntegerField()
    dilewati = serializers.IntegerField()
