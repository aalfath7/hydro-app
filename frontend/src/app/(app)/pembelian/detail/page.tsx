"use client";

import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import Link from "next/link";

import { Bungkus, Halaman, Medan, PesanGalat, Pilih, WajibIzin } from "@/components/bagian";
import { Status } from "@/components/status";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { rupiah, tanggal, waktu } from "@/lib/format";
import { useAksi, useSesi } from "@/lib/kait";
import type { MetodeBayar, TransaksiDetail } from "@/lib/tipe";

type UbahBuka = (b: boolean) => void;

function PilihMetode({ nilai, ubah }: { nilai: MetodeBayar; ubah: (m: MetodeBayar) => void }) {
  return (
    <Pilih value={nilai} onChange={(e) => ubah(e.target.value as MetodeBayar)}>
      <option value="tunai">Tunai</option>
      <option value="transfer">Transfer</option>
      <option value="qris">QRIS</option>
    </Pilih>
  );
}

function DialogBayar({
  t,
  buka,
  ubah,
}: {
  t: TransaksiDetail;
  buka: boolean;
  ubah: UbahBuka;
}) {
  const [jumlah, setJumlah] = useState("");
  const [metode, setMetode] = useState<MetodeBayar>("tunai");
  const [referensi, setReferensi] = useState("");
  useEffect(() => setJumlah(t.sisa_tagihan), [t.sisa_tagihan, buka]);
  const simpan = useAksi(
    () => api.post(`/api/transaksi/${t.id}/bayar/`, { jumlah, metode, referensi }),
    { sukses: "Pembayaran dicatat.", setelah: () => ubah(false) },
  );
  return (
    <Dialog open={buka} onOpenChange={ubah}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Catat pembayaran</DialogTitle>
        </DialogHeader>
        <div className="grid gap-3">
          <Medan label="Jumlah (Rp)" bantuan={`Sisa tagihan ${rupiah(t.sisa_tagihan)}`}>
            <Input inputMode="decimal" value={jumlah} onChange={(e) => setJumlah(e.target.value)} />
          </Medan>
          <Medan label="Metode">
            <PilihMetode nilai={metode} ubah={setMetode} />
          </Medan>
          <Medan label="Referensi">
            <Input value={referensi} onChange={(e) => setReferensi(e.target.value)} />
          </Medan>
        </div>
        <DialogFooter>
          <Button disabled={!jumlah || simpan.isPending} onClick={() => simpan.mutate(undefined)}>
            Simpan
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

type BarisRetur = { jumlah: string; kondisi: "layak" | "rusak" };

function DialogRetur({
  t,
  buka,
  ubah,
}: {
  t: TransaksiDetail;
  buka: boolean;
  ubah: UbahBuka;
}) {
  const [isian, setIsian] = useState<Record<number, BarisRetur>>({});
  const [alasan, setAlasan] = useState("");
  const [metode, setMetode] = useState<MetodeBayar>("tunai");
  const baris = Object.entries(isian)
    .filter(([, b]) => Number(b.jumlah) > 0)
    .map(([id, b]) => ({
      alokasi: Number(id),
      jumlah_botol: Number(b.jumlah),
      kondisi: b.kondisi,
    }));
  const simpan = useAksi(
    () =>
      api.post("/api/retur/", {
        transaksi: t.id,
        items: baris,
        alasan,
        metode_pengembalian: metode,
      }),
    {
      sukses: "Retur dicatat.",
      setelah: () => {
        setIsian({});
        setAlasan("");
        ubah(false);
      },
    },
  );
  const ubahBaris = (id: number, sebagian: Partial<BarisRetur>) =>
    setIsian((i) => ({
      ...i,
      [id]: { ...(i[id] ?? { jumlah: "", kondisi: "layak" }), ...sebagian },
    }));

  return (
    <Dialog open={buka} onOpenChange={ubah}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Retur dari nota {t.nomor}</DialogTitle>
        </DialogHeader>
        <div className="space-y-2">
          {t.items.flatMap((item) =>
            item.alokasi
              .filter((a) => (a.jumlah_diretur ?? 0) < a.jumlah_botol)
              .map((a) => {
                const maks = a.jumlah_botol - (a.jumlah_diretur ?? 0);
                return (
                  <div
                    key={a.id}
                    className="grid items-center gap-2 border-b pb-2 text-sm sm:grid-cols-[1fr_6rem_8rem]"
                  >
                    <div>
                      <div className="font-medium">{item.nama_produk}</div>
                      <div className="text-muted-foreground text-xs">
                        Batch {a.nomor_batch} · bisa diretur {maks} botol
                      </div>
                    </div>
                    <Input
                      aria-label={`Jumlah retur batch ${a.nomor_batch}`}
                      inputMode="numeric"
                      placeholder="Botol"
                      value={isian[a.id]?.jumlah ?? ""}
                      onChange={(e) =>
                        ubahBaris(a.id, { jumlah: e.target.value.replace(/\D/g, "") })
                      }
                    />
                    <Pilih
                      aria-label={`Kondisi batch ${a.nomor_batch}`}
                      value={isian[a.id]?.kondisi ?? "layak"}
                      onChange={(e) =>
                        ubahBaris(a.id, { kondisi: e.target.value as BarisRetur["kondisi"] })
                      }
                    >
                      <option value="layak">Layak jual</option>
                      <option value="rusak">Rusak</option>
                    </Pilih>
                  </div>
                );
              }),
          )}
        </div>
        <Medan label="Alasan">
          <Input value={alasan} onChange={(e) => setAlasan(e.target.value)} />
        </Medan>
        <Medan
          label="Metode pengembalian uang"
          bantuan="Nilai retur memotong piutang dulu. Sisanya dikembalikan dengan metode ini."
        >
          <PilihMetode nilai={metode} ubah={setMetode} />
        </Medan>
        <DialogFooter>
          <Button
            disabled={!baris.length || !alasan.trim() || simpan.isPending}
            onClick={() => simpan.mutate(undefined)}
          >
            Simpan retur
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function DialogAlasan({
  judul,
  tombol,
  url,
  sukses,
  buka,
  ubah,
}: {
  judul: string;
  tombol: string;
  url: string;
  sukses: string;
  buka: boolean;
  ubah: UbahBuka;
}) {
  const [alasan, setAlasan] = useState("");
  const simpan = useAksi(() => api.post(url, { alasan }), {
    sukses,
    setelah: () => {
      setAlasan("");
      ubah(false);
    },
  });
  return (
    <Dialog open={buka} onOpenChange={ubah}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{judul}</DialogTitle>
        </DialogHeader>
        <Medan label="Alasan">
          <Textarea value={alasan} onChange={(e) => setAlasan(e.target.value)} />
        </Medan>
        <DialogFooter>
          <Button
            disabled={!alasan.trim() || simpan.isPending}
            onClick={() => simpan.mutate(undefined)}
          >
            {tombol}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function DialogSetujuiBatal({
  t,
  buka,
  ubah,
}: {
  t: TransaksiDetail;
  buka: boolean;
  ubah: UbahBuka;
}) {
  const [metode, setMetode] = useState<MetodeBayar>("tunai");
  const simpan = useAksi(
    () => api.post(`/api/transaksi/${t.id}/setujui-batal/`, { metode_pengembalian: metode }),
    { sukses: "Transaksi dibatalkan.", setelah: () => ubah(false) },
  );
  return (
    <Dialog open={buka} onOpenChange={ubah}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Setujui pembatalan {t.nomor}</DialogTitle>
        </DialogHeader>
        <p className="text-sm">
          Barang kembali ke batch asal
          {Number(t.terbayar) > 0 && ` dan uang ${rupiah(t.terbayar)} dicatat sebagai dikembalikan`}.
          Tindakan ini tidak bisa diurungkan.
        </p>
        {Number(t.terbayar) > 0 && (
          <Medan label="Metode pengembalian">
            <PilihMetode nilai={metode} ubah={setMetode} />
          </Medan>
        )}
        <DialogFooter>
          <Button
            variant="destructive"
            disabled={simpan.isPending}
            onClick={() => simpan.mutate(undefined)}
          >
            Setujui pembatalan
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function Isi() {
  const id = useSearchParams().get("id");
  const { punya } = useSesi();
  const [dialog, setDialog] = useState<string | null>(null);
  const tutup = (nama: string) => (b: boolean) => setDialog(b ? nama : null);

  const q = useQuery({
    queryKey: ["transaksi", id],
    queryFn: () => api.get<TransaksiDetail>(`/api/transaksi/${id}/`),
    enabled: !!id,
  });
  if (q.isLoading) return <Skeleton className="h-64 w-full" />;
  if (q.error || !q.data) return <PesanGalat galat={q.error} />;
  const t = q.data;
  const selesai = t.status === "selesai";

  return (
    <Halaman
      judul={`Nota ${t.nomor}`}
      keterangan={`${waktu(t.tanggal)} · dicatat ${t.dibuat_oleh_nama}`}
      aksi={
        <>
          <Button
            variant="outline"
            render={<a href={`/api/transaksi/${t.id}/nota/`} target="_blank" rel="noreferrer" />}
            nativeButton={false}
          >
            Cetak nota
          </Button>
          {selesai && Number(t.sisa_tagihan) > 0 && (
            <Button onClick={() => setDialog("bayar")}>Catat pembayaran</Button>
          )}
          {selesai && (
            <>
              <Button variant="outline" onClick={() => setDialog("retur")}>
                Retur
              </Button>
              <Button variant="destructive" onClick={() => setDialog("ajukan")}>
                Ajukan pembatalan
              </Button>
            </>
          )}
        </>
      }
    >
      {t.status === "menunggu_batal" && (
        <Alert>
          <AlertTitle>Menunggu persetujuan pembatalan</AlertTitle>
          <AlertDescription className="space-y-2">
            <p>Alasan: {t.alasan_batal}</p>
            {punya("setujui_pembatalan") && (
              <div className="flex gap-2">
                <Button variant="destructive" size="sm" onClick={() => setDialog("setujui")}>
                  Setujui
                </Button>
                <Button variant="outline" size="sm" onClick={() => setDialog("tolak")}>
                  Tolak
                </Button>
              </div>
            )}
          </AlertDescription>
        </Alert>
      )}
      {t.status === "dibatalkan" && (
        <Alert variant="destructive">
          <AlertTitle>Dibatalkan {waktu(t.dibatalkan_pada)}</AlertTitle>
          <AlertDescription>Alasan: {t.alasan_batal}</AlertDescription>
        </Alert>
      )}
      {t.alasan_tolak_batal && selesai && (
        <Alert>
          <AlertTitle>Pengajuan pembatalan ditolak</AlertTitle>
          <AlertDescription>{t.alasan_tolak_batal}</AlertDescription>
        </Alert>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Barang</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="divide-y text-sm">
              {t.items.map((i) => (
                <li key={i.id} className="py-2">
                  <div className="flex justify-between gap-3">
                    <span className="font-medium">{i.nama_produk}</span>
                    <span className="tabular-nums">{rupiah(i.subtotal)}</span>
                  </div>
                  <div className="text-muted-foreground text-xs">
                    {i.jumlah} {i.nama_satuan} × {rupiah(i.harga_satuan)} · batch{" "}
                    {i.alokasi
                      .map(
                        (a) =>
                          `${a.nomor_batch} (${a.jumlah_botol} botol${
                            a.jumlah_diretur ? `, ${a.jumlah_diretur} diretur` : ""
                          })`,
                      )
                      .join(", ")}
                  </div>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Ringkasan</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span>Pelanggan</span>
              <Link href={`/pelanggan/detail?id=${t.pelanggan}`} className="text-primary">
                {t.pelanggan_nama}
              </Link>
            </div>
            <div className="flex justify-between">
              <span>Status</span>
              <Status nilai={t.status_bayar} />
            </div>
            <div className="flex justify-between">
              <span>Total</span>
              <span className="tabular-nums">{rupiah(t.total)}</span>
            </div>
            {Number(t.total_retur) > 0 && (
              <div className="flex justify-between">
                <span>Retur</span>
                <span className="tabular-nums">{rupiah(t.total_retur)}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span>Terbayar</span>
              <span className="tabular-nums">{rupiah(t.terbayar)}</span>
            </div>
            {t.status !== "dibatalkan" && (
              <div className="flex justify-between font-semibold">
                <span>Sisa tagihan</span>
                <span className="tabular-nums">{rupiah(t.sisa_tagihan)}</span>
              </div>
            )}
            {t.jatuh_tempo && (
              <div className="flex justify-between">
                <span>Jatuh tempo</span>
                <span>{tanggal(t.jatuh_tempo)}</span>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Pembayaran</CardTitle>
          </CardHeader>
          <CardContent>
            {t.pembayaran.length === 0 ? (
              <p className="text-muted-foreground text-sm">Belum ada pembayaran.</p>
            ) : (
              <ul className="divide-y text-sm">
                {t.pembayaran.map((p) => (
                  <li key={p.id} className="flex justify-between gap-3 py-2">
                    <div>
                      <div>
                        {p.jenis_label} · {p.metode_label}
                      </div>
                      <div className="text-muted-foreground text-xs">
                        {waktu(p.dibuat_pada)} · {p.dibuat_oleh_nama}
                        {p.referensi && ` · ${p.referensi}`}
                      </div>
                    </div>
                    <span className="tabular-nums">
                      {p.jenis === "kembali" ? "-" : ""}
                      {rupiah(p.jumlah)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Retur</CardTitle>
          </CardHeader>
          <CardContent>
            {t.retur.length === 0 ? (
              <p className="text-muted-foreground text-sm">Tidak ada retur.</p>
            ) : (
              <ul className="divide-y text-sm">
                {t.retur.map((r) => (
                  <li key={r.id} className="py-2">
                    <div className="flex justify-between gap-3">
                      <span className="font-medium">{r.nomor}</span>
                      <span className="tabular-nums">{rupiah(r.total)}</span>
                    </div>
                    <div className="text-muted-foreground text-xs">
                      {waktu(r.tanggal)} · {r.alasan}
                    </div>
                    <div className="text-muted-foreground text-xs">
                      {r.items
                        .map((i) => `${i.jumlah_botol} botol ${i.kondisi} (${i.nomor_batch})`)
                        .join(", ")}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      <DialogBayar t={t} buka={dialog === "bayar"} ubah={tutup("bayar")} />
      <DialogRetur t={t} buka={dialog === "retur"} ubah={tutup("retur")} />
      <DialogAlasan
        judul={`Ajukan pembatalan ${t.nomor}`}
        tombol="Ajukan"
        url={`/api/transaksi/${t.id}/ajukan-batal/`}
        sukses="Pengajuan dikirim ke pemilik."
        buka={dialog === "ajukan"}
        ubah={tutup("ajukan")}
      />
      <DialogAlasan
        judul={`Tolak pembatalan ${t.nomor}`}
        tombol="Tolak pembatalan"
        url={`/api/transaksi/${t.id}/tolak-batal/`}
        sukses="Pembatalan ditolak."
        buka={dialog === "tolak"}
        ubah={tutup("tolak")}
      />
      <DialogSetujuiBatal t={t} buka={dialog === "setujui"} ubah={tutup("setujui")} />
    </Halaman>
  );
}

export default function HalamanDetailTransaksi() {
  return (
    <WajibIzin izin="kelola_transaksi">
      <Bungkus>
        <Isi />
      </Bungkus>
    </WajibIzin>
  );
}
