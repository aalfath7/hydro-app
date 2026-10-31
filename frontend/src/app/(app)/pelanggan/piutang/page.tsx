"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { useMemo, useState } from "react";

import { Filter, Halaman, Medan, PesanGalat, Pilih, TabelData, WajibIzin } from "@/components/bagian";
import { KOLOM_TAGIHAN } from "@/components/kolom-transaksi";
import { useDaftar } from "@/lib/kait";
import type { Transaksi } from "@/lib/tipe";

function Isi() {
  const [status, setStatus] = useState("belum_lunas");
  const daftar = useDaftar<Transaksi>("/api/transaksi/", { status_bayar: status });
  const kolom = useMemo<ColumnDef<Transaksi, unknown>[]>(
    () => [
      KOLOM_TAGIHAN[0],
      { header: "Pelanggan", accessorKey: "pelanggan_nama" },
      ...KOLOM_TAGIHAN.slice(1),
    ],
    [],
  );
  return (
    <Halaman judul="Piutang" keterangan="Buka nota untuk mencatat pelunasan.">
      <Filter>
        <Medan label="Tampilkan" className="w-44">
          <Pilih value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="belum_lunas">Semua belum lunas</option>
            <option value="jatuh_tempo">Lewat jatuh tempo</option>
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
          kosong="Tidak ada piutang."
        />
      )}
    </Halaman>
  );
}

export default function HalamanPiutang() {
  return (
    <WajibIzin izin="kelola_transaksi">
      <Isi />
    </WajibIzin>
  );
}
