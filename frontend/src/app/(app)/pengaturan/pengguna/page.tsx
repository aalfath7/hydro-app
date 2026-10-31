"use client";

import { useQuery } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { Plus } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Halaman, Medan, PesanGalat, Pilih, TabelData, WajibIzin } from "@/components/bagian";
import { Status } from "@/components/status";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { waktu } from "@/lib/format";
import { useAksi, useDaftar } from "@/lib/kait";
import type { Pengguna, Peran } from "@/lib/tipe";

function usePeran() {
  return useQuery({ queryKey: ["peran"], queryFn: () => api.get<Peran[]>("/api/peran/") });
}

function DialogBaru({ buka, ubah }: { buka: boolean; ubah: (b: boolean) => void }) {
  const peran = usePeran();
  const [isian, setIsian] = useState({ username: "", nama: "", peran: "", password: "" });
  const atur = (k: keyof typeof isian, v: string) => setIsian((i) => ({ ...i, [k]: v }));
  const simpan = useAksi(() => api.post("/api/pengguna/", isian), {
    sukses: "Pengguna dibuat.",
    setelah: () => {
      setIsian({ username: "", nama: "", peran: "", password: "" });
      ubah(false);
    },
  });
  return (
    <Dialog open={buka} onOpenChange={ubah}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Pengguna baru</DialogTitle>
        </DialogHeader>
        <div className="grid gap-3">
          <Medan label="Nama pengguna">
            <Input
              autoComplete="off"
              value={isian.username}
              onChange={(e) => atur("username", e.target.value)}
            />
          </Medan>
          <Medan label="Nama lengkap">
            <Input value={isian.nama} onChange={(e) => atur("nama", e.target.value)} />
          </Medan>
          <Medan label="Peran">
            <Pilih value={isian.peran} onChange={(e) => atur("peran", e.target.value)}>
              <option value="">Pilih peran</option>
              {peran.data?.map((p) => (
                <option key={p.kode} value={p.kode}>
                  {p.nama}
                </option>
              ))}
            </Pilih>
          </Medan>
          <Medan label="Password awal" bantuan="Minimal 10 karakter.">
            <Input
              type="password"
              autoComplete="new-password"
              value={isian.password}
              onChange={(e) => atur("password", e.target.value)}
            />
          </Medan>
        </div>
        <DialogFooter>
          <Button
            disabled={!isian.username || !isian.peran || !isian.password || simpan.isPending}
            onClick={() => simpan.mutate(undefined)}
          >
            Simpan
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function DialogUbah({ akun, tutup }: { akun: Pengguna | null; tutup: () => void }) {
  const peran = usePeran();
  const [nama, setNama] = useState("");
  const [idPeran, setIdPeran] = useState("");
  const [aktif, setAktif] = useState(true);
  const [password, setPassword] = useState("");

  useEffect(() => {
    if (!akun) return;
    setNama(akun.nama ?? "");
    setIdPeran(akun.peran ?? "");
    setAktif(akun.aktif ?? true);
    setPassword("");
  }, [akun]);

  const simpan = useAksi(
    () => api.patch(`/api/pengguna/${akun?.id}/`, { nama, peran: idPeran, aktif }),
    { sukses: "Pengguna diperbarui.", setelah: tutup },
  );
  const aturPassword = useAksi(
    () => api.post(`/api/pengguna/${akun?.id}/atur-password/`, { password }),
    { sukses: "Password diatur ulang.", setelah: () => setPassword("") },
  );
  const reset2fa = useAksi(() => api.post(`/api/pengguna/${akun?.id}/reset-2fa/`), {
    sukses: "2FA direset.",
    setelah: tutup,
  });

  return (
    <Dialog open={!!akun} onOpenChange={(b) => !b && tutup()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{akun?.username}</DialogTitle>
        </DialogHeader>
        <div className="grid gap-3">
          <Medan label="Nama lengkap">
            <Input value={nama} onChange={(e) => setNama(e.target.value)} />
          </Medan>
          <Medan label="Peran">
            <Pilih value={idPeran} onChange={(e) => setIdPeran(e.target.value)}>
              {peran.data?.map((p) => (
                <option key={p.kode} value={p.kode}>
                  {p.nama}
                </option>
              ))}
            </Pilih>
          </Medan>
          <div className="flex items-center gap-2">
            <Checkbox
              id="aktif"
              checked={aktif}
              onCheckedChange={(c) => setAktif(c === true)}
            />
            <Label htmlFor="aktif">Akun aktif</Label>
          </div>
          <Button disabled={simpan.isPending} onClick={() => simpan.mutate(undefined)}>
            Simpan perubahan
          </Button>
          <div className="grid gap-2 border-t pt-3">
            <Medan label="Password baru">
              <Input
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </Medan>
            <Button
              variant="outline"
              disabled={!password || aturPassword.isPending}
              onClick={() => aturPassword.mutate(undefined)}
            >
              Atur ulang password
            </Button>
          </div>
        </div>
        {akun?.punya_2fa && (
          <DialogFooter>
            <Button
              variant="destructive"
              disabled={reset2fa.isPending}
              onClick={() => reset2fa.mutate(undefined)}
            >
              Reset 2FA
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
}

function Isi() {
  const [baru, setBaru] = useState(false);
  const [dipilih, setDipilih] = useState<Pengguna | null>(null);
  const daftar = useDaftar<Pengguna>("/api/pengguna/");
  const kolom = useMemo<ColumnDef<Pengguna, unknown>[]>(
    () => [
      { header: "Nama pengguna", accessorKey: "username" },
      { header: "Nama", accessorKey: "nama" },
      { header: "Peran", accessorKey: "peran_nama" },
      {
        header: "2FA",
        cell: ({ row }) => (row.original.punya_2fa ? "Aktif" : "Belum"),
      },
      { header: "Login terakhir", cell: ({ row }) => waktu(row.original.terakhir_login) },
      {
        header: "Status",
        cell: ({ row }) => <Status nilai={row.original.aktif ? "aktif" : "nonaktif"} />,
      },
      {
        id: "aksi",
        header: "",
        meta: { kanan: true },
        cell: ({ row }) => (
          <Button variant="outline" size="sm" onClick={() => setDipilih(row.original)}>
            Kelola
          </Button>
        ),
      },
    ],
    [],
  );
  return (
    <Halaman
      judul="Pengguna"
      keterangan="Akun hanya dibuat di sini, tidak ada pendaftaran publik."
      aksi={
        <Button onClick={() => setBaru(true)}>
          <Plus />
          Pengguna baru
        </Button>
      }
    >
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
        />
      )}
      <DialogBaru buka={baru} ubah={setBaru} />
      <DialogUbah akun={dipilih} tutup={() => setDipilih(null)} />
    </Halaman>
  );
}

export default function HalamanPengguna() {
  return (
    <WajibIzin izin="kelola_pengguna">
      <Isi />
    </WajibIzin>
  );
}
