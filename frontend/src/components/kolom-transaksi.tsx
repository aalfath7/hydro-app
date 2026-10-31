"use client";

import type { ColumnDef } from "@tanstack/react-table";
import Link from "next/link";

import { Status } from "@/components/status";
import { rupiah, tanggal, waktu } from "@/lib/format";
import type { Transaksi } from "@/lib/tipe";

export const KOLOM_TAGIHAN: ColumnDef<Transaksi, unknown>[] = [
  {
    header: "Nota",
    cell: ({ row: { original: t } }) => (
      <Link href={`/pembelian/detail?id=${t.id}`} className="text-primary font-medium">
        {t.nomor}
      </Link>
    ),
  },
  { header: "Tanggal", cell: ({ row }) => waktu(row.original.tanggal) },
  { header: "Jatuh tempo", cell: ({ row }) => tanggal(row.original.jatuh_tempo) },
  { header: "Total", meta: { kanan: true }, cell: ({ row }) => rupiah(row.original.total) },
  {
    header: "Sisa",
    meta: { kanan: true },
    cell: ({ row }) => rupiah(row.original.sisa_tagihan),
  },
  { header: "Status", cell: ({ row }) => <Status nilai={row.original.status_bayar} /> },
];
