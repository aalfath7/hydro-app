"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { ImageIcon, Plus, Upload } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import {
  Cari,
  Filter,
  Halaman,
  Medan,
  PesanGalat,
  Pilih,
  TabelData,
  WajibIzin,
} from "@/components/bagian";
import { Status } from "@/components/status";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { api, pesanGalat } from "@/lib/api";
import { rupiah } from "@/lib/format";
import { useAksi, useDaftar, useSesi, useTunda } from "@/lib/kait";
import type { Kategori, Produk } from "@/lib/tipe";

const uang = z.string().regex(/^\d+(\.\d{1,2})?$/, "Isi angka, contoh 3500");
const opsional = (pola: RegExp, pesan: string) =>
  z.string().refine((v) => v === "" || pola.test(v), pesan);

const skema = z
  .object({
    sku: z.string().min(1, "SKU wajib diisi"),
    nama: z.string().min(1, "Nama wajib diisi"),
    kategori: z.string().min(1, "Pilih kategori"),
    ukuran_ml: opsional(/^\d+$/, "Isi angka"),
    kemasan: z.string(),
    stok_minimum: z.string().regex(/^\d+$/, "Isi angka"),
    harga_botol: uang,
    isi_dus: opsional(/^([2-9]|\d{2,})$/, "Minimal 2"),
    harga_dus: opsional(/^\d+(\.\d{1,2})?$/, "Isi angka"),
  })
  .refine((d) => !!d.isi_dus === !!d.harga_dus, {
    path: ["harga_dus"],
    message: "Isi dus dan harga dus diisi bersamaan",
  });
type Form = z.infer<typeof skema>;

function DialogProduk({ buka, ubah }: { buka: boolean; ubah: (b: boolean) => void }) {
  const kategori = useQuery({
    queryKey: ["kategori"],
    queryFn: () => api.get<Kategori[]>("/api/kategori/"),
  });
  const form = useForm<Form>({
    resolver: zodResolver(skema),
    defaultValues: {
      sku: "",
      nama: "",
      kategori: "",
      ukuran_ml: "",
      kemasan: "",
      stok_minimum: "0",
      harga_botol: "",
      isi_dus: "",
      harga_dus: "",
    },
  });
  const simpan = useAksi(
    (d: Form) =>
      api.post("/api/produk/", {
        ...d,
        kategori: Number(d.kategori),
        ukuran_ml: d.ukuran_ml ? Number(d.ukuran_ml) : null,
        stok_minimum: Number(d.stok_minimum),
        isi_dus: d.isi_dus ? Number(d.isi_dus) : null,
        harga_dus: d.harga_dus || null,
      }),
    {
      sukses: "Produk ditambahkan.",
      setelah: () => {
        form.reset();
        ubah(false);
      },
    },
  );
  const g = form.formState.errors;

  return (
    <Dialog open={buka} onOpenChange={ubah}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Produk baru</DialogTitle>
        </DialogHeader>
        <form
          id="form-produk"
          className="grid gap-3 sm:grid-cols-2"
          onSubmit={form.handleSubmit((d) => simpan.mutate(d))}
        >
          <Medan label="SKU" galat={g.sku?.message}>
            <Input {...form.register("sku")} />
          </Medan>
          <Medan label="Kategori" galat={g.kategori?.message}>
            <Pilih {...form.register("kategori")}>
              <option value="">Pilih kategori</option>
              {kategori.data
                ?.filter((k) => k.aktif)
                .map((k) => (
                  <option key={k.id} value={k.id}>
                    {k.nama}
                  </option>
                ))}
            </Pilih>
          </Medan>
          <Medan label="Nama produk" galat={g.nama?.message} className="sm:col-span-2">
            <Input {...form.register("nama")} />
          </Medan>
          <Medan label="Ukuran (ml)" galat={g.ukuran_ml?.message}>
            <Input inputMode="numeric" {...form.register("ukuran_ml")} />
          </Medan>
          <Medan label="Kemasan" galat={g.kemasan?.message}>
            <Input placeholder="Botol, galon, gelas" {...form.register("kemasan")} />
          </Medan>
          <Medan label="Stok minimum (botol)" galat={g.stok_minimum?.message}>
            <Input inputMode="numeric" {...form.register("stok_minimum")} />
          </Medan>
          <Medan label="Harga per botol (Rp)" galat={g.harga_botol?.message}>
            <Input inputMode="decimal" {...form.register("harga_botol")} />
          </Medan>
          <Medan label="Isi per dus (botol)" galat={g.isi_dus?.message}>
            <Input inputMode="numeric" {...form.register("isi_dus")} />
          </Medan>
          <Medan label="Harga per dus (Rp)" galat={g.harga_dus?.message}>
            <Input inputMode="decimal" {...form.register("harga_dus")} />
          </Medan>
        </form>
        <DialogFooter>
          <Button type="submit" form="form-produk" disabled={simpan.isPending}>
            Simpan
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function DialogImpor({ buka, ubah }: { buka: boolean; ubah: (b: boolean) => void }) {
  const [berkas, setBerkas] = useState<File | null>(null);
  const [galat, setGalat] = useState<string | null>(null);
  const impor = useAksi(
    (f: File) => {
      const data = new FormData();
      data.append("berkas", f);
      return api.post<{ dibuat: number; dilewati: number }>("/api/produk/impor/", data);
    },
    {
      setelah: (h) => {
        toast.success(`${h.dibuat} produk dibuat, ${h.dilewati} dilewati.`);
        setBerkas(null);
        setGalat(null);
        ubah(false);
      },
    },
  );
  return (
    <Dialog open={buka} onOpenChange={ubah}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Impor produk dari Excel</DialogTitle>
        </DialogHeader>
        <p className="text-sm">
          Gunakan{" "}
          <a className="text-primary underline" href="/api/produk/template-impor/">
            template impor
          </a>
          . SKU yang sudah ada dilewati.
        </p>
        <Input
          type="file"
          accept=".xlsx"
          aria-label="Berkas Excel"
          onChange={(e) => setBerkas(e.target.files?.[0] ?? null)}
        />
        {galat && <p className="text-destructive text-sm">{galat}</p>}
        <DialogFooter>
          <Button
            disabled={!berkas || impor.isPending}
            onClick={() =>
              berkas && impor.mutate(berkas, { onError: (e) => setGalat(pesanGalat(e)) })
            }
          >
            Impor
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function Isi() {
  const { punya } = useSesi();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [kategori, setKategori] = useState("");
  const [buatBuka, setBuatBuka] = useState(false);
  const [imporBuka, setImporBuka] = useState(false);
  const qTunda = useTunda(q);

  const daftarKategori = useQuery({
    queryKey: ["kategori"],
    queryFn: () => api.get<Kategori[]>("/api/kategori/"),
  });
  const daftar = useDaftar<Produk>("/api/produk/", { q: qTunda, status, kategori });

  const kolom = useMemo<ColumnDef<Produk, unknown>[]>(
    () => [
      {
        id: "foto",
        header: "",
        cell: ({ row: { original: p } }) =>
          p.punya_foto ? (
            // Foto dilayani Django dengan cek login, bukan lewat optimizer gambar.
            // eslint-disable-next-line @next/next/no-img-element
            <img src={`/api/produk/${p.id}/foto/`} alt="" className="size-9 rounded object-cover" />
          ) : (
            <div className="bg-muted flex size-9 items-center justify-center rounded">
              <ImageIcon className="text-muted-foreground size-4" />
            </div>
          ),
      },
      {
        header: "Produk",
        cell: ({ row: { original: p } }) => (
          <div>
            <Link href={`/produk/detail?id=${p.id}`} className="text-primary font-medium">
              {p.nama}
            </Link>
            <div className="text-muted-foreground text-xs">
              {p.sku} · {p.kategori_nama}
            </div>
          </div>
        ),
      },
      { header: "Kemasan", cell: ({ row: { original: p } }) => p.kemasan || "-" },
      {
        header: "Stok",
        meta: { kanan: true },
        cell: ({ row: { original: p } }) => p.stok_teks,
      },
      {
        header: "Harga",
        meta: { kanan: true },
        cell: ({ row: { original: p } }) => (
          <div>
            {p.satuan
              .filter((s) => s.aktif)
              .map((s) => (
                <div key={s.id}>
                  {s.harga ? rupiah(s.harga) : "-"}/{s.nama}
                </div>
              ))}
          </div>
        ),
      },
      {
        header: "Status",
        cell: ({ row: { original: p } }) =>
          p.aktif ? <Status nilai={p.status_stok} /> : <Status nilai="nonaktif" />,
      },
    ],
    [],
  );

  return (
    <Halaman
      judul="Daftar produk"
      aksi={
        punya("ubah_produk") && (
          <>
            <Button variant="outline" onClick={() => setImporBuka(true)}>
              <Upload />
              Impor Excel
            </Button>
            <Button onClick={() => setBuatBuka(true)}>
              <Plus />
              Produk baru
            </Button>
          </>
        )
      }
    >
      <Filter>
        <Cari nilai={q} ubah={setQ} placeholder="Cari nama atau SKU" />
        <Pilih
          aria-label="Status stok"
          className="w-40"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="">Semua status</option>
          <option value="aman">Aman</option>
          <option value="menipis">Menipis</option>
          <option value="habis">Habis</option>
        </Pilih>
        <Pilih
          aria-label="Kategori"
          className="w-44"
          value={kategori}
          onChange={(e) => setKategori(e.target.value)}
        >
          <option value="">Semua kategori</option>
          {daftarKategori.data?.map((k) => (
            <option key={k.id} value={k.id}>
              {k.nama}
            </option>
          ))}
        </Pilih>
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
          kosong="Belum ada produk."
        />
      )}
      <DialogProduk buka={buatBuka} ubah={setBuatBuka} />
      <DialogImpor buka={imporBuka} ubah={setImporBuka} />
    </Halaman>
  );
}

export default function HalamanProduk() {
  return (
    <WajibIzin izin="lihat_produk">
      <Isi />
    </WajibIzin>
  );
}
