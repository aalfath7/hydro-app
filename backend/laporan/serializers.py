from rest_framework import serializers


def uang(**opsi) -> serializers.DecimalField:
    return serializers.DecimalField(max_digits=18, decimal_places=2, **opsi)


class BarisPenjualanSerializer(serializers.Serializer):
    periode = serializers.DateField()
    jumlah_transaksi = serializers.IntegerField()
    bruto = uang()
    retur = uang()
    neto = uang()


class BarisTerlarisSerializer(serializers.Serializer):
    produk = serializers.IntegerField()
    sku = serializers.CharField()
    nama = serializers.CharField()
    botol_terjual = serializers.IntegerField()
    nilai = uang()


class BarisStokSerializer(serializers.Serializer):
    produk = serializers.IntegerField()
    sku = serializers.CharField()
    nama = serializers.CharField()
    stok_botol = serializers.IntegerField()
    stok_teks = serializers.CharField()
    stok_minimum = serializers.IntegerField()
    stok_kedaluwarsa = serializers.IntegerField()
    kedaluwarsa_terdekat = serializers.DateField(allow_null=True)
    status = serializers.CharField()


class BarisPiutangSerializer(serializers.Serializer):
    transaksi = serializers.IntegerField()
    nomor = serializers.CharField()
    pelanggan = serializers.CharField()
    tanggal = serializers.DateField()
    jatuh_tempo = serializers.DateField(allow_null=True)
    total = uang()
    retur = uang()
    terbayar = uang()
    sisa = uang()
    terlambat_hari = serializers.IntegerField()


class TrenSerializer(serializers.Serializer):
    tanggal = serializers.DateField()
    neto = uang()


class DasborProdukSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nama = serializers.CharField()
    stok_teks = serializers.CharField()


class DasborBatchSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    produk_nama = serializers.CharField()
    nomor_batch = serializers.CharField()
    kedaluwarsa = serializers.DateField()
    stok_teks = serializers.CharField()


class DasborSerializer(serializers.Serializer):
    stok_habis = serializers.IntegerField()
    stok_menipis = DasborProdukSerializer(many=True)
    hampir_kedaluwarsa = DasborBatchSerializer(many=True)
    jumlah_transaksi_hari_ini = serializers.IntegerField(allow_null=True)
    tagihan_jatuh_tempo = serializers.IntegerField(allow_null=True)
    penjualan_hari_ini = uang(allow_null=True)
    total_piutang = uang(allow_null=True)
    pembatalan_menunggu = serializers.IntegerField(allow_null=True)
    opname_menunggu = serializers.IntegerField(allow_null=True)
    tren = TrenSerializer(many=True, allow_null=True)
    terlaris = BarisTerlarisSerializer(many=True, allow_null=True)
