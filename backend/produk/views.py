from django.conf import settings
from django.db.models import F, Prefetch, Q
from django.http import FileResponse, Http404, HttpResponse
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from inti.izin import LIHAT_PRODUK, UBAH_PRODUK

from . import impor
from .layanan import dengan_stok
from .models import HargaProduk, Kategori, Produk, SatuanProduk
from .serializers import (
    BerkasSerializer,
    FotoSerializer,
    HargaSerializer,
    HasilImporSerializer,
    KategoriSerializer,
    ProdukBuatSerializer,
    ProdukSerializer,
    ProdukUbahSerializer,
    SatuanBuatSerializer,
    SatuanUbahSerializer,
)

FORMAT_FOTO = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


class KategoriViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Kategori.objects.all()
    serializer_class = KategoriSerializer
    pagination_class = None
    http_method_names = ["get", "post", "patch", "head", "options"]
    izin = {"list": LIHAT_PRODUK, "create": UBAH_PRODUK, "partial_update": UBAH_PRODUK}


class ProdukViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Tidak ada hapus: produk lama dinonaktifkan supaya riwayat transaksi tetap utuh."""

    http_method_names = ["get", "post", "patch", "head", "options"]
    izin = {
        "list": LIHAT_PRODUK,
        "retrieve": LIHAT_PRODUK,
        "foto": LIHAT_PRODUK,
        "create": UBAH_PRODUK,
        "partial_update": UBAH_PRODUK,
        "unggah_foto": UBAH_PRODUK,
        "impor": UBAH_PRODUK,
        "template_impor": UBAH_PRODUK,
    }

    def get_queryset(self):
        hari_ini = timezone.localdate()
        qs = dengan_stok(
            Produk.objects.select_related("kategori").prefetch_related(
                Prefetch("satuan", SatuanProduk.objects.dengan_harga(hari_ini))
            )
        )
        param = self.request.query_params
        if q := param.get("q"):
            qs = qs.filter(Q(nama__icontains=q) | Q(sku__icontains=q))
        if kategori := param.get("kategori"):
            qs = qs.filter(kategori_id=kategori) if kategori.isdigit() else qs.none()
        if param.get("aktif") == "1":
            qs = qs.filter(aktif=True)
        status_filter = param.get("status")
        if status_filter == "habis":
            qs = qs.filter(stok_tersedia__lte=0)
        elif status_filter == "menipis":
            qs = qs.filter(stok_tersedia__gt=0, stok_tersedia__lte=F("stok_minimum"))
        elif status_filter == "aman":
            qs = qs.filter(stok_tersedia__gt=F("stok_minimum"))
        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return ProdukBuatSerializer
        if self.action == "partial_update":
            return ProdukUbahSerializer
        return ProdukSerializer

    @extend_schema(responses={(200, "image/*"): OpenApiTypes.BINARY})
    @action(detail=True, methods=["get"], url_path="foto")
    def foto(self, request, pk=None):
        produk = self.get_object()
        if not produk.foto:
            raise Http404
        return FileResponse(produk.foto.open("rb"))

    @extend_schema(request={"multipart/form-data": FotoSerializer}, responses={204: None})
    @foto.mapping.post
    def unggah_foto(self, request, pk=None):
        produk = self.get_object()
        serializer = FotoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        berkas = serializer.validated_data["foto"]
        if berkas.size > settings.FOTO_MAKS_BYTE:
            raise ValidationError({"foto": ["Ukuran foto maksimal 2 MB."]})
        ekstensi = FORMAT_FOTO.get(berkas.image.format)
        if ekstensi is None:
            raise ValidationError({"foto": ["Gunakan foto JPG, PNG, atau WebP."]})
        # Ekstensi mengikuti isi file, bukan nama kiriman, supaya tidak dilayani sebagai HTML.
        berkas.name = f"foto.{ekstensi}"
        if produk.foto:
            produk.foto.delete(save=False)
        produk.foto = berkas
        produk.save(update_fields=["foto", "diubah_pada"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        request={"multipart/form-data": BerkasSerializer},
        responses={200: HasilImporSerializer},
    )
    @action(detail=False, methods=["post"], url_path="impor")
    def impor(self, request):
        serializer = BerkasSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        berkas = serializer.validated_data["berkas"]
        if berkas.size > settings.IMPOR_MAKS_BYTE:
            raise ValidationError({"berkas": ["Ukuran berkas maksimal 5 MB."]})
        try:
            baris, galat = impor.baca_baris(berkas)
        except Exception as exc:
            raise ValidationError({"berkas": ["Berkas bukan Excel yang valid."]}) from exc
        if galat:
            raise ValidationError({"berkas": galat})
        return Response(impor.simpan_baris(request.user, baris))

    @extend_schema(responses={(200, "application/octet-stream"): OpenApiTypes.BINARY})
    @action(detail=False, methods=["get"], url_path="template-impor")
    def template_impor(self, request):
        respons = HttpResponse(
            impor.buat_template(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        respons["Content-Disposition"] = 'attachment; filename="template-produk.xlsx"'
        return respons


class SatuanViewSet(mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    queryset = SatuanProduk.objects.all()
    http_method_names = ["post", "patch", "head", "options"]
    izin = {"create": UBAH_PRODUK, "partial_update": UBAH_PRODUK}

    def get_serializer_class(self):
        return SatuanBuatSerializer if self.action == "create" else SatuanUbahSerializer


class HargaViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = HargaSerializer
    izin = {"list": LIHAT_PRODUK, "create": UBAH_PRODUK}

    def get_queryset(self):
        qs = HargaProduk.objects.select_related("satuan", "dibuat_oleh")
        produk = self.request.query_params.get("produk")
        if produk:
            qs = qs.filter(satuan__produk_id=produk) if produk.isdigit() else qs.none()
        return qs

    def perform_create(self, serializer):
        serializer.save(dibuat_oleh=self.request.user)
