from allauth.mfa.models import Authenticator
from auditlog.models import LogEntry
from django.db.models import Q
from django.http import JsonResponse
from django.utils.dateparse import parse_date
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from inti.izin import KELOLA_PENGGUNA

from .models import Pengguna, Peran
from .serializers import (
    AturPasswordSerializer,
    LogAktivitasSerializer,
    PenggunaBuatSerializer,
    PenggunaSerializer,
    PeranSerializer,
    SesiPenggunaSerializer,
    SesiSerializer,
)


def kesehatan(request):
    return JsonResponse({"status": "ok"})


@method_decorator(ensure_csrf_cookie, name="dispatch")
class SesiView(APIView):
    """Bagian dari alur login: memberi cookie CSRF dan status sesi saat ini."""

    permission_classes = [AllowAny]

    @extend_schema(responses=SesiSerializer)
    def get(self, request):
        pengguna = request.user
        if not pengguna.is_authenticated:
            return Response({"terautentikasi": False, "pengguna": None})
        return Response({"terautentikasi": True, "pengguna": SesiPenggunaSerializer(pengguna).data})


class PenggunaViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Pengguna.objects.select_related("peran").all()
    http_method_names = ["get", "post", "patch", "head", "options"]
    izin = KELOLA_PENGGUNA

    def get_serializer_class(self):
        return PenggunaBuatSerializer if self.action == "create" else PenggunaSerializer

    @extend_schema(request=AturPasswordSerializer, responses={204: None})
    @action(detail=True, methods=["post"], url_path="atur-password")
    def atur_password(self, request, pk=None):
        pengguna = self.get_object()
        serializer = AturPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pengguna.set_password(serializer.validated_data["password"])
        pengguna.save(update_fields=["password"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(request=None, responses={204: None})
    @action(detail=True, methods=["post"], url_path="reset-2fa")
    def reset_2fa(self, request, pk=None):
        """Untuk pengguna yang kehilangan perangkat autentikatornya."""
        Authenticator.objects.filter(user=self.get_object()).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PeranViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Peran.objects.all()
    serializer_class = PeranSerializer
    pagination_class = None
    izin = KELOLA_PENGGUNA


class LogAktivitasViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = LogAktivitasSerializer
    izin = KELOLA_PENGGUNA

    def get_queryset(self):
        qs = LogEntry.objects.select_related("actor", "content_type").order_by("-timestamp")
        param = self.request.query_params
        if q := param.get("q"):
            qs = qs.filter(
                Q(object_repr__icontains=q)
                | Q(actor__username__icontains=q)
                | Q(content_type__model__icontains=q)
            )
        if dari := parse_date(param.get("dari", "")):
            qs = qs.filter(timestamp__date__gte=dari)
        if sampai := parse_date(param.get("sampai", "")):
            qs = qs.filter(timestamp__date__lte=sampai)
        return qs
