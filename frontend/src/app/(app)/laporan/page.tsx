"use client";

import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Download } from "lucide-react";
import { useMemo, useState } from "react";

import {
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
import { api, denganParam } from "@/lib/api";
import { angka, hariIni, rupiah, tanggal } from "@/lib/format";
import type { BarisPenjualan, BarisPiutang, BarisStok, BarisTerlaris } from "@/lib/tipe";
import { cn } from "@/lib/utils";

const TAB = [
  { id: "penjualan", label: "Penjualan", url: "/api/laporan/penjualan/", periode: true },
  { id: "terlaris", label: "Produk terlaris", url: "/api/laporan/produk-terlaris/", periode: true },
  { id: "stok", label: "Stok", url: "/api/laporan/stok/", periode: false },
  { id: "piutang", label: "Piutang", url: "/api/laporan/piutang/", periode: false },
] as const;

function Tabel<T>({
  url,
  param,
  kolom,
}: {
  url: string;
  param: Record<string, string>;
  kolom: ColumnDef<T, unknown>[];
}) {
  const q = useQuery({
    queryKey: [url, param],
    queryFn: () => api.get<T[]>(url, param),
  });
  if (q.error) return <PesanGalat galat={q.error} />;
  return <TabelData kolom={kolom} data={q.data} memuat={q.isLoading} kosong="Tidak ada data." />;
}

function Isi() {
  const [tab, setTab] = useState<(typeof TAB)[number]["id"]>("penjualan");
  const [dari, setDari] = useState(`${hariIni().slice(0, 8)}01`);
  const [sampai, setSampai] = useState(hariIni());
  const [per, setPer] = useState("hari");
  const aktif = TAB.find((t) => t.id === tab)!;
  const param: Record<string, string> = aktif.periode
    ? { dari, sampai, ...(tab === "penjualan" ? { per } : {}) }
    : {};

  const kolomPenjualan = useMemo<ColumnDef<BarisPenjualan, unknown>[]>(
    () => [
      { header: "Periode", cell: ({ row }) => tanggal(row.original.periode) },
      {
        header: "Transaksi",
        meta: { kanan: true },
        cell: ({ row }) => angka(row.original.jumlah_transaksi),
      },
      { header: "Penjualan", meta: { kanan: true }, cell: ({ row }) => rupiah(row.original.bruto) },
      { header: "Retur", meta: { kanan: true }, cell: ({ row }) => rupiah(row.original.retur) },
      { header: "Neto", meta: { kanan: true }, cell: ({ row }) => rupiah(row.original.neto) },
    ],
    [],
  );
  const kolomTerlaris = useMemo<ColumnDef<BarisTerlaris, unknown>[]>(
    () => [
      { header: "SKU", accessorKey: "sku" },
      { header: "Produk", accessorKey: "nama" },
      {
        header: "Botol terjual",
        meta: { kanan: true },
        cell: ({ row }) => angka(row.original.botol_terjual),
      },
      { header: "Nilai", meta: { kanan: true }, cell: ({ row }) => rupiah(row.original.nilai) },
    ],
    [],
  );
  const kolomStok = useMemo<ColumnDef<BarisStok, unknown>[]>(
    () => [
      { header: "SKU", accessorKey: "sku" },
      { header: "Produk", accessorKey: "nama" },
      { header: "Stok", meta: { kanan: true }, accessorKey: "stok_teks" },
      {
        header: "Minimum (botol)",
        meta: { kanan: true },
        cell: ({ row }) => angka(row.original.stok_minimum),
      },
      {
        header: "Kedaluwarsa (botol)",
        meta: { kanan: true },
        cell: ({ row }) => angka(row.original.stok_kedaluwarsa),
      },
      {
        header: "Kedaluwarsa terdekat",
        cell: ({ row }) => tanggal(row.original.kedaluwarsa_terdekat),
      },
      { header: "Status", cell: ({ row }) => <Status nilai={row.original.status} /> },
    ],
    [],
  );
  const kolomPiutang = useMemo<ColumnDef<BarisPiutang, unknown>[]>(
    () => [
      { header: "Nota", accessorKey: "nomor" },
      { header: "Pelanggan", accessorKey: "pelanggan" },
      { header: "Tanggal", cell: ({ row }) => tanggal(row.original.tanggal) },
      { header: "Jatuh tempo", cell: ({ row }) => tanggal(row.original.jatuh_tempo) },
      { header: "Total", meta: { kanan: true }, cell: ({ row }) => rupiah(row.original.total) },
      { header: "Sisa", meta: { kanan: true }, cell: ({ row }) => rupiah(row.original.sisa) },
      {
        header: "Terlambat (hari)",
        meta: { kanan: true },
        accessorKey: "terlambat_hari",
      },
    ],
    [],
  );

  return (
    <Halaman
      judul="Laporan"
      aksi={
        <>
          {(["xlsx", "pdf"] as const).map((f) => (
            <Button
              key={f}
              variant="outline"
              render={<a href={denganParam(aktif.url, { ...param, ekspor: f })} />}
              nativeButton={false}
            >
              <Download />
              {f === "xlsx" ? "Excel" : "PDF"}
            </Button>
          ))}
        </>
      }
    >
      <div role="tablist" className="flex flex-wrap gap-1 border-b">
        {TAB.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              "-mb-px border-b-2 border-transparent px-3 py-2 text-sm",
              tab === t.id && "border-primary text-primary font-medium",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>
      {aktif.periode && (
        <Filter>
          <Medan label="Dari" className="w-40">
            <Input type="date" value={dari} onChange={(e) => setDari(e.target.value)} />
          </Medan>
          <Medan label="Sampai" className="w-40">
            <Input type="date" value={sampai} onChange={(e) => setSampai(e.target.value)} />
          </Medan>
          {tab === "penjualan" && (
            <Medan label="Per" className="w-32">
              <Pilih value={per} onChange={(e) => setPer(e.target.value)}>
                <option value="hari">Hari</option>
                <option value="bulan">Bulan</option>
              </Pilih>
            </Medan>
          )}
        </Filter>
      )}
      {tab === "penjualan" && <Tabel url={aktif.url} param={param} kolom={kolomPenjualan} />}
      {tab === "terlaris" && <Tabel url={aktif.url} param={param} kolom={kolomTerlaris} />}
      {tab === "stok" && <Tabel url={aktif.url} param={param} kolom={kolomStok} />}
      {tab === "piutang" && <Tabel url={aktif.url} param={param} kolom={kolomPiutang} />}
    </Halaman>
  );
}

export default function HalamanLaporan() {
  return (
    <WajibIzin izin="lihat_laporan">
      <Isi />
    </WajibIzin>
  );
}
