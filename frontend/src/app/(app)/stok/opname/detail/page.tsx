"use client";

import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import type { ColumnDef } from "@tanstack/react-table";
import { useMemo } from "react";

import { Bungkus, Halaman, PesanGalat, TabelData, WajibIzin } from "@/components/bagian";
import { Status } from "@/components/status";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { tanggal, waktu } from "@/lib/format";
import { useAksi, useSesi } from "@/lib/kait";
import type { Opname } from "@/lib/tipe";

type Item = Opname["items"][number];

function Isi() {
  const id = useSearchParams().get("id");
  const { punya } = useSesi();
  const q = useQuery({
    queryKey: ["opname", id],
    queryFn: () => api.get<Opname>(`/api/opname/${id}/`),
    enabled: !!id,
  });
  const setujui = useAksi(() => api.post(`/api/opname/${id}/setujui/`), {
    sukses: "Selisih dicatat sebagai penyesuaian.",
  });
  const tolak = useAksi(() => api.post(`/api/opname/${id}/tolak/`), {
    sukses: "Opname ditolak.",
  });
  const kolom = useMemo<ColumnDef<Item, unknown>[]>(
    () => [
      { header: "Produk", accessorKey: "produk_nama" },
      { header: "Batch", accessorKey: "nomor_batch" },
      { header: "Kedaluwarsa", cell: ({ row }) => tanggal(row.original.kedaluwarsa) },
      { header: "Tercatat", meta: { kanan: true }, accessorKey: "stok_tercatat" },
      { header: "Fisik", meta: { kanan: true }, accessorKey: "stok_fisik" },
      {
        header: "Selisih",
        meta: { kanan: true },
        cell: ({ row: { original: i } }) => (i.selisih > 0 ? `+${i.selisih}` : i.selisih),
      },
    ],
    [],
  );

  if (q.isLoading) return <Skeleton className="h-64 w-full" />;
  if (q.error || !q.data) return <PesanGalat galat={q.error} />;
  const o = q.data;

  return (
    <Halaman
      judul={`Opname ${o.nomor}`}
      keterangan={`${waktu(o.dibuat_pada)} · ${o.dibuat_oleh_nama}${o.catatan ? ` · ${o.catatan}` : ""}`}
      aksi={
        <>
          <Status nilai={o.status} />
          {o.status === "menunggu" && punya("setujui_opname") && (
            <>
              <Button
                variant="outline"
                disabled={tolak.isPending}
                onClick={() => tolak.mutate(undefined)}
              >
                Tolak
              </Button>
              <Button disabled={setujui.isPending} onClick={() => setujui.mutate(undefined)}>
                Setujui
              </Button>
            </>
          )}
        </>
      }
    >
      <TabelData kolom={kolom} data={o.items} />
      {o.diputuskan_oleh_nama && (
        <p className="text-muted-foreground text-sm">
          Diputuskan {o.diputuskan_oleh_nama}, {waktu(o.diputuskan_pada)}.
        </p>
      )}
    </Halaman>
  );
}

export default function HalamanDetailOpname() {
  return (
    <WajibIzin izin="kelola_stok">
      <Bungkus>
        <Isi />
      </Bungkus>
    </WajibIzin>
  );
}
