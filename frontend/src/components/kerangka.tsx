"use client";

import { useQueryClient } from "@tanstack/react-query";
import {
  Boxes,
  LayoutDashboard,
  LogOut,
  Menu,
  Package,
  PlusCircle,
  Receipt,
  Settings,
  ShieldCheck,
  BarChart3,
  Users,
  Droplets,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ComponentType, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { panggilAuth } from "@/lib/api";
import { useSesi } from "@/lib/kait";
import { cn } from "@/lib/utils";

type Tautan = { label: string; href: string; izin: string };
type Grup = { label: string; ikon: ComponentType<{ className?: string }>; tautan: Tautan[] };

const MENU: Grup[] = [
  {
    label: "Dasbor",
    ikon: LayoutDashboard,
    tautan: [{ label: "Ringkasan", href: "/", izin: "lihat_produk" }],
  },
  {
    label: "Produk",
    ikon: Package,
    tautan: [
      { label: "Daftar produk", href: "/produk", izin: "lihat_produk" },
      { label: "Kategori", href: "/produk/kategori", izin: "lihat_produk" },
    ],
  },
  {
    label: "Pembelian",
    ikon: Receipt,
    tautan: [
      { label: "Transaksi baru", href: "/pembelian/baru", izin: "kelola_transaksi" },
      { label: "Riwayat", href: "/pembelian", izin: "kelola_transaksi" },
      { label: "Retur", href: "/pembelian/retur", izin: "kelola_transaksi" },
    ],
  },
  {
    label: "Pelanggan",
    ikon: Users,
    tautan: [
      { label: "Daftar pelanggan", href: "/pelanggan", izin: "kelola_transaksi" },
      { label: "Piutang", href: "/pelanggan/piutang", izin: "kelola_transaksi" },
    ],
  },
  {
    label: "Stok",
    ikon: Boxes,
    tautan: [
      { label: "Stok terkini", href: "/stok", izin: "kelola_stok" },
      { label: "Barang masuk", href: "/stok/barang-masuk", izin: "kelola_stok" },
      { label: "Batch", href: "/stok/batch", izin: "kelola_stok" },
      { label: "Stok opname", href: "/stok/opname", izin: "kelola_stok" },
    ],
  },
  {
    label: "Laporan",
    ikon: BarChart3,
    tautan: [{ label: "Semua laporan", href: "/laporan", izin: "lihat_laporan" }],
  },
  {
    label: "Pengaturan",
    ikon: Settings,
    tautan: [
      { label: "Pengguna", href: "/pengaturan/pengguna", izin: "kelola_pengguna" },
      { label: "Peran", href: "/pengaturan/peran", izin: "kelola_pengguna" },
      { label: "Log aktivitas", href: "/pengaturan/log", izin: "kelola_pengguna" },
    ],
  },
];

const bersihkan = (jalur: string) => (jalur.length > 1 ? jalur.replace(/\/$/, "") : jalur);

function Navigasi({ jalur, tutup }: { jalur: string; tutup: () => void }) {
  const { punya } = useSesi();
  return (
    <nav className="space-y-4 p-3 text-sm">
      {MENU.map((grup) => {
        const tampil = grup.tautan.filter((t) => punya(t.izin));
        if (!tampil.length) return null;
        const Ikon = grup.ikon;
        return (
          <div key={grup.label}>
            <div className="text-muted-foreground mb-1 flex items-center gap-2 px-2 text-xs font-medium">
              <Ikon className="size-3.5" />
              {grup.label}
            </div>
            {tampil.map((t) => (
              <Link
                key={t.href}
                href={t.href}
                onClick={tutup}
                aria-current={jalur === t.href ? "page" : undefined}
                className={cn(
                  "hover:bg-muted block rounded-md px-2 py-1.5",
                  jalur === t.href && "bg-primary/10 text-primary font-medium",
                )}
              >
                {t.label}
              </Link>
            ))}
          </div>
        );
      })}
    </nav>
  );
}

export function Kerangka({ children }: { children: ReactNode }) {
  const { memuat, pengguna, punya } = useSesi();
  const router = useRouter();
  const klien = useQueryClient();
  const jalur = bersihkan(usePathname());
  const [menuTerbuka, setMenuTerbuka] = useState(false);

  const perlu2fa = !!pengguna && pengguna.wajib_2fa && !pengguna.punya_2fa;

  useEffect(() => {
    if (memuat) return;
    if (!pengguna) router.replace("/login/");
    else if (perlu2fa && jalur !== "/keamanan") router.replace("/keamanan/");
  }, [memuat, pengguna, perlu2fa, jalur, router]);

  async function keluar() {
    await panggilAuth("DELETE", "/auth/session");
    klien.clear();
    location.href = "/login/";
  }

  if (memuat || !pengguna) {
    return (
      <div className="p-6">
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <aside
        className={cn(
          "bg-sidebar fixed inset-y-0 left-0 z-40 w-60 -translate-x-full overflow-y-auto border-r transition-transform lg:static lg:translate-x-0",
          menuTerbuka && "translate-x-0",
        )}
      >
        <div className="flex h-14 items-center justify-between border-b px-4">
          <Link href="/" className="text-primary flex items-center gap-2 font-semibold">
            <Droplets className="size-5" />
            Hydro
          </Link>
          <Button
            variant="ghost"
            size="icon-sm"
            className="lg:hidden"
            aria-label="Tutup menu"
            onClick={() => setMenuTerbuka(false)}
          >
            <X />
          </Button>
        </div>
        {!perlu2fa && <Navigasi jalur={jalur} tutup={() => setMenuTerbuka(false)} />}
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="bg-background sticky top-0 z-30 flex h-14 items-center gap-2 border-b px-4">
          <Button
            variant="ghost"
            size="icon-sm"
            className="lg:hidden"
            aria-label="Buka menu"
            onClick={() => setMenuTerbuka(true)}
          >
            <Menu />
          </Button>
          <div className="flex-1" />
          {punya("kelola_transaksi") && !perlu2fa && (
            <Button render={<Link href="/pembelian/baru" />} nativeButton={false}>
              <PlusCircle />
              Transaksi baru
            </Button>
          )}
          <div className="hidden text-right text-xs leading-tight sm:block">
            <div className="font-medium">{pengguna.nama || pengguna.username}</div>
            <div className="text-muted-foreground">{pengguna.peran_nama}</div>
          </div>
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label="Keamanan akun"
            render={<Link href="/keamanan" />}
            nativeButton={false}
          >
            <ShieldCheck />
          </Button>
          <Button variant="ghost" size="icon-sm" aria-label="Keluar" onClick={keluar}>
            <LogOut />
          </Button>
        </header>
        <main className="flex-1 p-4 lg:p-6">{children}</main>
      </div>
    </div>
  );
}
