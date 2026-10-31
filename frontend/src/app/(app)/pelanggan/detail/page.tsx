"use client";

import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { Bungkus, Halaman, PesanGalat, TabelData, WajibIzin } from "@/components/bagian";
import { DialogPelanggan } from "@/components/dialog-pelanggan";
import { KOLOM_TAGIHAN } from "@/components/kolom-transaksi";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { rupiah } from "@/lib/format";
import { useAksi, useDaftar } from "@/lib/kait";
import type { Pelanggan, Transaksi } from "@/lib/tipe";

function Isi() {
  const id = useSearchParams().get("id");
  const [buka, setBuka] = useState(false);
  const q = useQuery({
    queryKey: ["pelanggan", id],
    queryFn: () => api.get<Pelanggan>(`/api/pelanggan/${id}/`),
    enabled: !!id,
  });
  const riwayat = useDaftar<Transaksi>("/api/transaksi/", { pelanggan: id ?? "" });
  const aktifkan = useAksi((aktif: boolean) => api.patch(`/api/pelanggan/${id}/`, { aktif }), {
    sukses: "Status pelanggan diperbarui.",
  });

  if (q.isLoading) return <Skeleton className="h-64 w-full" />;
  if (q.error || !q.data) return <PesanGalat galat={q.error} />;
  const p = q.data;

  return (
    <Halaman
      judul={p.nama}
      aksi={
        <>
          <Button variant="outline" onClick={() => aktifkan.mutate(!p.aktif)}>
            {p.aktif ? "Nonaktifkan" : "Aktifkan"}
          </Button>
          <Button onClick={() => setBuka(true)}>Ubah</Button>
        </>
      }
    >
      <Card>
        <CardContent className="grid gap-3 text-sm sm:grid-cols-3">
          <div>
            <div className="text-muted-foreground">Telepon</div>
            {p.telepon || "-"}
          </div>
          <div>
            <div className="text-muted-foreground">Alamat</div>
            {p.alamat || "-"}
          </div>
          <div>
            <div className="text-muted-foreground">Piutang</div>
            <strong className="tabular-nums">{rupiah(p.total_piutang)}</strong>
          </div>
        </CardContent>
      </Card>
      <section className="space-y-2">
        <h2 className="font-medium">Riwayat pembelian</h2>
        <TabelData
          kolom={KOLOM_TAGIHAN}
          data={riwayat.data?.results}
          memuat={riwayat.isLoading}
          jumlah={riwayat.data?.count}
          halaman={riwayat.halaman}
          ubahHalaman={riwayat.setHalaman}
          kosong="Belum ada pembelian."
        />
      </section>
      <DialogPelanggan buka={buka} ubah={setBuka} awal={p} />
    </Halaman>
  );
}

export default function HalamanDetailPelanggan() {
  return (
    <WajibIzin izin="kelola_transaksi">
      <Bungkus>
        <Isi />
      </Bungkus>
    </WajibIzin>
  );
}
