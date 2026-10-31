"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { Droplets } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Medan } from "@/components/bagian";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { panggilAuth, type BalasanAuth } from "@/lib/api";
import { useSesi } from "@/lib/kait";

const skema = z.object({
  username: z.string().min(1, "Nama pengguna wajib diisi"),
  password: z.string().min(1, "Password wajib diisi"),
});
type Form = z.infer<typeof skema>;

type Alur = { id: string; is_pending?: boolean };

const butuhKode = (r: BalasanAuth) =>
  r.status === 401 &&
  ((r.data?.flows as Alur[] | undefined) ?? []).some(
    (a) => a.id === "mfa_authenticate" && a.is_pending,
  );

export default function HalamanLogin() {
  const router = useRouter();
  const klien = useQueryClient();
  const { pengguna } = useSesi();
  const [galat, setGalat] = useState("");
  const [tahap2fa, setTahap2fa] = useState(false);
  const [kode, setKode] = useState("");
  const [kirim, setKirim] = useState(false);
  const form = useForm<Form>({
    resolver: zodResolver(skema),
    defaultValues: { username: "", password: "" },
  });

  useEffect(() => {
    if (pengguna) router.replace("/");
  }, [pengguna, router]);

  async function selesai() {
    await klien.invalidateQueries({ queryKey: ["sesi"] });
    router.replace("/");
  }

  async function masuk(data: Form) {
    setGalat("");
    setKirim(true);
    try {
      const r = await panggilAuth("POST", "/auth/login", data);
      if (r.status === 200 || r.status === 409) await selesai();
      else if (butuhKode(r)) setTahap2fa(true);
      else if (r.status === 403 || r.status === 429) {
        setGalat("Terlalu banyak percobaan. Coba lagi nanti.");
      } else if (r.status === 400 && r.errors?.length) {
        setGalat("Nama pengguna atau password salah.");
      } else {
        setGalat("Server menolak permintaan ini. Hubungi admin aplikasi.");
      }
    } catch {
      setGalat("Tidak bisa menghubungi server.");
    } finally {
      setKirim(false);
    }
  }

  async function kirimKode(e: React.FormEvent) {
    e.preventDefault();
    setGalat("");
    setKirim(true);
    try {
      const r = await panggilAuth("POST", "/auth/2fa/authenticate", { code: kode.trim() });
      if (r.status === 200) await selesai();
      else if (r.status === 400 && r.errors?.length) setGalat("Kode tidak valid.");
      else setGalat("Server menolak permintaan ini. Hubungi admin aplikasi.");
    } catch {
      setGalat("Tidak bisa menghubungi server.");
    } finally {
      setKirim(false);
    }
  }

  return (
    <main className="bg-muted/40 flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="text-primary flex items-center gap-2 text-lg">
            <Droplets className="size-5" />
            Hydro
          </CardTitle>
          <p className="text-muted-foreground text-sm">
            {tahap2fa
              ? "Masukkan kode dari aplikasi autentikator atau kode pemulihan."
              : "Masuk dengan akun karyawan."}
          </p>
        </CardHeader>
        <CardContent className="space-y-3">
          {galat && (
            <Alert variant="destructive">
              <AlertDescription>{galat}</AlertDescription>
            </Alert>
          )}
          {tahap2fa ? (
            <form onSubmit={kirimKode} className="space-y-3">
              <Medan label="Kode 2FA">
                <Input
                  autoFocus
                  autoComplete="one-time-code"
                  inputMode="text"
                  value={kode}
                  onChange={(e) => setKode(e.target.value)}
                />
              </Medan>
              <Button type="submit" className="w-full" disabled={kirim || !kode.trim()}>
                Verifikasi
              </Button>
            </form>
          ) : (
            <form onSubmit={form.handleSubmit(masuk)} className="space-y-3">
              <Medan label="Nama pengguna" galat={form.formState.errors.username?.message}>
                <Input autoFocus autoComplete="username" {...form.register("username")} />
              </Medan>
              <Medan label="Password" galat={form.formState.errors.password?.message}>
                <Input
                  type="password"
                  autoComplete="current-password"
                  {...form.register("password")}
                />
              </Medan>
              <Button type="submit" className="w-full" disabled={kirim}>
                Masuk
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </main>
  );
}
