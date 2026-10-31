from datetime import date
from decimal import Decimal
from io import BytesIO
from typing import Any

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Font

from inti.format import rupiah

Kolom = tuple[str, str, str]  # kunci, label, jenis: teks | angka | uang | tanggal


def _unduhan(isi: bytes, jenis: str, nama: str) -> HttpResponse:
    respons = HttpResponse(isi, content_type=jenis)
    respons["Content-Disposition"] = f'attachment; filename="{nama}"'
    return respons


def ke_xlsx(judul: str, kolom: list[Kolom], baris: list[dict[str, Any]], nama: str) -> HttpResponse:
    buku = Workbook()
    lembar = buku.active
    lembar.title = judul[:31]
    for i, (_, label, _jenis) in enumerate(kolom, start=1):
        lembar.cell(row=1, column=i, value=label).font = Font(bold=True)
    for r, data in enumerate(baris, start=2):
        for c, (kunci, _label, jenis) in enumerate(kolom, start=1):
            nilai = data.get(kunci)
            if isinstance(nilai, Decimal):
                nilai = float(nilai)
            sel = lembar.cell(row=r, column=c, value=nilai)
            if isinstance(nilai, str):
                # Teks dari pengguna tidak boleh terbaca sebagai rumus Excel.
                sel.data_type = "s"
            elif jenis == "uang":
                sel.number_format = "#,##0.00"
            elif jenis == "tanggal":
                sel.number_format = "dd/mm/yyyy"
    keluaran = BytesIO()
    buku.save(keluaran)
    return _unduhan(
        keluaran.getvalue(),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        f"{nama}.xlsx",
    )


def _tampil(nilai: Any, jenis: str) -> str:
    if nilai is None:
        return ""
    if jenis == "uang":
        return rupiah(nilai)
    if isinstance(nilai, date):
        return nilai.strftime("%d/%m/%Y")
    return str(nilai)


def ke_pdf(
    judul: str, periode: str, kolom: list[Kolom], baris: list[dict[str, Any]], nama: str
) -> HttpResponse:
    from weasyprint import HTML

    html = render_to_string(
        "laporan/tabel.html",
        {
            "perusahaan": settings.NAMA_PERUSAHAAN,
            "judul": judul,
            "periode": periode,
            "dicetak": timezone.localtime(),
            "kepala": [{"label": k[1], "angka": k[2] in ("uang", "angka")} for k in kolom],
            "baris": [
                [
                    {"teks": _tampil(d.get(k[0]), k[2]), "angka": k[2] in ("uang", "angka")}
                    for k in kolom
                ]
                for d in baris
            ],
        },
    )
    return _unduhan(HTML(string=html).write_pdf(), "application/pdf", f"{nama}.pdf")
