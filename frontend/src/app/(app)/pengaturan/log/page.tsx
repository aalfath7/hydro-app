"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { useMemo, useState } from "react";

import { Cari, Filter, Halaman, Medan, PesanGalat, TabelData, WajibIzin } from "@/components/bagian";
import { Input } from "@/components/ui/input";
import { waktu } from "@/lib/format";
import { useDaftar, useTunda } from "@/lib/kait";
import type { LogAktivitas } from "@/lib/tipe";

function ringkasPerubahan(perubahan: unknown): string {
  if (!perubahan || typeof perubahan !== "object") return "";
  return Object.entries(perubahan as Record<string, unknown>)
    .slice(0, 4)
    .map(([kolom, nilai]) =>
      Array.isArray(nilai) ? `${kolom}: ${nilai[0]} → ${nilai[1]}` : kolom,
    )
    .join("; ");
}

function Isi() {
  const [q, setQ] = useState("");
  const [dari, setDari] = useState("");
  const [sampai, setSampai] = useState("");
  const daftar = useDaftar<LogAktivitas>("/api/log-aktivitas/", {
    q: useTunda(q),
    dari,
    sampai,
  });
  const kolom = useMemo<ColumnDef<LogAktivitas, unknown>[]>(
    () => [
      { header: "Waktu", cell: ({ row }) => waktu(row.original.waktu) },
      { header: "Pengguna", cell: ({ row }) => row.original.pengguna ?? "Sistem" },
      { header: "Aksi", accessorKey: "aksi" },
      { header: "Data", accessorKey: "objek" },
      { header: "Keterangan", accessorKey: "keterangan" },
      {
        header: "Perubahan",
        cell: ({ row }) => (
          <span className="block max-w-md truncate" title={ringkasPerubahan(row.original.perubahan)}>
            {ringkasPerubahan(row.original.perubahan)}
          </span>
        ),
      },
    ],
    [],
  );
  return (
    <Halaman judul="Log aktivitas">
      <Filter>
        <Cari nilai={q} ubah={setQ} placeholder="Cari pengguna atau data" />
        <Medan label="Dari" className="w-40">
          <Input type="date" value={dari} onChange={(e) => setDari(e.target.value)} />
        </Medan>
        <Medan label="Sampai" className="w-40">
          <Input type="date" value={sampai} onChange={(e) => setSampai(e.target.value)} />
        </Medan>
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

export default function HalamanLog() {
  return (
    <WajibIzin izin="kelola_pengguna">
      <Isi />
    </WajibIzin>
  );
}
