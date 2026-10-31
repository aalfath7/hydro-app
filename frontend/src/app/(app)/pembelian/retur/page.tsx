"use client";

import type { ColumnDef } from "@tanstack/react-table";
import Link from "next/link";
import { useMemo, useState } from "react";

import { Cari, Filter, Halaman, PesanGalat, TabelData, WajibIzin } from "@/components/bagian";
import { rupiah, waktu } from "@/lib/format";
import { useDaftar, useTunda } from "@/lib/kait";
import type { Retur } from "@/lib/tipe";

function Isi() {
  const [q, setQ] = useState("");
  const daftar = useDaftar<Retur>("/api/retur/", { q: useTunda(q) });
  const kolom = useMemo<ColumnDef<Retur, unknown>[]>(
    () => [
      { header: "Retur", accessorKey: "nomor" },
      { header: "Tanggal", cell: ({ row }) => waktu(row.original.tanggal) },
      {
        header: "Nota",
        cell: ({ row: { original: r } }) => (
          <Link href={`/pembelian/detail?id=${r.transaksi}`} className="text-primary">
            {r.transaksi_nomor}
          </Link>
        ),
      },
      { header: "Pelanggan", accessorKey: "pelanggan_nama" },
      { header: "Alasan", accessorKey: "alasan" },
      { header: "Nilai", meta: { kanan: true }, cell: ({ row }) => rupiah(row.original.total) },
      {
        header: "Potong piutang",
        meta: { kanan: true },
        cell: ({ row }) => rupiah(row.original.potong_piutang),
      },
      {
        header: "Uang kembali",
        meta: { kanan: true },
        cell: ({ row }) => rupiah(row.original.pengembalian_uang),
      },
    ],
    [],
  );
  return (
    <Halaman judul="Retur" keterangan="Retur baru dibuat dari halaman nota di Riwayat.">
      <Filter>
        <Cari nilai={q} ubah={setQ} placeholder="Cari retur, nota, pelanggan" />
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
          kosong="Belum ada retur."
        />
      )}
    </Halaman>
  );
}

export default function HalamanRetur() {
  return (
    <WajibIzin izin="kelola_transaksi">
      <Isi />
    </WajibIzin>
  );
}
