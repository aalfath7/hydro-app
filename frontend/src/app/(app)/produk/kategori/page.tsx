"use client";

import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { useMemo, useState } from "react";

import { Halaman, PesanGalat, TabelData, WajibIzin } from "@/components/bagian";
import { Status } from "@/components/status";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { useAksi, useSesi } from "@/lib/kait";
import type { Kategori } from "@/lib/tipe";

function Isi() {
  const { punya } = useSesi();
  const boleh = punya("ubah_produk");
  const [nama, setNama] = useState("");
  const daftar = useQuery({
    queryKey: ["kategori"],
    queryFn: () => api.get<Kategori[]>("/api/kategori/"),
  });
  const tambah = useAksi((n: string) => api.post("/api/kategori/", { nama: n }), {
    sukses: "Kategori ditambahkan.",
    setelah: () => setNama(""),
  });
  const ubah = useAksi((k: Kategori) =>
    api.patch(`/api/kategori/${k.id}/`, { aktif: !k.aktif }),
  );

  const kolom = useMemo<ColumnDef<Kategori, unknown>[]>(
    () => [
      { header: "Nama", accessorKey: "nama" },
      {
        header: "Status",
        cell: ({ row: { original: k } }) => <Status nilai={k.aktif ? "aktif" : "nonaktif"} />,
      },
      {
        id: "aksi",
        header: "",
        meta: { kanan: true },
        cell: ({ row: { original: k } }) =>
          boleh && (
            <Button variant="outline" size="sm" onClick={() => ubah.mutate(k)}>
              {k.aktif ? "Nonaktifkan" : "Aktifkan"}
            </Button>
          ),
      },
    ],
    [boleh, ubah],
  );

  return (
    <Halaman judul="Kategori">
      {boleh && (
        <form
          className="flex max-w-md gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (nama.trim()) tambah.mutate(nama.trim());
          }}
        >
          <Input
            aria-label="Nama kategori"
            placeholder="Nama kategori baru"
            value={nama}
            onChange={(e) => setNama(e.target.value)}
          />
          <Button type="submit" disabled={tambah.isPending || !nama.trim()}>
            Tambah
          </Button>
        </form>
      )}
      {daftar.error ? (
        <PesanGalat galat={daftar.error} />
      ) : (
        <TabelData kolom={kolom} data={daftar.data} memuat={daftar.isLoading} />
      )}
    </Halaman>
  );
}

export default function HalamanKategori() {
  return (
    <WajibIzin izin="lihat_produk">
      <Isi />
    </WajibIzin>
  );
}
