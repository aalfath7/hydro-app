"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { Plus } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { Cari, Filter, Halaman, PesanGalat, TabelData, WajibIzin } from "@/components/bagian";
import { DialogPelanggan } from "@/components/dialog-pelanggan";
import { Status } from "@/components/status";
import { Button } from "@/components/ui/button";
import { rupiah } from "@/lib/format";
import { useDaftar, useTunda } from "@/lib/kait";
import type { Pelanggan } from "@/lib/tipe";

function Isi() {
  const [q, setQ] = useState("");
  const [buka, setBuka] = useState(false);
  const daftar = useDaftar<Pelanggan>("/api/pelanggan/", { q: useTunda(q) });
  const kolom = useMemo<ColumnDef<Pelanggan, unknown>[]>(
    () => [
      {
        header: "Nama",
        cell: ({ row: { original: p } }) => (
          <Link href={`/pelanggan/detail?id=${p.id}`} className="text-primary font-medium">
            {p.nama}
          </Link>
        ),
      },
      { header: "Telepon", accessorKey: "telepon" },
      { header: "Alamat", accessorKey: "alamat" },
      {
        header: "Piutang",
        meta: { kanan: true },
        cell: ({ row }) => rupiah(row.original.total_piutang),
      },
      {
        header: "Status",
        cell: ({ row }) => <Status nilai={row.original.aktif ? "aktif" : "nonaktif"} />,
      },
    ],
    [],
  );
  return (
    <Halaman
      judul="Daftar pelanggan"
      aksi={
        <Button onClick={() => setBuka(true)}>
          <Plus />
          Pelanggan baru
        </Button>
      }
    >
      <Filter>
        <Cari nilai={q} ubah={setQ} placeholder="Cari nama atau telepon" />
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
          kosong="Belum ada pelanggan."
        />
      )}
      <DialogPelanggan buka={buka} ubah={setBuka} />
    </Halaman>
  );
}

export default function HalamanPelanggan() {
  return (
    <WajibIzin izin="kelola_transaksi">
      <Isi />
    </WajibIzin>
  );
}
