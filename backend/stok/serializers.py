from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from inti.format import stok_teks
from produk.layanan import satuan_terbesar
from produk.models import Produk, SatuanProduk

from .models import BarangMasuk, BatchProduk, JenisMutasi, MutasiStok, StokOpname, StokOpnameItem


class BatchSerializer(serializers.ModelSerializer):
    produk_nama = serializers.CharField(source="produk.nama", read_only=True)
    sku = serializers.CharField(source="produk.sku", read_only=True)
    stok_teks = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = BatchProduk
        fields = [
            "id",
            "produk",
            "produk_nama",
            "sku",
            "nomor_batch",
            "kedaluwarsa",
            "jumlah_awal",
            "sisa",
            "stok_teks",
            "status",
        ]

    def get_stok_teks(self, obj: BatchProduk) -> str:
        isi, nama = satuan_terbesar(list(obj.produk.satuan.all()))
        return stok_teks(obj.sisa, isi, nama)

    def get_status(self, obj: BatchProduk) -> str:
        hari_ini = timezone.localdate()
        if obj.kedaluwarsa < hari_ini:
            return "kedaluwarsa"
        batas = hari_ini + timedelta(days=settings.HARI_HAMPIR_KEDALUWARSA)
        return "hampir" if obj.kedaluwarsa <= batas else "aman"


class KurangiStokSerializer(serializers.Serializer):
    jenis = serializers.ChoiceField(choices=[JenisMutasi.RUSAK, JenisMutasi.KEDALUWARSA])
    jumlah = serializers.IntegerField(min_value=1, max_value=10_000_000)
    catatan = serializers.CharField(max_length=255)


class MutasiSerializer(serializers.ModelSerializer):
    nomor_batch = serializers.CharField(source="batch.nomor_batch", read_only=True)
    produk_nama = serializers.CharField(source="batch.produk.nama", read_only=True)
    jenis_label = serializers.CharField(source="get_jenis_display", read_only=True)
    dibuat_oleh_nama = serializers.CharField(source="dibuat_oleh.username", read_only=True)

    class Meta:
        model = MutasiStok
        fields = [
            "id",
            "batch",
            "nomor_batch",
            "produk_nama",
            "jenis",
            "jenis_label",
            "jumlah",
            "sisa_sesudah",
            "referensi",
            "catatan",
            "dibuat_oleh_nama",
            "dibuat_pada",
        ]


class BarangMasukSerializer(serializers.ModelSerializer):
    produk_nama = serializers.CharField(source="produk.nama", read_only=True)
    satuan_nama = serializers.CharField(source="satuan.nama", read_only=True)
    nomor_batch = serializers.CharField(source="batch.nomor_batch", read_only=True)
    kedaluwarsa = serializers.DateField(source="batch.kedaluwarsa", read_only=True)
    dibuat_oleh_nama = serializers.CharField(source="dibuat_oleh.username", read_only=True)

    class Meta:
        model = BarangMasuk
        fields = [
            "id",
            "nomor",
            "produk",
            "produk_nama",
            "satuan_nama",
            "jumlah",
            "jumlah_botol",
            "tanggal",
            "sumber",
            "catatan",
            "nomor_batch",
            "kedaluwarsa",
            "dibuat_oleh_nama",
            "dibuat_pada",
        ]


class BarangMasukBuatSerializer(serializers.Serializer):
    produk = serializers.PrimaryKeyRelatedField(queryset=Produk.objects.filter(aktif=True))
    satuan = serializers.PrimaryKeyRelatedField(queryset=SatuanProduk.objects.filter(aktif=True))
    jumlah = serializers.IntegerField(min_value=1, max_value=10_000_000)
    nomor_batch = serializers.CharField(max_length=60)
    kedaluwarsa = serializers.DateField()
    tanggal = serializers.DateField(required=False)
    sumber = serializers.CharField(max_length=160, required=False, allow_blank=True)
    catatan = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        attrs.setdefault("tanggal", timezone.localdate())
        if attrs["satuan"].produk_id != attrs["produk"].id:
            raise serializers.ValidationError({"satuan": ["Satuan bukan milik produk ini."]})
        if attrs["kedaluwarsa"] <= attrs["tanggal"]:
            raise serializers.ValidationError(
                {"kedaluwarsa": ["Tanggal kedaluwarsa harus setelah tanggal masuk."]}
            )
        if attrs["produk"].batch.filter(nomor_batch=attrs["nomor_batch"]).exists():
            raise serializers.ValidationError(
                {"nomor_batch": ["Nomor batch sudah dipakai untuk produk ini."]}
            )
        return attrs


class OpnameItemSerializer(serializers.ModelSerializer):
    nomor_batch = serializers.CharField(source="batch.nomor_batch", read_only=True)
    produk_nama = serializers.CharField(source="batch.produk.nama", read_only=True)
    kedaluwarsa = serializers.DateField(source="batch.kedaluwarsa", read_only=True)

    class Meta:
        model = StokOpnameItem
        fields = [
            "id",
            "batch",
            "nomor_batch",
            "produk_nama",
            "kedaluwarsa",
            "stok_tercatat",
            "stok_fisik",
            "selisih",
        ]


class OpnameSerializer(serializers.ModelSerializer):
    items = OpnameItemSerializer(many=True, read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    dibuat_oleh_nama = serializers.CharField(source="dibuat_oleh.username", read_only=True)
    diputuskan_oleh_nama = serializers.CharField(
        source="diputuskan_oleh.username", read_only=True, allow_null=True
    )

    class Meta:
        model = StokOpname
        fields = [
            "id",
            "nomor",
            "status",
            "status_label",
            "catatan",
            "items",
            "dibuat_oleh_nama",
            "dibuat_pada",
            "diputuskan_oleh_nama",
            "diputuskan_pada",
        ]
        read_only_fields = fields


class OpnameItemBuatSerializer(serializers.Serializer):
    batch = serializers.PrimaryKeyRelatedField(queryset=BatchProduk.objects.all())
    stok_fisik = serializers.IntegerField(min_value=0, max_value=10_000_000)


class OpnameBuatSerializer(serializers.Serializer):
    items = OpnameItemBuatSerializer(many=True, allow_empty=False)
    catatan = serializers.CharField(required=False, allow_blank=True)

    def validate_items(self, items):
        id_batch = [i["batch"].id for i in items]
        if len(id_batch) != len(set(id_batch)):
            raise serializers.ValidationError("Batch tidak boleh ganda.")
        return items
