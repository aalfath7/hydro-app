"use client";

import { Minus, Plus, Trash2, UserPlus } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";

import { Cari, Medan, PesanGalat, Pilih, WajibIzin } from "@/components/bagian";
import { DialogPelanggan } from "@/components/dialog-pelanggan";
import { PilihPelanggan } from "@/components/pilih-pelanggan";
import { Status } from "@/components/status";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { hariIni, rupiah } from "@/lib/format";
import { useAksi, useDaftar, useTunda } from "@/lib/kait";
import type { MetodeBayar, Pelanggan, Produk, Satuan, TransaksiDetail } from "@/lib/tipe";
import Link from "next/link";

type Baris = { produk: Produk; satuan: Satuan; jumlah: number };

function DaftarProduk({ tambah }: { tambah: (p: Produk, s: Satuan) => void }) {
  const [q, setQ] = useState("");
  const qTunda = useTunda(q);
  const daftar = useDaftar<Produk>("/api/produk/", { q: qTunda, aktif: 1, ukuran: 100 });

  return (
    <Card className="min-h-0 lg:col-span-3">
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <CardTitle className="text-base">Produk</CardTitle>
        <Cari nilai={q} ubah={setQ} placeholder="Cari nama atau SKU" />
      </CardHeader>
      <CardContent>
        {daftar.error ? (
          <PesanGalat galat={daftar.error} />
        ) : (
          <ul className="divide-y lg:max-h-[calc(100vh-14rem)] lg:overflow-y-auto">
            {daftar.data?.results.length === 0 && (
              <li className="text-muted-foreground py-6 text-center text-sm">
                Produk tidak ditemukan.
              </li>
            )}
            {daftar.data?.results.map((p) => (
              <li key={p.id} className="flex flex-wrap items-center justify-between gap-2 py-2.5">
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium">{p.nama}</div>
                  <div className="text-muted-foreground flex items-center gap-2 text-xs">
                    <span className="tabular-nums">{p.stok_teks}</span>
                    {p.status_stok !== "aman" && <Status nilai={p.status_stok} />}
                  </div>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {p.satuan
                    .filter((s) => s.aktif && s.harga)
                    .map((s) => (
                      <Button
                        key={s.id}
                        variant="outline"
                        size="sm"
                        className="tabular-nums"
                        disabled={p.stok_tersedia < s.isi_botol}
                        onClick={() => tambah(p, s)}
                      >
                        <Plus />
                        {s.nama} {rupiah(s.harga)}
                      </Button>
                    ))}
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

function Isi() {
  const [keranjang, setKeranjang] = useState<Baris[]>([]);
  const [pelanggan, setPelanggan] = useState<Pelanggan | null>(null);
  const [metode, setMetode] = useState<MetodeBayar>("tunai");
  const [tempo, setTempo] = useState(false);
  const [uangMuka, setUangMuka] = useState("");
  const [jatuhTempo, setJatuhTempo] = useState(hariIni(14));
  const [diterima, setDiterima] = useState("");
  const [referensi, setReferensi] = useState("");
  const [pelangganBaru, setPelangganBaru] = useState(false);
  const [selesai, setSelesai] = useState<TransaksiDetail | null>(null);
  // Dipertahankan saat kirim ulang, supaya klik ganda tidak membuat nota kedua.
  const kunci = useRef(crypto.randomUUID());

  const total = keranjang.reduce((t, b) => t + Number(b.satuan.harga) * b.jumlah, 0);
  const uangMukaAngka = Number(uangMuka || 0);

  function tambah(produk: Produk, satuan: Satuan) {
    setKeranjang((isi) => {
      const ada = isi.find((b) => b.satuan.id === satuan.id);
      if (ada) {
        return isi.map((b) => (b === ada ? { ...b, jumlah: b.jumlah + 1 } : b));
      }
      return [...isi, { produk, satuan, jumlah: 1 }];
    });
  }

  const ubahJumlah = (id: number, jumlah: number) =>
    setKeranjang((isi) =>
      isi.flatMap((b) =>
        b.satuan.id === id ? (jumlah > 0 ? [{ ...b, jumlah }] : []) : [b],
      ),
    );

  const melebihi = (produkId: number) => {
    const baris = keranjang.filter((b) => b.produk.id === produkId);
    const perlu = baris.reduce((t, b) => t + b.jumlah * b.satuan.isi_botol, 0);
    return perlu > (baris[0]?.produk.stok_tersedia ?? 0);
  };
  const adaLebih = keranjang.some((b) => melebihi(b.produk.id));

  const simpan = useAksi(
    () =>
      api.post<TransaksiDetail>("/api/transaksi/", {
        kunci_idempoten: kunci.current,
        pelanggan: pelanggan!.id,
        items: keranjang.map((b) => ({ satuan: b.satuan.id, jumlah: b.jumlah })),
        metode,
        tempo,
        uang_muka: tempo ? uangMuka || "0" : "0",
        jatuh_tempo: tempo ? jatuhTempo : null,
        referensi,
      }),
    {
      setelah: (t) => {
        setSelesai(t);
        kunci.current = crypto.randomUUID();
        setKeranjang([]);
        setPelanggan(null);
        setTempo(false);
        setUangMuka("");
        setDiterima("");
        setReferensi("");
      },
    },
  );

  const tempoSalah = tempo && (!jatuhTempo || uangMukaAngka >= total);
  const bisaSimpan =
    !!pelanggan && keranjang.length > 0 && !adaLebih && !tempoSalah && !simpan.isPending;
  const kembalian = Number(diterima || 0) - total;

  return (
    <div className="mx-auto w-full max-w-7xl space-y-4">
      <h1 className="text-xl font-semibold tracking-tight">Transaksi baru</h1>
      <div className="grid items-start gap-4 lg:grid-cols-5">
        <DaftarProduk tambah={tambah} />

        <Card className="lg:col-span-2 lg:sticky lg:top-20">
          <CardHeader>
            <CardTitle className="text-base">Keranjang</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Medan label="Pelanggan">
              <div className="flex gap-2">
                <div className="min-w-0 flex-1">
                  <PilihPelanggan nilai={pelanggan} ubah={setPelanggan} />
                </div>
                <Button
                  variant="outline"
                  size="icon"
                  aria-label="Pelanggan baru"
                  onClick={() => setPelangganBaru(true)}
                >
                  <UserPlus />
                </Button>
              </div>
            </Medan>

            {keranjang.length === 0 ? (
              <p className="text-muted-foreground py-4 text-center text-sm">
                Pilih produk dari daftar.
              </p>
            ) : (
              <ul className="divide-y text-sm">
                {keranjang.map((b) => (
                  <li key={b.satuan.id} className="space-y-1 py-2">
                    <div className="flex justify-between gap-2">
                      <span className="min-w-0 truncate font-medium">{b.produk.nama}</span>
                      <span className="tabular-nums">
                        {rupiah(Number(b.satuan.harga) * b.jumlah)}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Button
                        variant="outline"
                        size="icon-xs"
                        aria-label="Kurangi"
                        onClick={() => ubahJumlah(b.satuan.id, b.jumlah - 1)}
                      >
                        <Minus />
                      </Button>
                      <Input
                        aria-label={`Jumlah ${b.produk.nama}`}
                        inputMode="numeric"
                        className="h-6 w-14 text-center tabular-nums"
                        value={b.jumlah}
                        onChange={(e) =>
                          ubahJumlah(b.satuan.id, Number(e.target.value.replace(/\D/g, "")))
                        }
                      />
                      <Button
                        variant="outline"
                        size="icon-xs"
                        aria-label="Tambah"
                        onClick={() => ubahJumlah(b.satuan.id, b.jumlah + 1)}
                      >
                        <Plus />
                      </Button>
                      <span className="text-muted-foreground text-xs">
                        {b.satuan.nama} × {rupiah(b.satuan.harga)}
                      </span>
                      <Button
                        variant="ghost"
                        size="icon-xs"
                        className="ml-auto"
                        aria-label={`Hapus ${b.produk.nama}`}
                        onClick={() => ubahJumlah(b.satuan.id, 0)}
                      >
                        <Trash2 />
                      </Button>
                    </div>
                    {melebihi(b.produk.id) && (
                      <p className="text-destructive text-xs">
                        Melebihi stok ({b.produk.stok_teks}).
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            )}

            <div className="flex items-baseline justify-between border-t pt-3">
              <span className="text-sm">Total</span>
              <span className="text-xl font-semibold tabular-nums">{rupiah(total)}</span>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <Medan label="Metode bayar">
                <Pilih value={metode} onChange={(e) => setMetode(e.target.value as MetodeBayar)}>
                  <option value="tunai">Tunai</option>
                  <option value="transfer">Transfer</option>
                  <option value="qris">QRIS</option>
                </Pilih>
              </Medan>
              {metode === "tunai" && !tempo ? (
                <Medan
                  label="Uang diterima"
                  bantuan={
                    diterima && kembalian >= 0 ? `Kembalian ${rupiah(kembalian)}` : undefined
                  }
                >
                  <Input
                    inputMode="decimal"
                    value={diterima}
                    onChange={(e) => setDiterima(e.target.value)}
                  />
                </Medan>
              ) : metode !== "tunai" ? (
                <Medan label="Referensi">
                  <Input
                    placeholder="No. transfer/QRIS"
                    value={referensi}
                    onChange={(e) => setReferensi(e.target.value)}
                  />
                </Medan>
              ) : null}
            </div>

            <div className="flex items-center gap-2">
              <Checkbox
                id="tempo"
                checked={tempo}
                onCheckedChange={(c) => setTempo(c === true)}
              />
              <Label htmlFor="tempo">Bayar tempo</Label>
            </div>
            {tempo && (
              <div className="grid gap-3 sm:grid-cols-2">
                <Medan
                  label="Uang muka"
                  galat={
                    uangMukaAngka >= total && total > 0 ? "Harus di bawah total." : undefined
                  }
                >
                  <Input
                    inputMode="decimal"
                    value={uangMuka}
                    onChange={(e) => setUangMuka(e.target.value)}
                  />
                </Medan>
                <Medan label="Jatuh tempo">
                  <Input
                    type="date"
                    min={hariIni()}
                    value={jatuhTempo}
                    onChange={(e) => setJatuhTempo(e.target.value)}
                  />
                </Medan>
              </div>
            )}

            <Button
              size="lg"
              className="w-full"
              disabled={!bisaSimpan}
              onClick={() => simpan.mutate(undefined)}
            >
              Simpan transaksi
            </Button>
          </CardContent>
        </Card>
      </div>

      <DialogPelanggan
        buka={pelangganBaru}
        ubah={setPelangganBaru}
        setelah={(p) => {
          setPelanggan(p);
          toast.success(`${p.nama} dipilih.`);
        }}
      />

      <Dialog open={!!selesai} onOpenChange={(b) => !b && setSelesai(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Transaksi tersimpan</DialogTitle>
          </DialogHeader>
          {selesai && (
            <p className="text-sm">
              Nota <strong>{selesai.nomor}</strong> untuk {selesai.pelanggan_nama}, total{" "}
              <strong>{rupiah(selesai.total)}</strong>.
            </p>
          )}
          <DialogFooter>
            {selesai && (
              <>
                <Button
                  variant="outline"
                  render={<Link href={`/pembelian/detail?id=${selesai.id}`} />}
                  nativeButton={false}
                >
                  Lihat detail
                </Button>
                <Button
                  variant="outline"
                  render={
                    <a href={`/api/transaksi/${selesai.id}/nota/`} target="_blank" rel="noreferrer" />
                  }
                  nativeButton={false}
                >
                  Cetak nota
                </Button>
              </>
            )}
            <Button onClick={() => setSelesai(null)}>Transaksi baru</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function HalamanTransaksiBaru() {
  return (
    <WajibIzin izin="kelola_transaksi">
      <Isi />
    </WajibIzin>
  );
}
