from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from .models import (
    ItemTransaksi,
    ItemTransaksiBatch,
    KondisiRetur,
    MetodeBayar,
    Pelanggan,
    Pembayaran,
    Retur,
    ReturItem,
    StatusTransaksi,
    Transaksi,
)


def status_bayar(t: Transaksi) -> str:
    if t.status == StatusTransaksi.DIBATALKAN:
        return "dibatalkan"
    if t.sisa_tagihan <= 0:
        return "lunas"
    if t.jatuh_tempo and t.jatuh_tempo < timezone.localdate():
        return "jatuh_tempo"
    return "tempo"


class PelangganSerializer(serializers.ModelSerializer):
    total_piutang = serializers.DecimalField(
        max_digits=18, decimal_places=2, read_only=True, default=Decimal("0")
    )

    class Meta:
        model = Pelanggan
        fields = ["id", "nama", "telepon", "alamat", "catatan", "aktif", "total_piutang"]


class AlokasiSerializer(serializers.ModelSerializer):
    nomor_batch = serializers.CharField(source="batch.nomor_batch", read_only=True)
    kedaluwarsa = serializers.DateField(source="batch.kedaluwarsa", read_only=True)

    class Meta:
        model = ItemTransaksiBatch
        fields = ["id", "nomor_batch", "kedaluwarsa", "jumlah_botol", "jumlah_diretur"]


class ItemSerializer(serializers.ModelSerializer):
    alokasi = AlokasiSerializer(many=True, read_only=True)

    class Meta:
        model = ItemTransaksi
        fields = [
            "id",
            "produk",
            "nama_produk",
            "nama_satuan",
            "isi_botol",
            "jumlah",
            "harga_satuan",
            "subtotal",
            "alokasi",
        ]


class PembayaranSerializer(serializers.ModelSerializer):
    jenis_label = serializers.CharField(source="get_jenis_display", read_only=True)
    metode_label = serializers.CharField(source="get_metode_display", read_only=True)
    dibuat_oleh_nama = serializers.CharField(source="dibuat_oleh.username", read_only=True)

    class Meta:
        model = Pembayaran
        fields = [
            "id",
            "jenis",
            "jenis_label",
            "metode",
            "metode_label",
            "jumlah",
            "referensi",
            "catatan",
            "dibuat_oleh_nama",
            "dibuat_pada",
        ]


class ReturItemSerializer(serializers.ModelSerializer):
    nama_produk = serializers.CharField(source="alokasi.item.nama_produk", read_only=True)
    nomor_batch = serializers.CharField(source="alokasi.batch.nomor_batch", read_only=True)

    class Meta:
        model = ReturItem
        fields = ["id", "nama_produk", "nomor_batch", "jumlah_botol", "kondisi", "nilai"]


class ReturSerializer(serializers.ModelSerializer):
    items = ReturItemSerializer(many=True, read_only=True)
    transaksi_nomor = serializers.CharField(source="transaksi.nomor", read_only=True)
    pelanggan_nama = serializers.CharField(source="transaksi.pelanggan.nama", read_only=True)
    dibuat_oleh_nama = serializers.CharField(source="dibuat_oleh.username", read_only=True)

    class Meta:
        model = Retur
        fields = [
            "id",
            "nomor",
            "transaksi",
            "transaksi_nomor",
            "pelanggan_nama",
            "tanggal",
            "alasan",
            "total",
            "potong_piutang",
            "pengembalian_uang",
            "dibuat_oleh_nama",
            "items",
        ]


class TransaksiSerializer(serializers.ModelSerializer):
    pelanggan_nama = serializers.CharField(source="pelanggan.nama", read_only=True)
    dibuat_oleh_nama = serializers.CharField(source="dibuat_oleh.username", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    status_bayar = serializers.SerializerMethodField()
    sisa_tagihan = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)

    class Meta:
        model = Transaksi
        fields = [
            "id",
            "nomor",
            "pelanggan",
            "pelanggan_nama",
            "tanggal",
            "status",
            "status_label",
            "status_bayar",
            "tempo",
            "jatuh_tempo",
            "total",
            "total_retur",
            "terbayar",
            "sisa_tagihan",
            "dibuat_oleh_nama",
        ]

    def get_status_bayar(self, obj: Transaksi) -> str:
        return status_bayar(obj)


class TransaksiDetailSerializer(TransaksiSerializer):
    items = ItemSerializer(many=True, read_only=True)
    pembayaran = PembayaranSerializer(many=True, read_only=True)
    retur = ReturSerializer(many=True, read_only=True)
    pelanggan_telepon = serializers.CharField(source="pelanggan.telepon", read_only=True)

    class Meta(TransaksiSerializer.Meta):
        fields = [
            *TransaksiSerializer.Meta.fields,
            "pelanggan_telepon",
            "catatan",
            "alasan_batal",
            "alasan_tolak_batal",
            "dibatalkan_pada",
            "items",
            "pembayaran",
            "retur",
        ]


class ItemBuatSerializer(serializers.Serializer):
    satuan = serializers.IntegerField(min_value=1)
    jumlah = serializers.IntegerField(min_value=1, max_value=1_000_000)


class TransaksiBuatSerializer(serializers.Serializer):
    kunci_idempoten = serializers.UUIDField()
    pelanggan = serializers.PrimaryKeyRelatedField(queryset=Pelanggan.objects.filter(aktif=True))
    items = ItemBuatSerializer(many=True, allow_empty=False, max_length=100)  # type: ignore[call-arg]
    metode = serializers.ChoiceField(choices=MetodeBayar.choices)
    tempo = serializers.BooleanField(default=False)
    uang_muka = serializers.DecimalField(
        max_digits=18, decimal_places=2, min_value=Decimal("0"), default=Decimal("0")
    )
    jatuh_tempo = serializers.DateField(required=False, allow_null=True)
    referensi = serializers.CharField(max_length=80, required=False, allow_blank=True)
    catatan = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs["tempo"]:
            jatuh_tempo = attrs.get("jatuh_tempo")
            if jatuh_tempo is None:
                raise serializers.ValidationError({"jatuh_tempo": ["Jatuh tempo wajib diisi."]})
            if jatuh_tempo < timezone.localdate():
                raise serializers.ValidationError(
                    {"jatuh_tempo": ["Jatuh tempo tidak boleh sebelum hari ini."]}
                )
        elif attrs["uang_muka"]:
            raise serializers.ValidationError({"uang_muka": ["Uang muka hanya untuk tempo."]})
        return attrs


class PelunasanSerializer(serializers.Serializer):
    jumlah = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal("0.01"))
    metode = serializers.ChoiceField(choices=MetodeBayar.choices)
    referensi = serializers.CharField(max_length=80, required=False, allow_blank=True)


class AlasanSerializer(serializers.Serializer):
    alasan = serializers.CharField(max_length=255)


class SetujuiBatalSerializer(serializers.Serializer):
    metode_pengembalian = serializers.ChoiceField(
        choices=MetodeBayar.choices, default=MetodeBayar.TUNAI
    )


class ReturItemBuatSerializer(serializers.Serializer):
    alokasi = serializers.IntegerField(min_value=1)
    jumlah_botol = serializers.IntegerField(min_value=1, max_value=10_000_000)
    kondisi = serializers.ChoiceField(choices=KondisiRetur.choices)


class ReturBuatSerializer(serializers.Serializer):
    transaksi = serializers.PrimaryKeyRelatedField(queryset=Transaksi.objects.all())
    items = ReturItemBuatSerializer(many=True, allow_empty=False)
    alasan = serializers.CharField(max_length=255)
    metode_pengembalian = serializers.ChoiceField(
        choices=MetodeBayar.choices, default=MetodeBayar.TUNAI
    )
