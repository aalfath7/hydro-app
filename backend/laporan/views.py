from datetime import date, timedelta
from typing import Any

from django.db.models import Sum
from django.utils import timezone
from django.utils.dateparse import parse_date
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from inti.format import stok_teks
from inti.izin import KELOLA_TRANSAKSI, LIHAT_LAPORAN, LIHAT_PRODUK, SETUJUI_OPNAME
from pembelian.models import StatusTransaksi, Transaksi
from produk.layanan import dengan_stok, satuan_terbesar, status_stok
from produk.models import Produk
from stok.models import StatusOpname, StokOpname

from . import data, ekspor
from .serializers import (
    BarisPenjualanSerializer,
    BarisPiutangSerializer,
    BarisStokSerializer,
    BarisTerlarisSerializer,
    DasborSerializer,
)

PARAM_PERIODE = [
    OpenApiParameter("dari", OpenApiTypes.DATE),
    OpenApiParameter("sampai", OpenApiTypes.DATE),
]
PARAM_EKSPOR = OpenApiParameter("ekspor", str, enum=["xlsx", "pdf"])


def ambil_periode(request) -> tuple[date, date]:
    hari_ini = timezone.localdate()
    dari = parse_date(request.query_params.get("dari", "")) or hari_ini.replace(day=1)
    sampai = parse_date(request.query_params.get("sampai", "")) or hari_ini
    if dari > sampai:
        raise ValidationError({"dari": ["Tanggal awal setelah tanggal akhir."]})
    return dari, sampai


class LaporanView(APIView):
    izin = LIHAT_LAPORAN
    judul = ""
    nama_file = ""
    kolom: list[ekspor.Kolom] = []

    def ambil_baris(self, request) -> tuple[list[dict[str, Any]], str]:
        raise NotImplementedError

    def get(self, request):
        baris, periode = self.ambil_baris(request)
        format_ekspor = request.query_params.get("ekspor")
        if format_ekspor == "xlsx":
            return ekspor.ke_xlsx(self.judul, self.kolom, baris, self.nama_file)
        if format_ekspor == "pdf":
            return ekspor.ke_pdf(self.judul, periode, self.kolom, baris, self.nama_file)
        return Response(self.serializer_class(baris, many=True).data)


def teks_periode(dari: date, sampai: date) -> str:
    return f"{dari:%d/%m/%Y} s.d. {sampai:%d/%m/%Y}"


class LaporanPenjualanView(LaporanView):
    serializer_class = BarisPenjualanSerializer
    judul = "Laporan penjualan"
    nama_file = "laporan-penjualan"
    kolom = [
        ("periode", "Periode", "tanggal"),
        ("jumlah_transaksi", "Transaksi", "angka"),
        ("bruto", "Penjualan", "uang"),
        ("retur", "Retur", "uang"),
        ("neto", "Neto", "uang"),
    ]

    def ambil_baris(self, request):
        dari, sampai = ambil_periode(request)
        per = "bulan" if request.query_params.get("per") == "bulan" else "hari"
        return data.penjualan(dari, sampai, per), teks_periode(dari, sampai)

    @extend_schema(
        parameters=[
            *PARAM_PERIODE,
            PARAM_EKSPOR,
            OpenApiParameter("per", str, enum=["hari", "bulan"]),
        ],
        responses=BarisPenjualanSerializer(many=True),
    )
    def get(self, request):
        return super().get(request)


class LaporanTerlarisView(LaporanView):
    serializer_class = BarisTerlarisSerializer
    judul = "Produk terlaris"
    nama_file = "produk-terlaris"
    kolom = [
        ("sku", "SKU", "teks"),
        ("nama", "Produk", "teks"),
        ("botol_terjual", "Botol terjual", "angka"),
        ("nilai", "Nilai", "uang"),
    ]

    def ambil_baris(self, request):
        dari, sampai = ambil_periode(request)
        return data.produk_terlaris(dari, sampai), teks_periode(dari, sampai)

    @extend_schema(
        parameters=[*PARAM_PERIODE, PARAM_EKSPOR], responses=BarisTerlarisSerializer(many=True)
    )
    def get(self, request):
        return super().get(request)


class LaporanStokView(LaporanView):
    serializer_class = BarisStokSerializer
    judul = "Laporan stok"
    nama_file = "laporan-stok"
    kolom = [
        ("sku", "SKU", "teks"),
        ("nama", "Produk", "teks"),
        ("stok_teks", "Stok", "teks"),
        ("stok_botol", "Stok (botol)", "angka"),
        ("stok_minimum", "Minimum", "angka"),
        ("stok_kedaluwarsa", "Kedaluwarsa (botol)", "angka"),
        ("kedaluwarsa_terdekat", "Kedaluwarsa terdekat", "tanggal"),
        ("status", "Status", "teks"),
    ]

    def ambil_baris(self, request):
        return data.stok(), ""

    @extend_schema(parameters=[PARAM_EKSPOR], responses=BarisStokSerializer(many=True))
    def get(self, request):
        return super().get(request)


class LaporanPiutangView(LaporanView):
    serializer_class = BarisPiutangSerializer
    judul = "Laporan piutang"
    nama_file = "laporan-piutang"
    kolom = [
        ("nomor", "Nota", "teks"),
        ("pelanggan", "Pelanggan", "teks"),
        ("tanggal", "Tanggal", "tanggal"),
        ("jatuh_tempo", "Jatuh tempo", "tanggal"),
        ("total", "Total", "uang"),
        ("retur", "Retur", "uang"),
        ("terbayar", "Terbayar", "uang"),
        ("sisa", "Sisa", "uang"),
        ("terlambat_hari", "Terlambat (hari)", "angka"),
    ]

    def ambil_baris(self, request):
        return data.piutang(), ""

    @extend_schema(parameters=[PARAM_EKSPOR], responses=BarisPiutangSerializer(many=True))
    def get(self, request):
        return super().get(request)


class DasborView(APIView):
    """Isi mengikuti izin: angka keuangan hanya untuk peran yang boleh melihat laporan."""

    izin = LIHAT_PRODUK

    @extend_schema(responses=DasborSerializer)
    def get(self, request):
        izin = request.user.izin
        hari_ini = timezone.localdate()

        produk = dengan_stok(Produk.objects.filter(aktif=True).prefetch_related("satuan"))
        rendah = [p for p in produk if status_stok(p.stok_tersedia, p.stok_minimum) != "aman"]

        def teks(p: Produk, botol: int) -> str:
            isi, nama = satuan_terbesar(list(p.satuan.all()))
            return stok_teks(botol, isi, nama)

        hasil: dict[str, Any] = {
            "stok_habis": sum(1 for p in rendah if p.stok_tersedia <= 0),
            "stok_menipis": [
                {"id": p.id, "nama": p.nama, "stok_teks": teks(p, p.stok_tersedia)}
                for p in sorted(rendah, key=lambda p: p.stok_tersedia)[:10]
            ],
            "hampir_kedaluwarsa": [
                {
                    "id": b.id,
                    "produk_nama": b.produk.nama,
                    "nomor_batch": b.nomor_batch,
                    "kedaluwarsa": b.kedaluwarsa,
                    "stok_teks": teks(b.produk, b.sisa),
                }
                for b in data.batch_hampir_kedaluwarsa()
            ],
            "jumlah_transaksi_hari_ini": None,
            "tagihan_jatuh_tempo": None,
            "penjualan_hari_ini": None,
            "total_piutang": None,
            "pembatalan_menunggu": None,
            "opname_menunggu": None,
            "tren": None,
            "terlaris": None,
        }
        sah = Transaksi.objects.exclude(status=StatusTransaksi.DIBATALKAN)
        if KELOLA_TRANSAKSI in izin:
            hasil["jumlah_transaksi_hari_ini"] = sah.filter(tanggal__date=hari_ini).count()
            hasil["tagihan_jatuh_tempo"] = sah.filter(
                sisa_tagihan__gt=0, jatuh_tempo__lte=hari_ini
            ).count()
        if LIHAT_LAPORAN in izin:
            bulan_lalu = hari_ini - timedelta(days=30)
            baris = data.penjualan(hari_ini, hari_ini)
            hasil["penjualan_hari_ini"] = baris[0]["neto"] if baris else 0
            hasil["total_piutang"] = (
                sah.filter(sisa_tagihan__gt=0).aggregate(t=Sum("sisa_tagihan"))["t"] or 0
            )
            hasil["pembatalan_menunggu"] = sah.filter(status=StatusTransaksi.MENUNGGU_BATAL).count()
            hasil["tren"] = data.tren_penjualan()
            hasil["terlaris"] = data.produk_terlaris(bulan_lalu, hari_ini, batas=5)
        if SETUJUI_OPNAME in izin:
            hasil["opname_menunggu"] = StokOpname.objects.filter(
                status=StatusOpname.MENUNGGU
            ).count()
        return Response(DasborSerializer(hasil).data)
