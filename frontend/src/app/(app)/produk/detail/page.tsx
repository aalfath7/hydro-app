"use client";

import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import {
  Bungkus,
  Halaman,
  Medan,
  PesanGalat,
  Pilih,
  TabelData,
  WajibIzin,
} from "@/components/bagian";
import { Status } from "@/components/status";
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
import { api } from "@/lib/api";
import { hariIni, rupiah, tanggal, waktu } from "@/lib/format";
import { useAksi, useDaftar, useSesi } from "@/lib/kait";
import type { Batch, Harga, Kategori, Mutasi, Produk } from "@/lib/tipe";

function DialogHarga({
  produk,
  buka,
  ubah,
}: {
  produk: Produk;
  buka: boolean;
  ubah: (b: boolean) => void;
}) {
  const [satuan, setSatuan] = useState("");
  const [harga, setHarga] = useState("");
  const [mulai, setMulai] = useState(hariIni());
  const simpan = useAksi(
    () =>
      api.post("/api/harga/", { satuan: Number(satuan), harga, berlaku_mulai: mulai }),
    {
      sukses: "Harga dicatat.",
      setelah: () => {
        setHarga("");
        ubah(false);
      },
    },
  );
  return (
    <Dialog open={buka} onOpenChange={ubah}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Ubah harga</DialogTitle>
        </DialogHeader>
        <div className="grid gap-3">
          <Medan label="Satuan">
            <Pilih value={satuan} onChange={(e) => setSatuan(e.target.value)}>
              <option value="">Pilih satuan</option>
              {produk.satuan.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.nama} ({s.isi_botol} botol)
                </option>
              ))}
            </Pilih>
          </Medan>
          <Medan label="Harga baru (Rp)">
            <Input inputMode="decimal" value={harga} onChange={(e) => setHarga(e.target.value)} />
          </Medan>
          <Medan label="Berlaku mulai" bantuan="Nota lama tidak ikut berubah.">
            <Input type="date" value={mulai} onChange={(e) => setMulai(e.target.value)} />
          </Medan>
        </div>
        <DialogFooter>
          <Button disabled={!satuan || !harga || simpan.isPending} onClick={() => simpan.mutate()}>
            Simpan
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function DialogSatuan({
  produk,
  buka,
  ubah,
}: {
  produk: Produk;
  buka: boolean;
  ubah: (b: boolean) => void;
}) {
  const [nama, setNama] = useState("");
  const [isi, setIsi] = useState("");
  const [harga, setHarga] = useState("");
  const simpan = useAksi(
    () => api.post("/api/satuan/", { produk: produk.id, nama, isi_botol: Number(isi), harga }),
    {
      sukses: "Satuan ditambahkan.",
      setelah: () => {
        setNama("");
        setIsi("");
        setHarga("");
        ubah(false);
      },
    },
  );
  return (
    <Dialog open={buka} onOpenChange={ubah}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Tambah satuan</DialogTitle>
        </DialogHeader>
        <div className="grid gap-3">
          <Medan label="Nama satuan">
            <Input placeholder="dus, pak" value={nama} onChange={(e) => setNama(e.target.value)} />
          </Medan>
          <Medan label="Isi (botol)">
            <Input inputMode="numeric" value={isi} onChange={(e) => setIsi(e.target.value)} />
          </Medan>
          <Medan label="Harga (Rp)">
            <Input inputMode="decimal" value={harga} onChange={(e) => setHarga(e.target.value)} />
          </Medan>
        </div>
        <DialogFooter>
          <Button
            disabled={!nama || !isi || !harga || simpan.isPending}
            onClick={() => simpan.mutate()}
          >
            Simpan
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function DialogUbah({
  produk,
  buka,
  ubah,
}: {
  produk: Produk;
  buka: boolean;
  ubah: (b: boolean) => void;
}) {
  const [nama, setNama] = useState(produk.nama);
  const [sku, setSku] = useState(produk.sku);
  const [kemasan, setKemasan] = useState(produk.kemasan ?? "");
  const [kategori, setKategori] = useState(String(produk.kategori));
  const [minimum, setMinimum] = useState(String(produk.stok_minimum ?? 0));
  useEffect(() => {
    setNama(produk.nama);
    setSku(produk.sku);
    setKemasan(produk.kemasan ?? "");
    setKategori(String(produk.kategori));
    setMinimum(String(produk.stok_minimum ?? 0));
  }, [produk]);
  const daftar = useQuery({
    queryKey: ["kategori"],
    queryFn: () => api.get<Kategori[]>("/api/kategori/"),
  });
  const simpan = useAksi(
    () =>
      api.patch(`/api/produk/${produk.id}/`, {
        nama,
        sku,
        kemasan,
        kategori: Number(kategori),
        stok_minimum: Number(minimum),
      }),
    { sukses: "Produk diperbarui.", setelah: () => ubah(false) },
  );
  return (
    <Dialog open={buka} onOpenChange={ubah}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Ubah produk</DialogTitle>
        </DialogHeader>
        <div className="grid gap-3 sm:grid-cols-2">
          <Medan label="Nama" className="sm:col-span-2">
            <Input value={nama} onChange={(e) => setNama(e.target.value)} />
          </Medan>
          <Medan label="SKU">
            <Input value={sku} onChange={(e) => setSku(e.target.value)} />
          </Medan>
          <Medan label="Kategori">
            <Pilih value={kategori} onChange={(e) => setKategori(e.target.value)}>
              {daftar.data?.map((k) => (
                <option key={k.id} value={k.id}>
                  {k.nama}
                </option>
              ))}
            </Pilih>
          </Medan>
          <Medan label="Kemasan">
            <Input value={kemasan} onChange={(e) => setKemasan(e.target.value)} />
          </Medan>
          <Medan label="Stok minimum (botol)">
            <Input
              inputMode="numeric"
              value={minimum}
              onChange={(e) => setMinimum(e.target.value)}
            />
          </Medan>
        </div>
        <DialogFooter>
          <Button disabled={simpan.isPending} onClick={() => simpan.mutate()}>
            Simpan
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function Isi() {
  const id = useSearchParams().get("id");
  const { punya } = useSesi();
  const boleh = punya("ubah_produk");
  const [dialog, setDialog] = useState<"harga" | "satuan" | "ubah" | null>(null);

  const produk = useQuery({
    queryKey: ["produk", id],
    queryFn: () => api.get<Produk>(`/api/produk/${id}/`),
    enabled: !!id,
  });
  const batch = useDaftar<Batch>("/api/batch/", { produk: id ?? "", ada_sisa: 1 });
  const mutasi = useDaftar<Mutasi>("/api/mutasi/", { produk: id ?? "" });
  const harga = useDaftar<Harga>("/api/harga/", { produk: id ?? "" });

  const aktifkan = useAksi((aktif: boolean) => api.patch(`/api/produk/${id}/`, { aktif }), {
    sukses: "Status produk diperbarui.",
  });
  const unggah = useAksi(
    (f: File) => {
      const data = new FormData();
      data.append("foto", f);
      return api.post(`/api/produk/${id}/foto/`, data);
    },
    { sukses: "Foto diperbarui." },
  );

  const kolomBatch = useMemo<ColumnDef<Batch, unknown>[]>(
    () => [
      { header: "Batch", accessorKey: "nomor_batch" },
      { header: "Kedaluwarsa", cell: ({ row: { original: b } }) => tanggal(b.kedaluwarsa) },
      {
        header: "Sisa",
        meta: { kanan: true },
        cell: ({ row: { original: b } }) => b.stok_teks,
      },
      { header: "Status", cell: ({ row: { original: b } }) => <Status nilai={b.status} /> },
    ],
    [],
  );
  const kolomMutasi = useMemo<ColumnDef<Mutasi, unknown>[]>(
    () => [
      { header: "Waktu", cell: ({ row: { original: m } }) => waktu(m.dibuat_pada) },
      { header: "Jenis", accessorKey: "jenis_label" },
      { header: "Batch", accessorKey: "nomor_batch" },
      {
        header: "Jumlah",
        meta: { kanan: true },
        cell: ({ row: { original: m } }) => (m.jumlah > 0 ? `+${m.jumlah}` : m.jumlah),
      },
      { header: "Sisa", meta: { kanan: true }, accessorKey: "sisa_sesudah" },
      { header: "Referensi", accessorKey: "referensi" },
      { header: "Oleh", accessorKey: "dibuat_oleh_nama" },
    ],
    [],
  );
  const kolomHarga = useMemo<ColumnDef<Harga, unknown>[]>(
    () => [
      { header: "Satuan", accessorKey: "satuan_nama" },
      { header: "Harga", meta: { kanan: true }, cell: ({ row }) => rupiah(row.original.harga) },
      { header: "Berlaku mulai", cell: ({ row }) => tanggal(row.original.berlaku_mulai) },
      { header: "Oleh", accessorKey: "dibuat_oleh_nama" },
    ],
    [],
  );

  if (produk.isLoading) return <Skeleton className="h-64 w-full" />;
  if (produk.error || !produk.data) return <PesanGalat galat={produk.error} />;
  const p = produk.data;

  return (
    <Halaman
      judul={p.nama}
      keterangan={`${p.sku} · ${p.kategori_nama}`}
      aksi={
        boleh && (
          <>
            <Button variant="outline" onClick={() => setDialog("ubah")}>
              Ubah produk
            </Button>
            <Button variant="outline" onClick={() => setDialog("satuan")}>
              Tambah satuan
            </Button>
            <Button onClick={() => setDialog("harga")}>Ubah harga</Button>
          </>
        )
      }
    >
      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Ringkasan</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {p.punya_foto && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={`/api/produk/${p.id}/foto/`}
                alt={p.nama}
                className="max-h-40 rounded object-contain"
              />
            )}
            <div className="flex justify-between">
              <span>Stok tersedia</span>
              <strong className="tabular-nums">{p.stok_teks}</strong>
            </div>
            <div className="flex justify-between">
              <span>Stok kedaluwarsa</span>
              <span className="tabular-nums">{p.stok_kedaluwarsa} botol</span>
            </div>
            <div className="flex justify-between">
              <span>Kedaluwarsa terdekat</span>
              <span>{tanggal(p.kedaluwarsa_terdekat)}</span>
            </div>
            <div className="flex justify-between">
              <span>Status</span>
              {p.aktif ? <Status nilai={p.status_stok} /> : <Status nilai="nonaktif" />}
            </div>
            {boleh && (
              <div className="space-y-2 border-t pt-3">
                <Medan label="Ganti foto" bantuan="JPG atau PNG, maksimal 2 MB.">
                  <Input
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) unggah.mutate(f);
                    }}
                  />
                </Medan>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => aktifkan.mutate(!p.aktif)}
                  disabled={aktifkan.isPending}
                >
                  {p.aktif ? "Nonaktifkan produk" : "Aktifkan produk"}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Satuan dan harga berlaku</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="divide-y text-sm">
              {p.satuan.map((s) => (
                <li key={s.id} className="flex justify-between py-2">
                  <span>
                    {s.nama} ({s.isi_botol} botol)
                  </span>
                  <span className="tabular-nums">{s.harga ? rupiah(s.harga) : "Belum ada"}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      <section className="space-y-2">
        <h2 className="font-medium">Stok per batch</h2>
        <TabelData
          kolom={kolomBatch}
          data={batch.data?.results}
          memuat={batch.isLoading}
          jumlah={batch.data?.count}
          halaman={batch.halaman}
          ubahHalaman={batch.setHalaman}
          kosong="Tidak ada stok."
        />
      </section>
      <section className="space-y-2">
        <h2 className="font-medium">Riwayat keluar-masuk</h2>
        <TabelData
          kolom={kolomMutasi}
          data={mutasi.data?.results}
          memuat={mutasi.isLoading}
          jumlah={mutasi.data?.count}
          halaman={mutasi.halaman}
          ubahHalaman={mutasi.setHalaman}
        />
      </section>
      <section className="space-y-2">
        <h2 className="font-medium">Riwayat harga</h2>
        <TabelData
          kolom={kolomHarga}
          data={harga.data?.results}
          memuat={harga.isLoading}
          jumlah={harga.data?.count}
          halaman={harga.halaman}
          ubahHalaman={harga.setHalaman}
        />
      </section>

      <DialogHarga produk={p} buka={dialog === "harga"} ubah={(b) => setDialog(b ? "harga" : null)} />
      <DialogSatuan
        produk={p}
        buka={dialog === "satuan"}
        ubah={(b) => setDialog(b ? "satuan" : null)}
      />
      <DialogUbah produk={p} buka={dialog === "ubah"} ubah={(b) => setDialog(b ? "ubah" : null)} />
    </Halaman>
  );
}

export default function HalamanDetailProduk() {
  return (
    <WajibIzin izin="lihat_produk">
      <Bungkus>
        <Isi />
      </Bungkus>
    </WajibIzin>
  );
}
