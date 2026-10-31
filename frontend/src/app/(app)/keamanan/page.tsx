"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { QRCodeSVG } from "qrcode.react";
import { useState } from "react";
import { toast } from "sonner";

import { Halaman, Medan } from "@/components/bagian";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { panggilAuth } from "@/lib/api";
import { useSesi } from "@/lib/kait";

function pesanAuth(r: { errors?: { message: string }[] }, cadangan: string) {
  return r.errors?.[0]?.message ?? cadangan;
}

function Aktifkan2fa({ wajib }: { wajib: boolean }) {
  const klien = useQueryClient();
  const [password, setPassword] = useState("");
  const [kode, setKode] = useState("");
  const [kodePemulihan, setKodePemulihan] = useState<string[] | null>(null);
  const [kirim, setKirim] = useState(false);

  const totp = useQuery({
    queryKey: ["totp-baru"],
    queryFn: async () => {
      const r = await panggilAuth("GET", "/account/authenticators/totp");
      return r.meta as { secret: string; totp_url: string };
    },
    enabled: kodePemulihan === null,
    staleTime: Infinity,
  });

  async function aktifkan(e: React.FormEvent) {
    e.preventDefault();
    setKirim(true);
    try {
      const ulang = await panggilAuth("POST", "/auth/reauthenticate", { password });
      if (ulang.status !== 200) {
        toast.error("Password salah.");
        return;
      }
      const r = await panggilAuth("POST", "/account/authenticators/totp", { code: kode.trim() });
      if (r.status !== 200) {
        toast.error(pesanAuth(r, "Kode tidak valid."));
        return;
      }
      const pemulihan = await panggilAuth("GET", "/account/authenticators/recovery-codes");
      setKodePemulihan((pemulihan.data?.unused_codes as string[]) ?? []);
    } finally {
      setKirim(false);
    }
  }

  if (kodePemulihan) {
    return (
      <div className="space-y-3">
        <Alert>
          <AlertTitle>2FA aktif. Simpan kode pemulihan ini</AlertTitle>
          <AlertDescription>
            Setiap kode hanya berlaku sekali, dan dipakai kalau perangkat autentikator hilang.
          </AlertDescription>
        </Alert>
        <ul className="grid grid-cols-2 gap-1 font-mono text-sm">
          {kodePemulihan.map((k) => (
            <li key={k}>{k}</li>
          ))}
        </ul>
        <Button onClick={() => klien.invalidateQueries({ queryKey: ["sesi"] })}>
          Saya sudah menyimpannya
        </Button>
      </div>
    );
  }

  return (
    <form onSubmit={aktifkan} className="space-y-4">
      {wajib && (
        <Alert>
          <AlertTitle>2FA wajib untuk pemilik/manajer</AlertTitle>
          <AlertDescription>Aktifkan dulu untuk memakai aplikasi.</AlertDescription>
        </Alert>
      )}
      {totp.data && (
        <div className="flex flex-wrap items-center gap-4">
          <div className="rounded-lg border bg-white p-2">
            <QRCodeSVG value={totp.data.totp_url} size={148} />
          </div>
          <div className="min-w-0 text-sm">
            <p>Pindai dengan aplikasi autentikator, atau masukkan kunci ini:</p>
            <code className="break-all">{totp.data.secret}</code>
          </div>
        </div>
      )}
      <div className="grid gap-3 sm:grid-cols-2">
        <Medan label="Password Anda">
          <Input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </Medan>
        <Medan label="Kode 6 digit">
          <Input
            inputMode="numeric"
            autoComplete="one-time-code"
            value={kode}
            onChange={(e) => setKode(e.target.value)}
          />
        </Medan>
      </div>
      <Button type="submit" disabled={kirim || !password || kode.trim().length < 6}>
        Aktifkan 2FA
      </Button>
    </form>
  );
}

function GantiPassword() {
  const [lama, setLama] = useState("");
  const [baru, setBaru] = useState("");
  const [kirim, setKirim] = useState(false);

  async function simpan(e: React.FormEvent) {
    e.preventDefault();
    setKirim(true);
    try {
      const r = await panggilAuth("POST", "/account/password/change", {
        current_password: lama,
        new_password: baru,
      });
      if (r.status === 200) {
        toast.success("Password diganti.");
        setLama("");
        setBaru("");
      } else {
        toast.error(pesanAuth(r, "Password gagal diganti."));
      }
    } finally {
      setKirim(false);
    }
  }

  return (
    <form onSubmit={simpan} className="grid max-w-md gap-3">
      <Medan label="Password lama">
        <Input
          type="password"
          autoComplete="current-password"
          value={lama}
          onChange={(e) => setLama(e.target.value)}
        />
      </Medan>
      <Medan label="Password baru" bantuan="Minimal 10 karakter.">
        <Input
          type="password"
          autoComplete="new-password"
          value={baru}
          onChange={(e) => setBaru(e.target.value)}
        />
      </Medan>
      <div>
        <Button type="submit" disabled={kirim || !lama || !baru}>
          Ganti password
        </Button>
      </div>
    </form>
  );
}

export default function HalamanKeamanan() {
  const { pengguna } = useSesi();
  if (!pengguna) return null;
  return (
    <Halaman judul="Keamanan akun">
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Verifikasi dua langkah (2FA)</CardTitle>
          </CardHeader>
          <CardContent>
            {pengguna.punya_2fa ? (
              <p className="text-sm">2FA sudah aktif untuk akun ini.</p>
            ) : (
              <Aktifkan2fa wajib={pengguna.wajib_2fa} />
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Password</CardTitle>
          </CardHeader>
          <CardContent>
            <GantiPassword />
          </CardContent>
        </Card>
      </div>
    </Halaman>
  );
}
