from decimal import Decimal

from django.db.models import DecimalField, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from inti.izin import KELOLA_TRANSAKSI, SETUJUI_PEMBATALAN

from . import layanan
from .models import Pelanggan, Retur, StatusTransaksi, Transaksi
from .nota import nota_pdf
from .serializers import (
    AlasanSerializer,
    PelangganSerializer,
    PelunasanSerializer,
    ReturBuatSerializer,
    ReturSerializer,
    SetujuiBatalSerializer,
    TransaksiBuatSerializer,
    TransaksiDetailSerializer,
    TransaksiSerializer,
)


class PelangganViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = PelangganSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]
    izin = KELOLA_TRANSAKSI

    def get_queryset(self):
        piutang = (
            Transaksi.objects.filter(pelanggan=OuterRef("pk"), sisa_tagihan__gt=0)
            .exclude(status=StatusTransaksi.DIBATALKAN)
            .order_by()
            .values("pelanggan")
            .annotate(t=Sum("sisa_tagihan"))
            .values("t")
        )
        qs = Pelanggan.objects.annotate(
            total_piutang=Coalesce(
                Subquery(piutang, output_field=DecimalField(max_digits=18, decimal_places=2)),
                Decimal("0"),
                output_field=DecimalField(max_digits=18, decimal_places=2),
            )
        )
        param = self.request.query_params
        if q := param.get("q"):
            qs = qs.filter(Q(nama__icontains=q) | Q(telepon__icontains=q))
        if param.get("aktif") == "1":
            qs = qs.filter(aktif=True)
        return qs


class TransaksiViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    izin = {
        "list": KELOLA_TRANSAKSI,
        "retrieve": KELOLA_TRANSAKSI,
        "create": KELOLA_TRANSAKSI,
        "bayar": KELOLA_TRANSAKSI,
        "nota": KELOLA_TRANSAKSI,
        "ajukan_batal": KELOLA_TRANSAKSI,
        "setujui_batal": SETUJUI_PEMBATALAN,
        "tolak_batal": SETUJUI_PEMBATALAN,
    }

    def get_serializer_class(self):
        return TransaksiSerializer if self.action == "list" else TransaksiDetailSerializer

    def get_queryset(self):
        qs = Transaksi.objects.select_related("pelanggan", "dibuat_oleh")
        if self.action != "list":
            qs = qs.prefetch_related(
                "items__alokasi__batch",
                "pembayaran__dibuat_oleh",
                "retur__items__alokasi__item",
                "retur__items__alokasi__batch",
                "retur__dibuat_oleh",
            )
            return qs

        param = self.request.query_params
        if q := param.get("q"):
            qs = qs.filter(Q(nomor__icontains=q) | Q(pelanggan__nama__icontains=q))
        if pelanggan := param.get("pelanggan"):
            qs = qs.filter(pelanggan_id=pelanggan) if pelanggan.isdigit() else qs.none()
        if dari := parse_date(param.get("dari", "")):
            qs = qs.filter(tanggal__date__gte=dari)
        if sampai := parse_date(param.get("sampai", "")):
            qs = qs.filter(tanggal__date__lte=sampai)
        if s := param.get("status"):
            qs = qs.filter(status=s)
        bayar = param.get("status_bayar")
        aktif = qs.exclude(status=StatusTransaksi.DIBATALKAN)
        if bayar == "lunas":
            qs = aktif.filter(sisa_tagihan__lte=0)
        elif bayar == "belum_lunas":
            qs = aktif.filter(sisa_tagihan__gt=0)
        elif bayar == "jatuh_tempo":
            qs = aktif.filter(sisa_tagihan__gt=0, jatuh_tempo__lt=timezone.localdate())
        return qs

    def _balas(self, transaksi, kode=status.HTTP_200_OK):
        self.action = "retrieve"
        data = TransaksiDetailSerializer(self.get_queryset().get(pk=transaksi.pk)).data
        return Response(data, status=kode)

    @extend_schema(request=TransaksiBuatSerializer, responses={201: TransaksiDetailSerializer})
    def create(self, request):
        serializer = TransaksiBuatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        transaksi = layanan.buat_transaksi(request.user, **serializer.validated_data)
        return self._balas(transaksi, status.HTTP_201_CREATED)

    @extend_schema(request=PelunasanSerializer, responses=TransaksiDetailSerializer)
    @action(detail=True, methods=["post"])
    def bayar(self, request, pk=None):
        transaksi = self.get_object()
        serializer = PelunasanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._balas(
            layanan.catat_pelunasan(request.user, transaksi.pk, **serializer.validated_data)
        )

    @extend_schema(request=AlasanSerializer, responses=TransaksiDetailSerializer)
    @action(detail=True, methods=["post"], url_path="ajukan-batal")
    def ajukan_batal(self, request, pk=None):
        transaksi = self.get_object()
        serializer = AlasanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._balas(
            layanan.ajukan_pembatalan(
                request.user, transaksi.pk, serializer.validated_data["alasan"]
            )
        )

    @extend_schema(request=SetujuiBatalSerializer, responses=TransaksiDetailSerializer)
    @action(detail=True, methods=["post"], url_path="setujui-batal")
    def setujui_batal(self, request, pk=None):
        transaksi = self.get_object()
        serializer = SetujuiBatalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._balas(
            layanan.setujui_pembatalan(
                request.user, transaksi.pk, serializer.validated_data["metode_pengembalian"]
            )
        )

    @extend_schema(request=AlasanSerializer, responses=TransaksiDetailSerializer)
    @action(detail=True, methods=["post"], url_path="tolak-batal")
    def tolak_batal(self, request, pk=None):
        transaksi = self.get_object()
        serializer = AlasanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._balas(
            layanan.tolak_pembatalan(
                request.user, transaksi.pk, serializer.validated_data["alasan"]
            )
        )

    @extend_schema(responses={(200, "application/pdf"): OpenApiTypes.BINARY})
    @action(detail=True, methods=["get"])
    def nota(self, request, pk=None):
        transaksi = self.get_object()
        respons = HttpResponse(nota_pdf(transaksi), content_type="application/pdf")
        respons["Content-Disposition"] = f'inline; filename="{transaksi.nomor}.pdf"'
        return respons


class ReturViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = ReturSerializer
    izin = KELOLA_TRANSAKSI

    def get_queryset(self):
        qs = Retur.objects.select_related("transaksi__pelanggan", "dibuat_oleh").prefetch_related(
            "items__alokasi__item", "items__alokasi__batch"
        )
        if q := self.request.query_params.get("q"):
            qs = qs.filter(
                Q(nomor__icontains=q)
                | Q(transaksi__nomor__icontains=q)
                | Q(transaksi__pelanggan__nama__icontains=q)
            )
        return qs

    @extend_schema(request=ReturBuatSerializer, responses={201: ReturSerializer})
    def create(self, request):
        serializer = ReturBuatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        retur = layanan.buat_retur(
            request.user,
            transaksi_id=data["transaksi"].pk,
            items=data["items"],
            alasan=data["alasan"],
            metode_pengembalian=data["metode_pengembalian"],
        )
        return Response(
            ReturSerializer(self.get_queryset().get(pk=retur.pk)).data,
            status=status.HTTP_201_CREATED,
        )
