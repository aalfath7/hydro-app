"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { Plus } from "lucide-react";
import Link from "next/link";
import { useMemo } from "react";

import { Halaman, PesanGalat, TabelData, WajibIzin } from "@/components/bagian";
import { Status } from "@/components/status";
import { Button } from "@/components/ui/button";
import { waktu } from "@/lib/format";
import { useDaftar } from "@/lib/kait";
import type { Opname } from "@/lib/tipe";

function Isi() {
  const daftar = useDaftar<Opname>("/api/opname/");
  const kolom = useMemo<ColumnDef<Opname, unknown>[]>(
    () => [
      {
        header: "Nomor",
        cell: ({ row: { original: o } }) => (
          <Link href={`/stok/opname/detail?id=${o.id}`} className="text-primary font-medium">
            {o.nomor}
          </Link>
        ),
      },
      { header: "Dibuat", cell: ({ row }) => waktu(row.original.dibuat_pada) },
      { header: "Oleh", accessorKey: "dibuat_oleh_nama" },
      {
        header: "Batch",
        meta: { kanan: true },
        cell: ({ row }) => row.original.items.length,
      },
      { header: "Status", cell: ({ row }) => <Status nilai={row.original.status} /> },
    ],
    [],
  );
  return (
    <Halaman
      judul="Stok opname"
      aksi={
        <Button render={<Link href="/stok/opname/baru" />} nativeButton={false}>
          <Plus />
          Opname baru
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
          kosong="Belum ada opname."
        />
      )}
    </Halaman>
  );
}

export default function HalamanOpname() {
  return (
    <WajibIzin izin="kelola_stok">
      <Isi />
    </WajibIzin>
  );
}
