"use client";

import type { ColumnDef } from "@tanstack/react-table";
import Link from "next/link";
import { useMemo, useState } from "react";

import { Cari, Filter, Halaman, PesanGalat, Pilih, TabelData, WajibIzin } from "@/components/bagian";
import { Status } from "@/components/status";
import { tanggal } from "@/lib/format";
import { useDaftar, useTunda } from "@/lib/kait";
import type { Produk } from "@/lib/tipe";

function Isi() {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const daftar = useDaftar<Produk>("/api/produk/", { q: useTunda(q), status, aktif: 1 });
  const kolom = useMemo<ColumnDef<Produk, unknown>[]>(
    () => [
      {
        header: "Produk",
        cell: ({ row: { original: p } }) => (
          <Link href={`/produk/detail?id=${p.id}`} className="text-primary font-medium">
            {p.nama}
          </Link>
        ),
      },
      { header: "SKU", accessorKey: "sku" },
      { header: "Stok", meta: { kanan: true }, cell: ({ row }) => row.original.stok_teks },
      {
        header: "Minimum (botol)",
        meta: { kanan: true },
        cell: ({ row }) => row.original.stok_minimum ?? 0,
      },
      {
        header: "Kedaluwarsa (botol)",
        meta: { kanan: true },
        cell: ({ row }) => row.original.stok_kedaluwarsa,
      },
      {
        header: "Kedaluwarsa terdekat",
        cell: ({ row }) => tanggal(row.original.kedaluwarsa_terdekat),
      },
      { header: "Status", cell: ({ row }) => <Status nilai={row.original.status_stok} /> },
    ],
    [],
  );
  return (
    <Halaman judul="Stok terkini" keterangan="Stok tersedia tidak menghitung batch kedaluwarsa.">
      <Filter>
        <Cari nilai={q} ubah={setQ} placeholder="Cari nama atau SKU" />
        <Pilih
          aria-label="Status stok"
          className="w-40"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="">Semua status</option>
          <option value="aman">Aman</option>
          <option value="menipis">Menipis</option>
          <option value="habis">Habis</option>
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
        />
      )}
    </Halaman>
  );
}

export default function HalamanStok() {
  return (
    <WajibIzin izin="kelola_stok">
      <Isi />
    </WajibIzin>
  );
}
