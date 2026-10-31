"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { ChevronLeft, ChevronRight, Search } from "lucide-react";
import {
  cloneElement,
  isValidElement,
  Suspense,
  useId,
  type ReactNode,
  type SelectHTMLAttributes,
} from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { pesanGalat } from "@/lib/api";
import { angka } from "@/lib/format";
import { useSesi } from "@/lib/kait";
import { cn } from "@/lib/utils";

declare module "@tanstack/react-table" {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  interface ColumnMeta<TData, TValue> {
    kanan?: boolean;
  }
}

export function Halaman({
  judul,
  keterangan,
  aksi,
  children,
}: {
  judul: string;
  keterangan?: string;
  aksi?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="mx-auto w-full max-w-7xl space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">{judul}</h1>
          {keterangan && <p className="text-muted-foreground text-sm">{keterangan}</p>}
        </div>
        {aksi && <div className="flex flex-wrap items-center gap-2">{aksi}</div>}
      </div>
      {children}
    </div>
  );
}

export function Bungkus({ children }: { children: ReactNode }) {
  return <Suspense fallback={<Skeleton className="h-40 w-full" />}>{children}</Suspense>;
}

export function WajibIzin({ izin, children }: { izin: string; children: ReactNode }) {
  const { memuat, punya } = useSesi();
  if (memuat) return <Skeleton className="h-40 w-full" />;
  if (!punya(izin)) {
    return (
      <Alert>
        <AlertTitle>Tidak ada akses</AlertTitle>
        <AlertDescription>Halaman ini tidak tersedia untuk peran Anda.</AlertDescription>
      </Alert>
    );
  }
  return <>{children}</>;
}

export function PesanGalat({ galat }: { galat: unknown }) {
  return (
    <Alert variant="destructive">
      <AlertTitle>Data gagal dimuat</AlertTitle>
      <AlertDescription>{pesanGalat(galat)}</AlertDescription>
    </Alert>
  );
}

export function Medan({
  label,
  galat,
  bantuan,
  children,
  className,
}: {
  label: string;
  galat?: string;
  bantuan?: string;
  children: ReactNode;
  className?: string;
}) {
  const id = useId();
  return (
    <div className={cn("space-y-1.5", className)}>
      <Label htmlFor={id}>{label}</Label>
      {isValidElement<{ id?: string }>(children) ? cloneElement(children, { id }) : children}
      {bantuan && !galat && <p className="text-muted-foreground text-xs">{bantuan}</p>}
      {galat && <p className="text-destructive text-xs">{galat}</p>}
    </div>
  );
}

export function Pilih({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "border-input bg-background focus-visible:border-ring focus-visible:ring-ring/50 h-8 w-full rounded-lg border px-2 text-sm outline-none focus-visible:ring-3",
        className,
      )}
      {...props}
    />
  );
}

export function Cari({
  nilai,
  ubah,
  placeholder = "Cari...",
}: {
  nilai: string;
  ubah: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <div className="relative w-full sm:w-72">
      <Search className="text-muted-foreground absolute top-2 left-2.5 size-4" />
      <Input
        aria-label={placeholder}
        className="pl-8"
        placeholder={placeholder}
        value={nilai}
        onChange={(e) => ubah(e.target.value)}
      />
    </div>
  );
}

export function Filter({ children }: { children: ReactNode }) {
  return <div className="flex flex-wrap items-end gap-2">{children}</div>;
}

export function TabelData<T>({
  kolom,
  data,
  memuat,
  jumlah,
  halaman,
  ubahHalaman,
  kosong = "Belum ada data.",
  ukuran = 25,
}: {
  kolom: ColumnDef<T, unknown>[];
  data: T[] | undefined;
  memuat?: boolean;
  jumlah?: number;
  halaman?: number;
  ubahHalaman?: (h: number) => void;
  kosong?: string;
  ukuran?: number;
}) {
  const tabel = useReactTable({
    data: data ?? [],
    columns: kolom,
    getCoreRowModel: getCoreRowModel(),
  });
  const totalHalaman = jumlah ? Math.max(Math.ceil(jumlah / ukuran), 1) : 1;

  return (
    <div className="bg-card rounded-xl border">
      <Table>
        <TableHeader>
          {tabel.getHeaderGroups().map((g) => (
            <TableRow key={g.id}>
              {g.headers.map((h) => (
                <TableHead
                  key={h.id}
                  className={cn(h.column.columnDef.meta?.kanan && "text-right")}
                >
                  {flexRender(h.column.columnDef.header, h.getContext())}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {memuat && !data ? (
            <TableRow>
              <TableCell colSpan={kolom.length}>
                <Skeleton className="h-16 w-full" />
              </TableCell>
            </TableRow>
          ) : tabel.getRowModel().rows.length === 0 ? (
            <TableRow>
              <TableCell
                colSpan={kolom.length}
                className="text-muted-foreground h-24 text-center"
              >
                {kosong}
              </TableCell>
            </TableRow>
          ) : (
            tabel.getRowModel().rows.map((b) => (
              <TableRow key={b.id}>
                {b.getVisibleCells().map((s) => (
                  <TableCell
                    key={s.id}
                    className={cn(s.column.columnDef.meta?.kanan && "text-right tabular-nums")}
                  >
                    {flexRender(s.column.columnDef.cell, s.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
      {halaman !== undefined && ubahHalaman && jumlah !== undefined && jumlah > 0 && (
        <div className="text-muted-foreground flex items-center justify-between border-t px-3 py-2 text-sm">
          <span>{angka(jumlah)} data</span>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="icon-sm"
              aria-label="Halaman sebelumnya"
              disabled={halaman <= 1}
              onClick={() => ubahHalaman(halaman - 1)}
            >
              <ChevronLeft />
            </Button>
            <span className="tabular-nums">
              {halaman} / {totalHalaman}
            </span>
            <Button
              variant="outline"
              size="icon-sm"
              aria-label="Halaman berikutnya"
              disabled={halaman >= totalHalaman}
              onClick={() => ubahHalaman(halaman + 1)}
            >
              <ChevronRight />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
