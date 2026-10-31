"use client";

import { useQuery } from "@tanstack/react-query";
import { Check, Minus } from "lucide-react";

import { Halaman, PesanGalat, WajibIzin } from "@/components/bagian";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api";
import type { Peran } from "@/lib/tipe";

const IZIN: [string, string][] = [
  ["lihat_produk", "Lihat produk"],
  ["kelola_transaksi", "Kelola transaksi dan pelanggan"],
  ["kelola_stok", "Kelola stok dan barang masuk"],
  ["ubah_produk", "Ubah produk dan harga"],
  ["setujui_pembatalan", "Setujui pembatalan transaksi"],
  ["setujui_opname", "Setujui stok opname"],
  ["lihat_laporan", "Lihat laporan keuangan"],
  ["kelola_pengguna", "Kelola pengguna"],
];

function Isi() {
  const q = useQuery({ queryKey: ["peran"], queryFn: () => api.get<Peran[]>("/api/peran/") });
  if (q.isLoading) return <Skeleton className="h-64 w-full" />;
  if (q.error || !q.data) return <PesanGalat galat={q.error} />;
  return (
    <Halaman judul="Peran" keterangan="Hak akses tiap peran ditetapkan di server.">
      <div className="bg-card rounded-xl border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Izin</TableHead>
              {q.data.map((p) => (
                <TableHead key={p.kode}>{p.nama}</TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {IZIN.map(([kode, label]) => (
              <TableRow key={kode}>
                <TableCell>{label}</TableCell>
                {q.data.map((p) => (
                  <TableCell key={p.kode}>
                    {p.izin.includes(kode) ? (
                      <span className="inline-flex items-center gap-1">
                        <Check className="text-primary size-4" /> Ya
                      </span>
                    ) : (
                      <span className="text-muted-foreground inline-flex items-center gap-1">
                        <Minus className="size-4" /> Tidak
                      </span>
                    )}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </Halaman>
  );
}

export default function HalamanPeran() {
  return (
    <WajibIzin izin="kelola_pengguna">
      <Isi />
    </WajibIzin>
  );
}
