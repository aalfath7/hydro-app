import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from pembelian.models import Pembayaran, Transaksi
from produk.layanan import catat_harga
from stok.models import BatchProduk, MutasiStok

from .conftest import stok_masuk

URL = "/api/transaksi/"


def data_jual(pelanggan, items, **lain):
    return {
        "kunci_idempoten": str(uuid.uuid4()),
        "pelanggan": pelanggan.id,
        "items": items,
        "metode": "tunai",
        **lain,
    }


def jual(klien, pelanggan, items, **lain):
    return klien.post(URL, data_jual(pelanggan, items, **lain), format="json")


def test_fefo_memakai_batch_kedaluwarsa_terdekat_dulu(
    klien_admin, pemilik, pelanggan, produk, botol
):
    jauh = stok_masuk(pemilik, produk, 10, "JAUH", hari=200)
    dekat = stok_masuk(pemilik, produk, 5, "DEKAT", hari=30)

    r = jual(klien_admin, pelanggan, [{"satuan": botol.id, "jumlah": 7}])

    assert r.status_code == 201
    dekat.refresh_from_db()
    jauh.refresh_from_db()
    assert (dekat.sisa, jauh.sisa) == (0, 8)
    alokasi = r.data["items"][0]["alokasi"]
    assert [(a["nomor_batch"], a["jumlah_botol"]) for a in alokasi] == [("DEKAT", 5), ("JAUH", 2)]


def test_batch_kedaluwarsa_tidak_terjual(klien_admin, pemilik, pelanggan, produk, botol):
    lama = stok_masuk(pemilik, produk, 100, "LAMA", hari=-1)

    r = jual(klien_admin, pelanggan, [{"satuan": botol.id, "jumlah": 1}])

    assert r.status_code == 409
    assert r.data["kode"] == "stok_tidak_cukup"
    lama.refresh_from_db()
    assert lama.sisa == 100


def test_stok_tidak_cukup_tidak_menyimpan_apa_pun(klien_admin, pemilik, pelanggan, produk, botol):
    batch = stok_masuk(pemilik, produk, 5, "A")

    r = jual(klien_admin, pelanggan, [{"satuan": botol.id, "jumlah": 6}])

    assert r.status_code == 409
    assert r.data["rincian"][0]["tersedia"] == 5
    batch.refresh_from_db()
    assert batch.sisa == 5
    assert not Transaksi.objects.exists()
    assert not MutasiStok.objects.filter(jenis="penjualan").exists()


def test_dua_baris_produk_sama_dihitung_bersama(
    klien_admin, pemilik, pelanggan, produk, botol, dus
):
    stok_masuk(pemilik, produk, 25, "A")
    r = jual(
        klien_admin,
        pelanggan,
        [{"satuan": dus.id, "jumlah": 1}, {"satuan": botol.id, "jumlah": 2}],
    )
    assert r.status_code == 409
    r = jual(
        klien_admin,
        pelanggan,
        [{"satuan": dus.id, "jumlah": 1}, {"satuan": botol.id, "jumlah": 1}],
    )
    assert r.status_code == 201
    assert BatchProduk.objects.get(nomor_batch="A").sisa == 0


def test_kegagalan_di_tengah_membatalkan_seluruh_transaksi(
    klien_admin, pemilik, pelanggan, produk, botol, monkeypatch
):
    batch = stok_masuk(pemilik, produk, 10, "A")

    def gagal(*a, **k):
        raise RuntimeError("disk penuh")

    monkeypatch.setattr(Pembayaran.objects, "create", gagal)
    klien_admin.raise_request_exception = False
    r = jual(klien_admin, pelanggan, [{"satuan": botol.id, "jumlah": 3}])

    assert r.status_code == 500
    batch.refresh_from_db()
    assert batch.sisa == 10
    assert not Transaksi.objects.exists()
    assert not MutasiStok.objects.filter(jenis="penjualan").exists()


def test_klik_ganda_tidak_mengurangi_stok_dua_kali(klien_admin, pemilik, pelanggan, produk, botol):
    batch = stok_masuk(pemilik, produk, 10, "A")
    data = data_jual(pelanggan, [{"satuan": botol.id, "jumlah": 2}])

    pertama = klien_admin.post(URL, data, format="json")
    kedua = klien_admin.post(URL, data, format="json")

    assert pertama.data["nomor"] == kedua.data["nomor"]
    batch.refresh_from_db()
    assert batch.sisa == 8
    assert Transaksi.objects.count() == 1


def test_harga_dari_server_dan_nota_lama_tidak_berubah(
    klien_admin, pemilik, pelanggan, produk, botol
):
    stok_masuk(pemilik, produk, 10, "A")
    r = jual(
        klien_admin,
        pelanggan,
        [{"satuan": botol.id, "jumlah": 2, "harga_satuan": "1"}],
        total="1",
    )
    assert r.data["total"] == "7000.00"

    besok_berlaku = timezone.localdate()
    botol.riwayat_harga.update(berlaku_mulai=besok_berlaku - timedelta(days=5))
    catat_harga(botol, Decimal("4000"), besok_berlaku, pemilik)
    r2 = jual(klien_admin, pelanggan, [{"satuan": botol.id, "jumlah": 1}])

    assert r2.data["total"] == "4000.00"
    lama = klien_admin.get(f"{URL}{r.data['id']}/")
    assert lama.data["items"][0]["harga_satuan"] == "3500.00"


def test_harga_masa_depan_belum_berlaku(klien_admin, pemilik, pelanggan, produk, botol):
    stok_masuk(pemilik, produk, 10, "A")
    catat_harga(botol, Decimal("9000"), timezone.localdate() + timedelta(days=3), pemilik)
    r = jual(klien_admin, pelanggan, [{"satuan": botol.id, "jumlah": 1}])
    assert r.data["total"] == "3500.00"


def test_produk_nonaktif_ditolak(klien_admin, pemilik, pelanggan, produk, botol):
    stok_masuk(pemilik, produk, 10, "A")
    produk.aktif = False
    produk.save()
    r = jual(klien_admin, pelanggan, [{"satuan": botol.id, "jumlah": 1}])
    assert r.status_code == 409
    assert r.data["kode"] == "produk_nonaktif"


def test_tempo_dan_pelunasan(klien_admin, pemilik, pelanggan, produk, botol):
    stok_masuk(pemilik, produk, 10, "A")
    tempo = (timezone.localdate() + timedelta(days=14)).isoformat()
    r = jual(
        klien_admin,
        pelanggan,
        [{"satuan": botol.id, "jumlah": 10}],
        tempo=True,
        uang_muka="5000",
        jatuh_tempo=tempo,
    )
    assert r.status_code == 201
    assert r.data["status_bayar"] == "tempo"
    assert r.data["sisa_tagihan"] == "30000.00"

    id_t = r.data["id"]
    lebih = klien_admin.post(
        f"{URL}{id_t}/bayar/", {"jumlah": "30000.01", "metode": "tunai"}, format="json"
    )
    assert lebih.status_code == 409

    lunas = klien_admin.post(
        f"{URL}{id_t}/bayar/", {"jumlah": "30000", "metode": "transfer"}, format="json"
    )
    assert lunas.data["status_bayar"] == "lunas"
    assert lunas.data["sisa_tagihan"] == "0.00"

    klien_pelanggan = klien_admin.get(f"/api/pelanggan/{pelanggan.id}/")
    assert klien_pelanggan.data["total_piutang"] == "0.00"


def test_tempo_wajib_jatuh_tempo(klien_admin, pemilik, pelanggan, produk, botol):
    stok_masuk(pemilik, produk, 10, "A")
    r = jual(klien_admin, pelanggan, [{"satuan": botol.id, "jumlah": 1}], tempo=True)
    assert r.status_code == 400
    assert "jatuh_tempo" in r.data["rincian"]


def _alokasi(respons, indeks=0):
    return respons.data["items"][indeks]["alokasi"][0]["id"]


def test_retur_layak_kembali_ke_batch_asal_dan_uang_dikembalikan(
    klien_admin, pemilik, pelanggan, produk, botol
):
    batch = stok_masuk(pemilik, produk, 10, "A")
    r = jual(klien_admin, pelanggan, [{"satuan": botol.id, "jumlah": 4}])

    retur = klien_admin.post(
        "/api/retur/",
        {
            "transaksi": r.data["id"],
            "alasan": "Kelebihan",
            "items": [{"alokasi": _alokasi(r), "jumlah_botol": 2, "kondisi": "layak"}],
        },
        format="json",
    )

    assert retur.status_code == 201
    assert retur.data["pengembalian_uang"] == "7000.00"
    assert retur.data["potong_piutang"] == "0.00"
    batch.refresh_from_db()
    assert batch.sisa == 8
    t = Transaksi.objects.get(pk=r.data["id"])
    assert t.terbayar == Decimal("7000") and t.sisa_tagihan == 0


def test_retur_rusak_tidak_menambah_stok_tetapi_tercatat(
    klien_admin, pemilik, pelanggan, produk, botol
):
    batch = stok_masuk(pemilik, produk, 10, "A")
    r = jual(klien_admin, pelanggan, [{"satuan": botol.id, "jumlah": 4}])

    klien_admin.post(
        "/api/retur/",
        {
            "transaksi": r.data["id"],
            "alasan": "Bocor",
            "items": [{"alokasi": _alokasi(r), "jumlah_botol": 1, "kondisi": "rusak"}],
        },
        format="json",
    )

    batch.refresh_from_db()
    assert batch.sisa == 6
    assert MutasiStok.objects.filter(batch=batch, jenis="rusak", jumlah=-1).exists()


def test_retur_tempo_memotong_piutang_dulu(klien_admin, pemilik, pelanggan, produk, botol):
    stok_masuk(pemilik, produk, 10, "A")
    tempo = (timezone.localdate() + timedelta(days=7)).isoformat()
    r = jual(
        klien_admin,
        pelanggan,
        [{"satuan": botol.id, "jumlah": 4}],
        tempo=True,
        uang_muka="10000",
        jatuh_tempo=tempo,
    )

    retur = klien_admin.post(
        "/api/retur/",
        {
            "transaksi": r.data["id"],
            "alasan": "Salah kirim",
            "items": [{"alokasi": _alokasi(r), "jumlah_botol": 3, "kondisi": "layak"}],
        },
        format="json",
    )

    assert retur.data["total"] == "10500.00"
    assert retur.data["potong_piutang"] == "4000.00"
    assert retur.data["pengembalian_uang"] == "6500.00"
    t = Transaksi.objects.get(pk=r.data["id"])
    assert t.sisa_tagihan == 0
    assert t.terbayar == Decimal("3500")


def test_retur_per_botol_dari_dus_tidak_selisih_pembulatan(
    klien_admin, pemilik, pelanggan, produk, dus
):
    stok_masuk(pemilik, produk, 24, "A")
    dus.riwayat_harga.update(harga=Decimal("78001"))
    r = jual(klien_admin, pelanggan, [{"satuan": dus.id, "jumlah": 1}])
    alokasi = _alokasi(r)

    total = Decimal("0")
    for _ in range(24):
        retur = klien_admin.post(
            "/api/retur/",
            {
                "transaksi": r.data["id"],
                "alasan": "Uji",
                "items": [{"alokasi": alokasi, "jumlah_botol": 1, "kondisi": "layak"}],
            },
            format="json",
        )
        assert retur.status_code == 201
        total += Decimal(retur.data["total"])

    assert total == Decimal("78001")
    t = Transaksi.objects.get(pk=r.data["id"])
    assert t.terbayar == 0


def test_retur_tidak_boleh_melebihi_pembelian(klien_admin, pemilik, pelanggan, produk, botol):
    stok_masuk(pemilik, produk, 10, "A")
    r = jual(klien_admin, pelanggan, [{"satuan": botol.id, "jumlah": 2}])
    baris = {"alokasi": _alokasi(r), "jumlah_botol": 2, "kondisi": "layak"}
    data = {"transaksi": r.data["id"], "alasan": "Uji", "items": [baris, baris]}

    balasan = klien_admin.post("/api/retur/", data, format="json")

    assert balasan.status_code == 409
    assert balasan.data["kode"] == "retur_lebih"
    assert BatchProduk.objects.get(nomor_batch="A").sisa == 8


def test_retur_alokasi_nota_lain_ditolak(klien_admin, pemilik, pelanggan, produk, botol):
    stok_masuk(pemilik, produk, 10, "A")
    r1 = jual(klien_admin, pelanggan, [{"satuan": botol.id, "jumlah": 1}])
    r2 = jual(klien_admin, pelanggan, [{"satuan": botol.id, "jumlah": 1}])
    balasan = klien_admin.post(
        "/api/retur/",
        {
            "transaksi": r1.data["id"],
            "alasan": "Uji",
            "items": [{"alokasi": _alokasi(r2), "jumlah_botol": 1, "kondisi": "layak"}],
        },
        format="json",
    )
    assert balasan.status_code == 409
    assert balasan.data["kode"] == "alokasi_salah"


def test_pembatalan_perlu_persetujuan_pemilik(
    klien_admin, klien_pemilik, pemilik, pelanggan, produk, botol
):
    batch = stok_masuk(pemilik, produk, 10, "A")
    r = jual(klien_admin, pelanggan, [{"satuan": botol.id, "jumlah": 4}])
    id_t = r.data["id"]

    assert klien_admin.post(f"{URL}{id_t}/setujui-batal/", {}, format="json").status_code == 403

    ajukan = klien_admin.post(f"{URL}{id_t}/ajukan-batal/", {"alasan": "Salah"}, format="json")
    assert ajukan.data["status"] == "menunggu_batal"
    batch.refresh_from_db()
    assert batch.sisa == 6

    tutup = klien_admin.post(
        f"{URL}{id_t}/bayar/", {"jumlah": "1", "metode": "tunai"}, format="json"
    )
    assert tutup.status_code == 409

    setuju = klien_pemilik.post(
        f"{URL}{id_t}/setujui-batal/", {"metode_pengembalian": "transfer"}, format="json"
    )
    assert setuju.data["status"] == "dibatalkan"
    assert setuju.data["status_bayar"] == "dibatalkan"
    assert Transaksi.objects.get(pk=id_t).alasan_batal == "Salah"
    batch.refresh_from_db()
    assert batch.sisa == 10
    kembali = Pembayaran.objects.get(transaksi_id=id_t, jenis="kembali")
    assert kembali.jumlah == Decimal("14000")


def test_pembatalan_tidak_menggandakan_barang_yang_sudah_diretur(
    klien_admin, klien_pemilik, pemilik, pelanggan, produk, botol
):
    batch = stok_masuk(pemilik, produk, 10, "A")
    r = jual(klien_admin, pelanggan, [{"satuan": botol.id, "jumlah": 4}])
    klien_admin.post(
        "/api/retur/",
        {
            "transaksi": r.data["id"],
            "alasan": "Rusak",
            "items": [{"alokasi": _alokasi(r), "jumlah_botol": 1, "kondisi": "rusak"}],
        },
        format="json",
    )
    klien_admin.post(f"{URL}{r.data['id']}/ajukan-batal/", {"alasan": "x"}, format="json")
    klien_pemilik.post(f"{URL}{r.data['id']}/setujui-batal/", {}, format="json")

    batch.refresh_from_db()
    assert batch.sisa == 9


def test_tolak_pembatalan_mengembalikan_status(
    klien_admin, klien_pemilik, pemilik, pelanggan, produk, botol
):
    stok_masuk(pemilik, produk, 10, "A")
    r = jual(klien_admin, pelanggan, [{"satuan": botol.id, "jumlah": 4}])
    klien_admin.post(f"{URL}{r.data['id']}/ajukan-batal/", {"alasan": "x"}, format="json")
    tolak = klien_pemilik.post(
        f"{URL}{r.data['id']}/tolak-batal/", {"alasan": "Barang terkirim"}, format="json"
    )
    assert tolak.data["status"] == "selesai"
    assert tolak.data["alasan_tolak_batal"] == "Barang terkirim"


def test_filter_status_bayar(klien_admin, pemilik, pelanggan, produk, botol):
    stok_masuk(pemilik, produk, 10, "A")
    jual(klien_admin, pelanggan, [{"satuan": botol.id, "jumlah": 1}])
    tempo = (timezone.localdate() + timedelta(days=7)).isoformat()
    jual(klien_admin, pelanggan, [{"satuan": botol.id, "jumlah": 1}], tempo=True, jatuh_tempo=tempo)

    assert klien_admin.get(URL, {"status_bayar": "lunas"}).data["count"] == 1
    assert klien_admin.get(URL, {"status_bayar": "belum_lunas"}).data["count"] == 1


@pytest.mark.parametrize("nilai", ["-1", "abc"])
def test_filter_tidak_valid_tidak_membuat_galat(klien_admin, pelanggan, nilai):
    assert klien_admin.get(URL, {"pelanggan": nilai}).status_code == 200
