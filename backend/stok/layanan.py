from datetime import date

from django.db import transaction
from django.utils import timezone

from inti.galat import AturanBisnisError
from inti.models import nomor_berikutnya
from produk.models import Produk, SatuanProduk

from .models import (
    BarangMasuk,
    BatchProduk,
    JenisMutasi,
    MutasiStok,
    StatusOpname,
    StokOpname,
    StokOpnameItem,
)


def ubah_stok(
    batch: BatchProduk,
    jumlah: int,
    jenis: str,
    pengguna,
    referensi: str = "",
    catatan: str = "",
) -> MutasiStok:
    """Satu-satunya jalan mengubah `sisa`. Baris batch harus sudah dikunci pemanggil."""
    batch.sisa += jumlah
    if batch.sisa < 0:
        raise AturanBisnisError(
            f"Stok batch {batch.nomor_batch} tidak boleh minus.", kode="stok_minus"
        )
    batch.save(update_fields=["sisa"])
    return MutasiStok.objects.create(
        batch=batch,
        jenis=jenis,
        jumlah=jumlah,
        sisa_sesudah=batch.sisa,
        referensi=referensi,
        catatan=catatan[:255],
        dibuat_oleh=pengguna,
    )


def kunci_batch(id_batch) -> dict[int, BatchProduk]:
    """Kunci selalu urut id supaya dua transaksi tidak saling menunggu (deadlock)."""
    baris = BatchProduk.objects.select_for_update().filter(id__in=id_batch).order_by("id")
    return {b.id: b for b in baris}


@transaction.atomic
def catat_barang_masuk(
    pengguna,
    *,
    produk: Produk,
    satuan: SatuanProduk,
    jumlah: int,
    nomor_batch: str,
    kedaluwarsa: date,
    tanggal: date,
    sumber: str = "",
    catatan: str = "",
) -> BarangMasuk:
    nomor = nomor_berikutnya(f"BM-{tanggal:%Y%m%d}", 3)
    masuk = BarangMasuk.objects.create(
        nomor=nomor,
        produk=produk,
        satuan=satuan,
        jumlah=jumlah,
        isi_botol=satuan.isi_botol,
        jumlah_botol=jumlah * satuan.isi_botol,
        tanggal=tanggal,
        sumber=sumber,
        catatan=catatan,
        dibuat_oleh=pengguna,
    )
    batch = BatchProduk.objects.create(
        produk=produk,
        barang_masuk=masuk,
        nomor_batch=nomor_batch,
        kedaluwarsa=kedaluwarsa,
        jumlah_awal=masuk.jumlah_botol,
        sisa=0,
    )
    ubah_stok(batch, masuk.jumlah_botol, JenisMutasi.MASUK, pengguna, nomor)
    return masuk


@transaction.atomic
def kurangi_stok(pengguna, *, batch_id: int, jenis: str, jumlah: int, catatan: str) -> BatchProduk:
    """Pengurangan barang rusak atau kedaluwarsa di gudang."""
    batch = kunci_batch([batch_id]).get(batch_id)
    if batch is None:
        raise AturanBisnisError("Batch tidak ditemukan.", kode="batch_tidak_ada")
    if jumlah > batch.sisa:
        raise AturanBisnisError(
            f"Sisa batch {batch.nomor_batch} hanya {batch.sisa} botol.", kode="stok_minus"
        )
    ubah_stok(batch, -jumlah, jenis, pengguna, catatan=catatan)
    return batch


@transaction.atomic
def buat_opname(pengguna, *, items: list[dict], catatan: str = "") -> StokOpname:
    id_batch = [i["batch"].id for i in items]
    batch = kunci_batch(id_batch)
    bentrok = (
        StokOpnameItem.objects.filter(batch_id__in=id_batch, opname__status=StatusOpname.MENUNGGU)
        .values_list("batch__nomor_batch", flat=True)
        .distinct()
    )
    if bentrok:
        raise AturanBisnisError(
            "Batch ini masih ada di opname yang menunggu persetujuan: " + ", ".join(bentrok),
            kode="opname_bentrok",
        )
    tanggal = timezone.localdate()
    opname = StokOpname.objects.create(
        nomor=nomor_berikutnya(f"OP-{tanggal:%Y%m%d}", 3), catatan=catatan, dibuat_oleh=pengguna
    )
    StokOpnameItem.objects.bulk_create(
        StokOpnameItem(
            opname=opname,
            batch=batch[i["batch"].id],
            stok_tercatat=batch[i["batch"].id].sisa,
            stok_fisik=i["stok_fisik"],
            selisih=i["stok_fisik"] - batch[i["batch"].id].sisa,
        )
        for i in items
    )
    return opname


def _ambil_opname_menunggu(opname_id: int) -> StokOpname:
    opname = StokOpname.objects.select_for_update().filter(pk=opname_id).first()
    if opname is None:
        raise AturanBisnisError("Opname tidak ditemukan.", kode="opname_tidak_ada")
    if opname.status != StatusOpname.MENUNGGU:
        raise AturanBisnisError("Opname ini sudah diputuskan.", kode="opname_selesai")
    return opname


@transaction.atomic
def setujui_opname(pengguna, opname_id: int) -> StokOpname:
    """Selisih saat dihitung yang diterapkan, jadi penjualan setelah hitung tetap terbawa."""
    opname = _ambil_opname_menunggu(opname_id)
    items = list(opname.items.all())
    batch = kunci_batch([i.batch_id for i in items])
    for item in items:
        if item.selisih:
            ubah_stok(
                batch[item.batch_id], item.selisih, JenisMutasi.OPNAME, pengguna, opname.nomor
            )
    opname.status = StatusOpname.DISETUJUI
    opname.diputuskan_oleh = pengguna
    opname.diputuskan_pada = timezone.now()
    opname.save()
    return opname


@transaction.atomic
def tolak_opname(pengguna, opname_id: int) -> StokOpname:
    opname = _ambil_opname_menunggu(opname_id)
    opname.status = StatusOpname.DITOLAK
    opname.diputuskan_oleh = pengguna
    opname.diputuskan_pada = timezone.now()
    opname.save()
    return opname
