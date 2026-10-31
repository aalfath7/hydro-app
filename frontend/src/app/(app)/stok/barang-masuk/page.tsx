"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Plus } from "lucide-react";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Halaman, Medan, PesanGalat, Pilih, TabelData, WajibIzin } from "@/components/bagian";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { hariIni, tanggal, waktu } from "@/lib/format";
import { useAksi, useDaftar } from "@/lib/kait";
import type { BarangMasuk, Halaman as Hal, Produk } from "@/lib/tipe";

const skema = z.object({
  produk: z.string().min(1, "Pilih produk"),
  satuan: z.string().min(1, "Pilih satuan"),
  jumlah: z.string().regex(/^[1-9]\d*$/, "Isi jumlah"),
  nomor_batch: z.string().min(1, "Nomor batch wajib diisi"),
  kedaluwarsa: z.string().min(1, "Tanggal wajib diisi"),
  tanggal: z.string().min(1, "Tanggal wajib diisi"),
  sumber: z.string(),
});
type Form = z.infer<typeof skema>;

function DialogMasuk({ buka, ubah }: { buka: boolean; ubah: (b: boolean) => void }) {
  const produk = useQuery({
    queryKey: ["produk-aktif"],
    queryFn: () => api.get<Hal<Produk>>("/api/produk/", { aktif: 1, ukuran: 200 }),
  });
  const form = useForm<Form>({
    resolver: zodResolver(skema),
    defaultValues: {
      produk: "",
      satuan: "",
      jumlah: "",
      nomor_batch: "",
      kedaluwarsa: "",
      tanggal: hariIni(),
      sumber: "",
    },
  });
  const idProduk = form.watch("produk");
  const dipilih = produk.data?.results.find((p) => String(p.id) === idProduk);
  const simpan = useAksi(
    (d: Form) =>
      api.post("/api/barang-masuk/", {
        ...d,
        produk: Number(d.produk),
        satuan: Number(d.satuan),
        jumlah: Number(d.jumlah),
      }),
    {
      sukses: "Barang masuk dicatat.",
      setelah: () => {
        form.reset();
        ubah(false);
      },
    },
  );
  const g = form.formState.errors;
  return (
    <Dialog open={buka} onOpenChange={ubah}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Barang masuk</DialogTitle>
        </DialogHeader>
        <form
          id="form-masuk"
          className="grid gap-3 sm:grid-cols-2"
          onSubmit={form.handleSubmit((d) => simpan.mutate(d))}
        >
          <Medan label="Produk" galat={g.produk?.message} className="sm:col-span-2">
            <Pilih {...form.register("produk")}>
              <option value="">Pilih produk</option>
              {produk.data?.results.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.nama} ({p.sku})
                </option>
              ))}
            </Pilih>
          </Medan>
          <Medan label="Satuan" galat={g.satuan?.message}>
            <Pilih {...form.register("satuan")}>
              <option value="">Pilih satuan</option>
              {dipilih?.satuan.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.nama} ({s.isi_botol} botol)
                </option>
              ))}
            </Pilih>
          </Medan>
          <Medan label="Jumlah" galat={g.jumlah?.message}>
            <Input inputMode="numeric" {...form.register("jumlah")} />
          </Medan>
          <Medan label="Nomor batch" galat={g.nomor_batch?.message}>
            <Input {...form.register("nomor_batch")} />
          </Medan>
          <Medan label="Kedaluwarsa" galat={g.kedaluwarsa?.message}>
            <Input type="date" {...form.register("kedaluwarsa")} />
          </Medan>
          <Medan label="Tanggal masuk" galat={g.tanggal?.message}>
            <Input type="date" {...form.register("tanggal")} />
          </Medan>
          <Medan label="Sumber">
            <Input placeholder="Produksi atau pemasok" {...form.register("sumber")} />
          </Medan>
        </form>
        <DialogFooter>
          <Button type="submit" form="form-masuk" disabled={simpan.isPending}>
            Simpan
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function Isi() {
  const [buka, setBuka] = useState(false);
  const daftar = useDaftar<BarangMasuk>("/api/barang-masuk/");
  const kolom = useMemo<ColumnDef<BarangMasuk, unknown>[]>(
    () => [
      { header: "Nomor", accessorKey: "nomor" },
      { header: "Tanggal", cell: ({ row }) => tanggal(row.original.tanggal) },
      { header: "Produk", accessorKey: "produk_nama" },
      { header: "Batch", accessorKey: "nomor_batch" },
      {
        header: "Jumlah",
        meta: { kanan: true },
        cell: ({ row: { original: b } }) => `${b.jumlah} ${b.satuan_nama}`,
      },
      { header: "Kedaluwarsa", cell: ({ row }) => tanggal(row.original.kedaluwarsa) },
      { header: "Sumber", accessorKey: "sumber" },
      { header: "Dicatat", cell: ({ row }) => waktu(row.original.dibuat_pada) },
      { header: "Oleh", accessorKey: "dibuat_oleh_nama" },
    ],
    [],
  );
  return (
    <Halaman
      judul="Barang masuk"
      aksi={
        <Button onClick={() => setBuka(true)}>
          <Plus />
          Barang masuk
        </Button>
      }
    >
      {daftar.error ? (
        <PesanGalat galat={daftar.error} />
      ) : (
        <TabelData
          kolom={kolom}
          data={daftar.data?.results}
          memuat={daftar.isLoading}
          jumlah={daftar.data?.count}
          halaman={daftar.halaman}
          ubahHalaman={daftar.setHalaman}
          kosong="Belum ada barang masuk."
        />
      )}
      <DialogMasuk buka={buka} ubah={setBuka} />
    </Halaman>
  );
}

export default function HalamanBarangMasuk() {
  return (
    <WajibIzin izin="kelola_stok">
      <Isi />
    </WajibIzin>
  );
}
