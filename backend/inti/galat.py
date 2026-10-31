from typing import Any

from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.views import exception_handler


class AturanBisnisError(APIException):
    """Permintaan valid, tetapi ditolak oleh aturan pencatatan."""

    status_code = status.HTTP_409_CONFLICT
    default_code = "aturan_bisnis"
    default_detail = "Permintaan ditolak oleh aturan pencatatan."

    def __init__(self, pesan: str, kode: str = "aturan_bisnis", rincian: Any = None):
        super().__init__(detail=pesan, code=kode)
        self.kode = kode
        self.rincian = rincian


def penangan_galat(exc, context):
    respons = exception_handler(exc, context)
    if respons is None:
        return None
    if isinstance(exc, AturanBisnisError):
        respons.data = {"kode": exc.kode, "pesan": str(exc.detail), "rincian": exc.rincian}
    elif isinstance(exc, ValidationError):
        respons.data = {"kode": "validasi", "pesan": "Data belum benar.", "rincian": exc.detail}
    elif isinstance(exc, APIException):
        respons.data = {"kode": exc.get_codes(), "pesan": str(exc.detail), "rincian": None}
    else:
        respons.data = {"kode": "galat", "pesan": "Data tidak ditemukan.", "rincian": None}
    return respons
