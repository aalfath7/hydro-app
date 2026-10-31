import { AlertTriangle, CheckCircle2, Clock, XCircle } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

type Nada = "aman" | "waspada" | "bahaya" | "netral";

const GAYA: Record<Nada, string> = {
  aman: "bg-emerald-50 text-emerald-800 border-emerald-200",
  waspada: "bg-amber-50 text-amber-800 border-amber-200",
  bahaya: "bg-red-50 text-red-800 border-red-200",
  netral: "bg-slate-100 text-slate-700 border-slate-200",
};

const IKON: Record<Nada, ReactNode> = {
  aman: <CheckCircle2 className="size-3" />,
  waspada: <AlertTriangle className="size-3" />,
  bahaya: <XCircle className="size-3" />,
  netral: <Clock className="size-3" />,
};

const PETA: Record<string, [Nada, string]> = {
  aman: ["aman", "Aman"],
  menipis: ["waspada", "Menipis"],
  habis: ["bahaya", "Habis"],
  hampir: ["waspada", "Hampir kedaluwarsa"],
  kedaluwarsa: ["bahaya", "Kedaluwarsa"],
  lunas: ["aman", "Lunas"],
  tempo: ["waspada", "Tempo"],
  jatuh_tempo: ["bahaya", "Jatuh tempo"],
  dibatalkan: ["netral", "Dibatalkan"],
  selesai: ["aman", "Selesai"],
  menunggu_batal: ["waspada", "Menunggu pembatalan"],
  menunggu: ["waspada", "Menunggu persetujuan"],
  disetujui: ["aman", "Disetujui"],
  ditolak: ["netral", "Ditolak"],
  aktif: ["aman", "Aktif"],
  nonaktif: ["netral", "Nonaktif"],
};

export function Status({ nilai }: { nilai: string }) {
  const [nada, label] = PETA[nilai] ?? ["netral", nilai];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium whitespace-nowrap",
        GAYA[nada],
      )}
    >
      {IKON[nada]}
      {label}
    </span>
  );
}
