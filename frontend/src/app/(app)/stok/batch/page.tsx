"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { useMemo, useState } from "react";

import {
  Cari,
  Filter,
  Halaman,
  Medan,
  PesanGalat,
  Pilih,
  TabelData,
  WajibIzin,
} from "@/components/bagian";
import { Status } from "@/components/status";
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
import { tanggal } from "@/lib/format";
import { useAksi, useDaftar, useTunda } from "@/lib/kait";
import type { Batch } from "@/lib/tipe";

function DialogKurangi({ batch, tutup }: { batch: Batch | null; tutup: () => void }) {
  const [jenis, setJenis] = useState("rusak");
  const [jumlah, setJumlah] = useState("");
  const [catatan, setCatatan] = useState("");
  const simpan = useAksi(
    () =>
      api.post(`/api/batch/${batch?.id}/kurangi/`, { jenis, jumlah: Number(jumlah), catatan }),
    {
      sukses: "Pengurangan stok dicatat.",
      setelah: () => {
        setJumlah("");
        setCatatan("");
        tutup();
      },
    },
  );
  return (
    <Dialog open={!!batch} onOpenChange={(b) => !b && tutup()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Kurangi stok batch {batch?.nomor_batch}</DialogTitle>
        </DialogHeader>
        <div className="grid gap-3">
          <p className="text-sm">
            {batch?.produk_nama}, sisa {batch?.sisa} botol.
          </p>
          <Medan label="Jenis">
            <Pilih value={jenis} onChange={(e) => setJenis(e.target.value)}>
              <option value="rusak">Rusak</option>
              <option value="kedaluwarsa">Kedaluwarsa</option>
            </Pilih>
          </Medan>
          <Medan label="Jumlah (botol)">
            <Input
              inputMode="numeric"
              value={jumlah}
              onChange={(e) => setJumlah(e.target.value.replace(/\D/g, ""))}
            />
          </Medan>
          <Medan label="Catatan">
            <Input value={catatan} onChange={(e) => setCatatan(e.target.value)} />
          </Medan>
        </div>
        <DialogFooter>
          <Button
            disabled={!jumlah || !catatan.trim() || simpan.isPending}
            onClick={() => simpan.mutate(undefined)}
          >
            Simpan
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function Isi() {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [dipilih, setDipilih] = useState<Batch | null>(null);
  const daftar = useDaftar<Batch>("/api/batch/", { q: useTunda(q), status, ada_sisa: 1 });
  const kolom = useMemo<ColumnDef<Batch, unknown>[]>(
    () => [
      { header: "Batch", accessorKey: "nomor_batch" },
      { header: "Produk", accessorKey: "produk_nama" },
      { header: "Kedaluwarsa", cell: ({ row }) => tanggal(row.original.kedaluwarsa) },
      { header: "Sisa", meta: { kanan: true }, cell: ({ row }) => row.original.stok_teks },
      { header: "Status", cell: ({ row }) => <Status nilai={row.original.status} /> },
      {
        id: "aksi",
        header: "",
        meta: { kanan: true },
        cell: ({ row: { original: b } }) => (
          <Button variant="outline" size="sm" onClick={() => setDipilih(b)}>
            Kurangi
          </Button>
        ),
      },
    ],
    [],
  );
  return (
    <Halaman judul="Batch" keterangan="Urut dari kedaluwarsa terdekat, sama seperti urutan keluar.">
      <Filter>
        <Cari nilai={q} ubah={setQ} placeholder="Cari batch atau produk" />
        <Pilih
          aria-label="Status batch"
          className="w-44"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="">Semua batch</option>
          <option value="kedaluwarsa">Sudah kedaluwarsa</option>
        </Pilih>
      </Filter>
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
          kosong="Tidak ada batch dengan stok."
        />
      )}
      <DialogKurangi batch={dipilih} tutup={() => setDipilih(null)} />
    </Halaman>
  );
}

export default function HalamanBatch() {
  return (
    <WajibIzin izin="kelola_stok">
      <Isi />
    </WajibIzin>
  );
}
