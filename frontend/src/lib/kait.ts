"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { api, pesanGalat } from "./api";
import type { Halaman, SesiPengguna, Sesi } from "./tipe";

export function useTunda<T>(nilai: T, jeda = 300): T {
  const [tertunda, setTertunda] = useState(nilai);
  useEffect(() => {
    const t = setTimeout(() => setTertunda(nilai), jeda);
    return () => clearTimeout(t);
  }, [nilai, jeda]);
  return tertunda;
}

type Param = Record<string, string | number | undefined>;

export function useDaftar<T>(url: string, param: Param = {}) {
  const [halaman, setHalaman] = useState(1);
  const kunciParam = JSON.stringify(param);
  useEffect(() => setHalaman(1), [kunciParam]);
  const query = useQuery({
    queryKey: [url, param, halaman],
    queryFn: () => api.get<Halaman<T>>(url, { ...param, page: halaman }),
    placeholderData: keepPreviousData,
  });
  return { ...query, halaman, setHalaman };
}

export function useAksi<V, H = unknown>(
  fungsi: (nilai: V) => Promise<H>,
  opsi: { sukses?: string; setelah?: (hasil: H) => void } = {},
) {
  const klien = useQueryClient();
  return useMutation({
    mutationFn: fungsi,
    onSuccess: (hasil) => {
      klien.invalidateQueries();
      if (opsi.sukses) toast.success(opsi.sukses);
      opsi.setelah?.(hasil);
    },
    onError: (galat) => {
      toast.error(pesanGalat(galat));
    },
  });
}

export function useSesi() {
  const query = useQuery({
    queryKey: ["sesi"],
    queryFn: () => api.get<Sesi>("/api/auth/sesi/"),
    staleTime: 60_000,
  });
  const pengguna: SesiPengguna | null = query.data?.pengguna ?? null;
  return {
    memuat: query.isLoading,
    pengguna,
    punya: (izin: string) => pengguna?.izin.includes(izin) ?? false,
  };
}
