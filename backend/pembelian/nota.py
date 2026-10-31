from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from inti.format import rupiah

from .models import Transaksi


def nota_pdf(transaksi: Transaksi) -> bytes:
    from weasyprint import HTML

    items = [
        {
            "nama": i.nama_produk,
            "jumlah": f"{i.jumlah} {i.nama_satuan}",
            "harga": rupiah(i.harga_satuan),
            "subtotal": rupiah(i.subtotal),
        }
        for i in transaksi.items.all()
    ]
    html = render_to_string(
        "pembelian/nota.html",
        {
            "perusahaan": settings.NAMA_PERUSAHAAN,
            "alamat": settings.ALAMAT_PERUSAHAAN,
            "t": transaksi,
            "tanggal": timezone.localtime(transaksi.tanggal),
            "items": items,
            "total": rupiah(transaksi.total),
            "retur": rupiah(transaksi.total_retur) if transaksi.total_retur else None,
            "terbayar": rupiah(transaksi.terbayar),
            "sisa": rupiah(transaksi.sisa_tagihan) if transaksi.sisa_tagihan > 0 else None,
        },
    )
    return HTML(string=html).write_pdf()
