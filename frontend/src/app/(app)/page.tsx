"use client";

import { useQuery } from "@tanstack/react-query";
import { CalendarClock, Package } from "lucide-react";
import Link from "next/link";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Halaman, PesanGalat, WajibIzin } from "@/components/bagian";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { angka, rupiah, tanggal } from "@/lib/format";
import type { Dasbor } from "@/lib/tipe";

function Tile({
  label,
  nilai,
  href,
}: {
  label: string;
  nilai: string | number;
  href?: string;
}) {
  const isi = (
    <Card className="hover:border-primary/40 h-full transition-colors">
      <CardContent>
        <div className="text-muted-foreground text-sm">{label}</div>
        <div className="mt-1 text-2xl font-semibold tabular-nums">{nilai}</div>
      </CardContent>
    </Card>
  );
  return href ? <Link href={href}>{isi}</Link> : isi;
}

const ringkas = new Intl.NumberFormat("id-ID", { notation: "compact" });
const hariBulan = (t: string) =>
  new Date(`${t}T00:00:00`).toLocaleDateString("id-ID", { day: "numeric", month: "short" });

function GrafikTren({ data }: { data: NonNullable<Dasbor["tren"]> }) {
  const titik = data.map((d) => ({ tanggal: d.tanggal, neto: Number(d.neto) }));
  return (
    <>
      <div className="h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={titik} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--border)" />
            <XAxis
              dataKey="tanggal"
              tickFormatter={hariBulan}
              tickLine={false}
              axisLine={false}
              fontSize={12}
              minTickGap={24}
              stroke="var(--muted-foreground)"
            />
            <YAxis
              tickFormatter={(v: number) => ringkas.format(v)}
              tickLine={false}
              axisLine={false}
              fontSize={12}
              width={44}
              stroke="var(--muted-foreground)"
            />
            <Tooltip
              cursor={{ stroke: "var(--muted-foreground)", strokeDasharray: "3 3" }}
              formatter={(v) => [rupiah(Number(v)), "Penjualan neto"]}
              labelFormatter={(l) => tanggal(String(l))}
            />
            <Line
              type="monotone"
              dataKey="neto"
              stroke="var(--chart-1)"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <details className="mt-2 text-sm">
        <summary className="text-muted-foreground cursor-pointer">Lihat sebagai tabel</summary>
        <table className="mt-2 w-full">
          <tbody>
            {titik.map((t) => (
              <tr key={t.tanggal} className="border-t">
                <td className="py-1">{tanggal(t.tanggal)}</td>
                <td className="py-1 text-right tabular-nums">{rupiah(t.neto)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </>
  );
}

function DaftarRingkas({
  judul,
  ikon,
  kosong,
  baris,
}: {
  judul: string;
  ikon: React.ReactNode;
  kosong: string;
  baris: { kunci: number; kiri: string; bawah?: string; kanan: string; href?: string }[];
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          {ikon}
          {judul}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {baris.length === 0 ? (
          <p className="text-muted-foreground text-sm">{kosong}</p>
        ) : (
          <ul className="divide-y text-sm">
            {baris.map((b) => (
              <li key={b.kunci} className="flex items-center justify-between gap-3 py-2">
                <div className="min-w-0">
                  <div className="truncate font-medium">
                    {b.href ? <Link href={b.href}>{b.kiri}</Link> : b.kiri}
                  </div>
                  {b.bawah && <div className="text-muted-foreground text-xs">{b.bawah}</div>}
                </div>
                <div className="shrink-0 tabular-nums">{b.kanan}</div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

function Isi() {
  const { data, error, isLoading } = useQuery({
    queryKey: ["dasbor"],
    queryFn: () => api.get<Dasbor>("/api/dasbor/"),
  });
  if (isLoading) return <Skeleton className="h-64 w-full" />;
  if (error || !data) return <PesanGalat galat={error} />;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {data.penjualan_hari_ini !== null && (
          <Tile label="Penjualan hari ini" nilai={rupiah(data.penjualan_hari_ini)} href="/laporan" />
        )}
        {data.jumlah_transaksi_hari_ini !== null && (
          <Tile
            label="Transaksi hari ini"
            nilai={angka(data.jumlah_transaksi_hari_ini)}
            href="/pembelian"
          />
        )}
        {data.total_piutang !== null && (
          <Tile label="Total piutang" nilai={rupiah(data.total_piutang)} href="/pelanggan/piutang" />
        )}
        {data.tagihan_jatuh_tempo !== null && (
          <Tile
            label="Tagihan jatuh tempo"
            nilai={angka(data.tagihan_jatuh_tempo)}
            href="/pelanggan/piutang"
          />
        )}
        <Tile label="Produk habis" nilai={angka(data.stok_habis)} />
        {!!data.pembatalan_menunggu && (
          <Tile
            label="Pembatalan menunggu"
            nilai={angka(data.pembatalan_menunggu)}
            href="/pembelian?status=menunggu_batal"
          />
        )}
        {!!data.opname_menunggu && (
          <Tile label="Opname menunggu" nilai={angka(data.opname_menunggu)} href="/stok/opname" />
        )}
      </div>

      {data.tren && (
        <div className="grid gap-4 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="text-base">Penjualan neto 14 hari terakhir</CardTitle>
            </CardHeader>
            <CardContent>
              <GrafikTren data={data.tren} />
            </CardContent>
          </Card>
          <DaftarRingkas
            judul="Produk terlaris 30 hari"
            ikon={<Package className="size-4" />}
            kosong="Belum ada penjualan."
            baris={(data.terlaris ?? []).map((t) => ({
              kunci: t.produk,
              kiri: t.nama,
              kanan: `${angka(t.botol_terjual)} botol`,
              href: `/produk/detail?id=${t.produk}`,
            }))}
          />
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <DaftarRingkas
          judul="Stok menipis"
          ikon={<Package className="size-4" />}
          kosong="Semua stok aman."
          baris={data.stok_menipis.map((p) => ({
            kunci: p.id,
            kiri: p.nama,
            kanan: p.stok_teks,
            href: `/produk/detail?id=${p.id}`,
          }))}
        />
        <DaftarRingkas
          judul="Hampir kedaluwarsa"
          ikon={<CalendarClock className="size-4" />}
          kosong="Tidak ada batch yang hampir kedaluwarsa."
          baris={data.hampir_kedaluwarsa.map((b) => ({
            kunci: b.id,
            kiri: b.produk_nama,
            bawah: `Batch ${b.nomor_batch} · ${tanggal(b.kedaluwarsa)}`,
            kanan: b.stok_teks,
          }))}
        />
      </div>
    </div>
  );
}

export default function HalamanDasbor() {
  return (
    <Halaman judul="Dasbor" keterangan="Hal yang perlu ditindak hari ini.">
      <WajibIzin izin="lihat_produk">
        <Isi />
      </WajibIzin>
    </Halaman>
  );
}
