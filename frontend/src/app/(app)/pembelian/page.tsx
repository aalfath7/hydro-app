"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { FileText } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";

import {
  Bungkus,
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
import { Input } from "@/components/ui/input";
import { rupiah, waktu } from "@/lib/format";
import { useDaftar, useTunda } from "@/lib/kait";
import type { Transaksi } from "@/lib/tipe";

function Isi() {
  const statusAwal = useSearchParams().get("status") ?? "";
  const [q, setQ] = useState("");
  const [dari, setDari] = useState("");
  const [sampai, setSampai] = useState("");
  const [bayar, setBayar] = useState("");
  const [status, setStatus] = useState(statusAwal);
  const qTunda = useTunda(q);
  const daftar = useDaftar<Transaksi>("/api/transaksi/", {
    q: qTunda,
    dari,
    sampai,
    status_bayar: bayar,
    status,
  });

  const kolom = useMemo<ColumnDef<Transaksi, unknown>[]>(
    () => [
      {
        header: "Nota",
        cell: ({ row: { original: t } }) => (
          <Link href={`/pembelian/detail?id=${t.id}`} className="text-primary font-medium">
            {t.nomor}
          </Link>
        ),
      },
      { header: "Tanggal", cell: ({ row }) => waktu(row.original.tanggal) },
      { header: "Pelanggan", accessorKey: "pelanggan_nama" },
      { header: "Total", meta: { kanan: true }, cell: ({ row }) => rupiah(row.original.total) },
      {
        header: "Sisa",
        meta: { kanan: true },
        cell: ({ row: { original: t } }) =>
          t.status === "dibatalkan" ? "-" : rupiah(t.sisa_tagihan),
      },
      {
        header: "Status",
        cell: ({ row: { original: t } }) => (
          <div className="flex flex-wrap gap-1">
            <Status nilai={t.status_bayar} />
            {t.status === "menunggu_batal" && <Status nilai="menunggu_batal" />}
          </div>
        ),
      },
      {
        id: "nota",
        header: "",
        meta: { kanan: true },
        cell: ({ row: { original: t } }) => (
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label={`Cetak nota ${t.nomor}`}
            render={<a href={`/api/transaksi/${t.id}/nota/`} target="_blank" rel="noreferrer" />}
            nativeButton={false}
          >
            <FileText />
          </Button>
        ),
      },
    ],
    [],
  );

  return (
    <Halaman judul="Riwayat pembelian">
      <Filter>
        <Cari nilai={q} ubah={setQ} placeholder="Cari nota atau pelanggan" />
        <Medan label="Dari" className="w-40">
          <Input type="date" value={dari} onChange={(e) => setDari(e.target.value)} />
        </Medan>
        <Medan label="Sampai" className="w-40">
          <Input type="date" value={sampai} onChange={(e) => setSampai(e.target.value)} />
        </Medan>
        <Medan label="Status bayar" className="w-40">
          <Pilih value={bayar} onChange={(e) => setBayar(e.target.value)}>
            <option value="">Semua</option>
            <option value="lunas">Lunas</option>
            <option value="belum_lunas">Belum lunas</option>
            <option value="jatuh_tempo">Jatuh tempo</option>
          </Pilih>
        </Medan>
        <Medan label="Status nota" className="w-44">
          <Pilih value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">Semua</option>
            <option value="selesai">Selesai</option>
            <option value="menunggu_batal">Menunggu pembatalan</option>
            <option value="dibatalkan">Dibatalkan</option>
          </Pilih>
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
          kosong="Belum ada transaksi."
        />
      )}
    </Halaman>
  );
}

export default function HalamanRiwayat() {
  return (
    <WajibIzin izin="kelola_transaksi">
      <Bungkus>
        <Isi />
      </Bungkus>
    </WajibIzin>
  );
}
