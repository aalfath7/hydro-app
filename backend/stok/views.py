from django.db.models import Prefetch, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from inti.izin import KELOLA_STOK, LIHAT_PRODUK, SETUJUI_OPNAME
from produk.models import SatuanProduk

from . import layanan
from .models import BarangMasuk, BatchProduk, MutasiStok, StokOpname
from .serializers import (
    BarangMasukBuatSerializer,
    BarangMasukSerializer,
    BatchSerializer,
    KurangiStokSerializer,
    MutasiSerializer,
    OpnameBuatSerializer,
    OpnameSerializer,
)


class BatchViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = BatchSerializer
    izin = {"list": LIHAT_PRODUK, "retrieve": LIHAT_PRODUK, "kurangi": KELOLA_STOK}

    def get_queryset(self):
        qs = BatchProduk.objects.select_related("produk").prefetch_related(
            Prefetch("produk__satuan", SatuanProduk.objects.all())
        )
        param = self.request.query_params
        if produk := param.get("produk"):
            qs = qs.filter(produk_id=produk) if produk.isdigit() else qs.none()
        if param.get("ada_sisa") == "1":
            qs = qs.filter(sisa__gt=0)
        if q := param.get("q"):
            qs = qs.filter(
                Q(nomor_batch__icontains=q)
                | Q(produk__nama__icontains=q)
                | Q(produk__sku__icontains=q)
            )
        if param.get("status") == "kedaluwarsa":
            qs = qs.filter(kedaluwarsa__lt=timezone.localdate())
        return qs

    @extend_schema(request=KurangiStokSerializer, responses=BatchSerializer)
    @action(detail=True, methods=["post"])
    def kurangi(self, request, pk=None):
        batch = self.get_object()
        serializer = KurangiStokSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        layanan.kurangi_stok(request.user, batch_id=batch.id, **serializer.validated_data)
        return Response(BatchSerializer(self.get_queryset().get(pk=batch.pk)).data)


class MutasiViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = MutasiSerializer
    izin = LIHAT_PRODUK

    def get_queryset(self):
        qs = MutasiStok.objects.select_related("batch__produk", "dibuat_oleh")
        param = self.request.query_params
        if produk := param.get("produk"):
            qs = qs.filter(batch__produk_id=produk) if produk.isdigit() else qs.none()
        if batch := param.get("batch"):
            qs = qs.filter(batch_id=batch) if batch.isdigit() else qs.none()
        if jenis := param.get("jenis"):
            qs = qs.filter(jenis=jenis)
        return qs


class BarangMasukViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = BarangMasukSerializer
    izin = {"list": KELOLA_STOK, "create": KELOLA_STOK}

    def get_queryset(self):
        return BarangMasuk.objects.select_related("produk", "satuan", "batch", "dibuat_oleh")

    @extend_schema(request=BarangMasukBuatSerializer, responses={201: BarangMasukSerializer})
    def create(self, request):
        serializer = BarangMasukBuatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        masuk = layanan.catat_barang_masuk(request.user, **serializer.validated_data)
        return Response(
            BarangMasukSerializer(self.get_queryset().get(pk=masuk.pk)).data,
            status=status.HTTP_201_CREATED,
        )


class OpnameViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = OpnameSerializer
    izin = {
        "list": KELOLA_STOK,
        "retrieve": KELOLA_STOK,
        "create": KELOLA_STOK,
        "setujui": SETUJUI_OPNAME,
        "tolak": SETUJUI_OPNAME,
    }

    def get_queryset(self):
        qs = StokOpname.objects.select_related("dibuat_oleh", "diputuskan_oleh").prefetch_related(
            "items__batch__produk"
        )
        if s := self.request.query_params.get("status"):
            qs = qs.filter(status=s)
        return qs

    def _balas(self, opname, kode=status.HTTP_200_OK):
        return Response(OpnameSerializer(self.get_queryset().get(pk=opname.pk)).data, status=kode)

    @extend_schema(request=OpnameBuatSerializer, responses={201: OpnameSerializer})
    def create(self, request):
        serializer = OpnameBuatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        opname = layanan.buat_opname(request.user, **serializer.validated_data)
        return self._balas(opname, status.HTTP_201_CREATED)

    @extend_schema(request=None, responses=OpnameSerializer)
    @action(detail=True, methods=["post"])
    def setujui(self, request, pk=None):
        return self._balas(layanan.setujui_opname(request.user, self.get_object().pk))

    @extend_schema(request=None, responses=OpnameSerializer)
    @action(detail=True, methods=["post"])
    def tolak(self, request, pk=None):
        return self._balas(layanan.tolak_opname(request.user, self.get_object().pk))
