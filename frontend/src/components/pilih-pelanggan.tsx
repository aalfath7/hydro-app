"use client";

import { Check, X } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { useTunda } from "@/lib/kait";
import type { Halaman, Pelanggan } from "@/lib/tipe";

export function PilihPelanggan({
  nilai,
  ubah,
}: {
  nilai: Pelanggan | null;
  ubah: (p: Pelanggan | null) => void;
}) {
  const [q, setQ] = useState("");
  const [fokus, setFokus] = useState(false);
  const qTunda = useTunda(q);
  const hasil = useQuery({
    queryKey: ["pelanggan-cari", qTunda],
    queryFn: () =>
      api.get<Halaman<Pelanggan>>("/api/pelanggan/", { q: qTunda, aktif: 1, ukuran: 8 }),
    enabled: fokus && !nilai,
  });

  if (nilai) {
    return (
      <div className="flex items-center justify-between rounded-lg border px-2.5 py-1 text-sm">
        <span className="flex items-center gap-2 truncate font-medium">
          <Check className="text-primary size-4" />
          {nilai.nama}
        </span>
        <Button
          variant="ghost"
          size="icon-xs"
          aria-label="Ganti pelanggan"
          onClick={() => ubah(null)}
        >
          <X />
        </Button>
      </div>
    );
  }

  return (
    <div className="relative">
      <Input
        aria-label="Cari pelanggan"
        placeholder="Cari nama atau telepon"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onFocus={() => setFokus(true)}
        onBlur={() => setTimeout(() => setFokus(false), 150)}
      />
      {fokus && (
        <ul className="bg-popover absolute z-20 mt-1 max-h-56 w-full overflow-auto rounded-lg border p-1 text-sm shadow-md">
          {hasil.data?.results.map((p) => (
            <li key={p.id}>
              <button
                type="button"
                className="hover:bg-muted w-full rounded px-2 py-1.5 text-left"
                onClick={() => {
                  ubah(p);
                  setQ("");
                }}
              >
                {p.nama}
                {p.telepon && <span className="text-muted-foreground"> · {p.telepon}</span>}
              </button>
            </li>
          ))}
          {hasil.data?.results.length === 0 && (
            <li className="text-muted-foreground px-2 py-1.5">Tidak ditemukan.</li>
          )}
        </ul>
      )}
    </div>
  );
}
