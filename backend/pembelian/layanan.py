import uuid
from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from inti.format import bulatkan
from inti.galat import AturanBisnisError
from inti.models import nomor_berikutnya
from produk.models import SatuanProduk
from stok.layanan import kunci_batch, ubah_stok
from stok.models import BatchProduk, JenisMutasi

from .models import (
    ItemTransaksi,
    ItemTransaksiBatch,
    JenisPembayaran,
    KondisiRetur,
    MetodeBayar,
    Pelanggan,
    Pembayaran,
    Retur,
    ReturItem,
    StatusTransaksi,
    Transaksi,
)


def buat_transaksi(pengguna, *, kunci_idempoten: uuid.UUID, **data) -> Transaksi:
    """Nota, stok keluar, dan pembayaran tersimpan bersama atau tidak sama sekali.

    Klik ganda atau kirim ulang dengan kunci yang sama mengembalikan nota yang sudah ada.
    """
    ada = Transaksi.objects.filter(kunci_idempoten=kunci_idempoten).first()
    if ada:
        return ada
    try:
        with transaction.atomic():
            return _buat_transaksi(pengguna, kunci_idempoten=kunci_idempoten, **data)
    except IntegrityError:
        ada = Transaksi.objects.filter(kunci_idempoten=kunci_idempoten).first()
        if ada:
            return ada
        raise


def _ambil_satuan(items: list[dict]) -> dict[int, SatuanProduk]:
    hari_ini = timezone.localdate()
    satuan = {
        s.id: s
        for s in SatuanProduk.objects.dengan_harga(hari_ini)
        .select_related("produk")
        .filter(id__in=[i["satuan"] for i in items])
    }
    for item in items:
        s = satuan.get(item["satuan"])
        if s is None or not s.aktif or not s.produk.aktif:
            raise AturanBisnisError("Produk atau satuan sudah tidak aktif.", kode="produk_nonaktif")
        if s.harga is None:
            raise AturanBisnisError(
                f"Harga {s.produk.nama} per {s.nama} belum ada.", kode="harga_belum_ada"
            )
    return satuan


def _kunci_batch_fefo(id_produk: set[int]) -> dict[int, list[BatchProduk]]:
    terkunci = list(
        BatchProduk.objects.select_for_update()
        .layak_jual()
        .filter(produk_id__in=id_produk)
        .order_by("id")
    )
    per_produk: dict[int, list[BatchProduk]] = defaultdict(list)
    for batch in sorted(terkunci, key=lambda b: (b.kedaluwarsa, b.id)):
        per_produk[batch.produk_id].append(batch)
    return per_produk


def _buat_transaksi(
    pengguna,
    *,
    kunci_idempoten: uuid.UUID,
    pelanggan: Pelanggan,
    items: list[dict],
    metode: str,
    tempo: bool = False,
    uang_muka: Decimal = Decimal("0"),
    jatuh_tempo: date | None = None,
    referensi: str = "",
    catatan: str = "",
) -> Transaksi:
    satuan = _ambil_satuan(items)

    kebutuhan: dict[int, int] = defaultdict(int)
    for data in items:
        s = satuan[data["satuan"]]
        kebutuhan[s.produk_id] += data["jumlah"] * s.isi_botol

    batch_produk = _kunci_batch_fefo(set(kebutuhan))
    kurang = []
    for produk_id, diminta in kebutuhan.items():
        tersedia = sum(b.sisa for b in batch_produk[produk_id])
        if tersedia < diminta:
            nama = next(s.produk.nama for s in satuan.values() if s.produk_id == produk_id)
            kurang.append(
                {"produk": produk_id, "nama": nama, "diminta": diminta, "tersedia": tersedia}
            )
    if kurang:
        raise AturanBisnisError("Stok tidak cukup.", kode="stok_tidak_cukup", rincian=kurang)

    total = sum((satuan[i["satuan"]].harga * i["jumlah"] for i in items), Decimal("0"))
    if tempo and uang_muka >= total:
        raise AturanBisnisError(
            "Uang muka sama dengan total, jadi transaksi ini bukan tempo.", kode="uang_muka_lebih"
        )

    tanggal = timezone.localdate()
    nomor = nomor_berikutnya(f"TRX-{tanggal:%Y%m%d}")
    terbayar = uang_muka if tempo else total
    transaksi_baru = Transaksi.objects.create(
        nomor=nomor,
        kunci_idempoten=kunci_idempoten,
        pelanggan=pelanggan,
        tempo=tempo,
        jatuh_tempo=jatuh_tempo if tempo else None,
        total=total,
        terbayar=terbayar,
        catatan=catatan,
        dibuat_oleh=pengguna,
    )

    for data in items:
        s = satuan[data["satuan"]]
        item = ItemTransaksi.objects.create(
            transaksi=transaksi_baru,
            produk=s.produk,
            satuan=s,
            nama_produk=s.produk.nama,
            nama_satuan=s.nama,
            isi_botol=s.isi_botol,
            jumlah=data["jumlah"],
            harga_satuan=s.harga,
            subtotal=s.harga * data["jumlah"],
        )
        perlu = item.total_botol
        for batch in batch_produk[s.produk_id]:
            if perlu == 0:
                break
            ambil = min(perlu, batch.sisa)
            if ambil == 0:
                continue
            ItemTransaksiBatch.objects.create(item=item, batch=batch, jumlah_botol=ambil)
            ubah_stok(batch, -ambil, JenisMutasi.PENJUALAN, pengguna, nomor)
            perlu -= ambil

    if terbayar > 0:
        Pembayaran.objects.create(
            transaksi=transaksi_baru,
            metode=metode,
            jumlah=terbayar,
            referensi=referensi,
            dibuat_oleh=pengguna,
        )
    return transaksi_baru


def _kunci_transaksi(transaksi_id: int) -> Transaksi:
    return Transaksi.objects.select_for_update().get(pk=transaksi_id)


def _wajib_selesai(transaksi_obj: Transaksi) -> None:
    if transaksi_obj.status != StatusTransaksi.SELESAI:
        raise AturanBisnisError(
            "Transaksi yang dibatalkan atau menunggu pembatalan tidak bisa diproses.",
            kode="status_transaksi",
        )


@transaction.atomic
def catat_pelunasan(
    pengguna, transaksi_id: int, *, jumlah: Decimal, metode: str, referensi: str = ""
) -> Transaksi:
    t = _kunci_transaksi(transaksi_id)
    _wajib_selesai(t)
    if jumlah > t.sisa:
        raise AturanBisnisError(f"Pembayaran melebihi sisa tagihan ({t.sisa}).", kode="bayar_lebih")
    Pembayaran.objects.create(
        transaksi=t, metode=metode, jumlah=jumlah, referensi=referensi, dibuat_oleh=pengguna
    )
    t.terbayar += jumlah
    t.save(update_fields=["terbayar"])
    return t


def _nilai_retur(item: ItemTransaksi, sebelum: int, jumlah: int) -> Decimal:
    """Selisih kumulatif, supaya retur penuh selalu sama persis dengan subtotal item."""
    total = item.total_botol

    def kumulatif(botol: int) -> Decimal:
        return bulatkan(item.subtotal * botol / total)

    return kumulatif(sebelum + jumlah) - kumulatif(sebelum)


@transaction.atomic
def buat_retur(
    pengguna,
    *,
    transaksi_id: int,
    items: list[dict],
    alasan: str,
    metode_pengembalian: str = MetodeBayar.TUNAI,
) -> Retur:
    t = _kunci_transaksi(transaksi_id)
    _wajib_selesai(t)

    semua_alokasi = {
        a.id: a
        for a in ItemTransaksiBatch.objects.select_for_update(of=("self",))
        .select_related("item")
        .filter(item__transaksi=t)
        .order_by("id")
    }
    diretur_item: dict[int, int] = defaultdict(int)
    for a in semua_alokasi.values():
        diretur_item[a.item_id] += a.jumlah_diretur

    for baris in items:
        if baris["alokasi"] not in semua_alokasi:
            raise AturanBisnisError("Barang ini bukan bagian dari nota.", kode="alokasi_salah")

    batch = kunci_batch({semua_alokasi[b["alokasi"]].batch_id for b in items})
    hari_ini = timezone.localdate()
    nomor = nomor_berikutnya(f"RTR-{hari_ini:%Y%m%d}", 3)

    total = Decimal("0")
    baris_retur = []
    for baris in items:
        alokasi = semua_alokasi[baris["alokasi"]]
        jumlah = baris["jumlah_botol"]
        kondisi = baris["kondisi"]
        b = batch[alokasi.batch_id]
        if alokasi.jumlah_diretur + jumlah > alokasi.jumlah_botol:
            raise AturanBisnisError(
                f"Retur batch {b.nomor_batch} melebihi jumlah yang dibeli.", kode="retur_lebih"
            )
        if kondisi == KondisiRetur.LAYAK and b.kedaluwarsa < hari_ini:
            raise AturanBisnisError(
                f"Batch {b.nomor_batch} sudah kedaluwarsa, catat sebagai rusak.",
                kode="retur_kedaluwarsa",
            )
        nilai = _nilai_retur(alokasi.item, diretur_item[alokasi.item_id], jumlah)
        diretur_item[alokasi.item_id] += jumlah
        alokasi.jumlah_diretur += jumlah
        alokasi.save(update_fields=["jumlah_diretur"])

        ubah_stok(b, jumlah, JenisMutasi.RETUR, pengguna, nomor)
        if kondisi == KondisiRetur.RUSAK:
            ubah_stok(b, -jumlah, JenisMutasi.RUSAK, pengguna, nomor, "Retur rusak")
        total += nilai
        baris_retur.append((alokasi, jumlah, kondisi, nilai))

    potong = min(total, t.sisa)
    kembali = total - potong
    retur = Retur.objects.create(
        nomor=nomor,
        transaksi=t,
        alasan=alasan,
        total=total,
        potong_piutang=potong,
        pengembalian_uang=kembali,
        dibuat_oleh=pengguna,
    )
    ReturItem.objects.bulk_create(
        ReturItem(retur=retur, alokasi=a, jumlah_botol=j, kondisi=k, nilai=n)
        for a, j, k, n in baris_retur
    )
    if kembali > 0:
        Pembayaran.objects.create(
            transaksi=t,
            jenis=JenisPembayaran.KEMBALI,
            metode=metode_pengembalian,
            jumlah=kembali,
            referensi=nomor,
            dibuat_oleh=pengguna,
        )
    t.total_retur += total
    t.terbayar -= kembali
    t.save(update_fields=["total_retur", "terbayar"])
    return retur


@transaction.atomic
def ajukan_pembatalan(pengguna, transaksi_id: int, alasan: str) -> Transaksi:
    t = _kunci_transaksi(transaksi_id)
    _wajib_selesai(t)
    t.status = StatusTransaksi.MENUNGGU_BATAL
    t.alasan_batal = alasan
    t.batal_diajukan_oleh = pengguna
    t.alasan_tolak_batal = ""
    t.save(update_fields=["status", "alasan_batal", "batal_diajukan_oleh", "alasan_tolak_batal"])
    return t


def _wajib_menunggu_batal(t: Transaksi) -> None:
    if t.status != StatusTransaksi.MENUNGGU_BATAL:
        raise AturanBisnisError("Tidak ada pengajuan pembatalan.", kode="status_transaksi")


@transaction.atomic
def setujui_pembatalan(
    pengguna, transaksi_id: int, metode_pengembalian: str = MetodeBayar.TUNAI
) -> Transaksi:
    """Barang yang belum diretur kembali ke batch asal, dan uang yang masuk dikembalikan."""
    t = _kunci_transaksi(transaksi_id)
    _wajib_menunggu_batal(t)

    alokasi = list(
        ItemTransaksiBatch.objects.select_for_update(of=("self",))
        .filter(item__transaksi=t)
        .order_by("id")
    )
    batch = kunci_batch({a.batch_id for a in alokasi})
    for a in alokasi:
        belum_diretur = a.jumlah_botol - a.jumlah_diretur
        if belum_diretur:
            ubah_stok(batch[a.batch_id], belum_diretur, JenisMutasi.BATAL, pengguna, t.nomor)

    if t.terbayar > 0:
        Pembayaran.objects.create(
            transaksi=t,
            jenis=JenisPembayaran.KEMBALI,
            metode=metode_pengembalian,
            jumlah=t.terbayar,
            referensi=t.nomor,
            catatan="Pembatalan transaksi",
            dibuat_oleh=pengguna,
        )
        t.terbayar = Decimal("0")
    t.status = StatusTransaksi.DIBATALKAN
    t.batal_diputuskan_oleh = pengguna
    t.dibatalkan_pada = timezone.now()
    t.save(update_fields=["status", "batal_diputuskan_oleh", "dibatalkan_pada", "terbayar"])
    return t


@transaction.atomic
def tolak_pembatalan(pengguna, transaksi_id: int, alasan: str) -> Transaksi:
    t = _kunci_transaksi(transaksi_id)
    _wajib_menunggu_batal(t)
    t.status = StatusTransaksi.SELESAI
    t.batal_diputuskan_oleh = pengguna
    t.alasan_tolak_batal = alasan
    t.save(update_fields=["status", "batal_diputuskan_oleh", "alasan_tolak_batal"])
    return t
