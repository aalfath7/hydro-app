"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Cari, Halaman, Medan, PesanGalat, WajibIzin } from "@/components/bagian";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import { tanggal } from "@/lib/format";
import { useAksi, useTunda } from "@/lib/kait";
import type { Batch, Halaman as Hal, Opname } from "@/lib/tipe";

function Isi() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [catatan, setCatatan] = useState("");
  const [fisik, setFisik] = useState<Record<number, string>>({});
  const qTunda = useTunda(q);
  const daftar = useQuery({
    queryKey: ["batch-opname", qTunda],
    queryFn: () =>
      api.get<Hal<Batch>>("/api/batch/", { ada_sisa: 1, ukuran: 200, q: qTunda }),
    placeholderData: keepPreviousData,
  });

  const items = Object.entries(fisik)
    .filter(([, v]) => v !== "")
    .map(([batch, v]) => ({ batch: Number(batch), stok_fisik: Number(v) }));

  const simpan = useAksi(() => api.post<Opname>("/api/opname/", { items, catatan }), {
    sukses: "Opname dikirim untuk disetujui.",
    setelah: (o) => router.push(`/stok/opname/detail?id=${o.id}`),
  });

  if (daftar.isLoading) return <Skeleton className="h-64 w-full" />;
  if (daftar.error) return <PesanGalat galat={daftar.error} />;
  const baris = daftar.data?.results;
  const jumlah = daftar.data?.count ?? 0;

  return (
    <Halaman
      judul="Opname baru"
      keterangan="Isi stok fisik pada batch yang dihitung, dalam botol."
      aksi={
        <Button disabled={!items.length || simpan.isPending} onClick={() => simpan.mutate(undefined)}>
          Kirim {items.length ? `(${items.length} batch)` : ""}
        </Button>
      }
    >
      <div className="flex flex-wrap items-end gap-3">
        <Cari nilai={q} ubah={setQ} placeholder="Cari batch atau produk" />
        <Medan label="Catatan" className="min-w-64 flex-1">
          <Input value={catatan} onChange={(e) => setCatatan(e.target.value)} />
        </Medan>
      </div>
      {jumlah > (baris?.length ?? 0) && (
        <p className="text-muted-foreground text-sm">
          Menampilkan {baris?.length} dari {jumlah} batch. Persempit dengan pencarian.
        </p>
      )}
      <div className="bg-card rounded-xl border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Produk</TableHead>
              <TableHead>Batch</TableHead>
              <TableHead>Kedaluwarsa</TableHead>
              <TableHead className="text-right">Tercatat (botol)</TableHead>
              <TableHead className="w-32 text-right">Fisik (botol)</TableHead>
              <TableHead className="text-right">Selisih</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {baris?.map((b) => {
              const nilai = fisik[b.id] ?? "";
              const selisih = nilai === "" ? null : Number(nilai) - b.sisa;
              return (
                <TableRow key={b.id}>
                  <TableCell>{b.produk_nama}</TableCell>
                  <TableCell>{b.nomor_batch}</TableCell>
                  <TableCell>{tanggal(b.kedaluwarsa)}</TableCell>
                  <TableCell className="text-right tabular-nums">{b.sisa}</TableCell>
                  <TableCell>
                    <Input
                      aria-label={`Stok fisik ${b.nomor_batch}`}
                      inputMode="numeric"
                      className="text-right tabular-nums"
                      value={nilai}
                      onChange={(e) =>
                        setFisik((f) => ({ ...f, [b.id]: e.target.value.replace(/\D/g, "") }))
                      }
                    />
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {selisih === null ? "-" : selisih > 0 ? `+${selisih}` : selisih}
                  </TableCell>
                </TableRow>
              );
            })}
            {baris?.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-muted-foreground h-20 text-center">
                  Tidak ada batch.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </Halaman>
  );
}

export default function HalamanOpnameBaru() {
  return (
    <WajibIzin izin="kelola_stok">
      <Isi />
    </WajibIzin>
  );
}
