"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Medan } from "@/components/bagian";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { useAksi } from "@/lib/kait";
import type { Pelanggan } from "@/lib/tipe";

const skema = z.object({
  nama: z.string().min(1, "Nama wajib diisi"),
  telepon: z.string(),
  alamat: z.string(),
  catatan: z.string(),
});
type Form = z.infer<typeof skema>;

export function DialogPelanggan({
  buka,
  ubah,
  awal,
  setelah,
}: {
  buka: boolean;
  ubah: (b: boolean) => void;
  awal?: Pelanggan;
  setelah?: (p: Pelanggan) => void;
}) {
  const form = useForm<Form>({
    resolver: zodResolver(skema),
    defaultValues: { nama: "", telepon: "", alamat: "", catatan: "" },
  });
  useEffect(() => {
    form.reset({
      nama: awal?.nama ?? "",
      telepon: awal?.telepon ?? "",
      alamat: awal?.alamat ?? "",
      catatan: awal?.catatan ?? "",
    });
  }, [awal, form, buka]);

  const simpan = useAksi(
    (d: Form) =>
      awal
        ? api.patch<Pelanggan>(`/api/pelanggan/${awal.id}/`, d)
        : api.post<Pelanggan>("/api/pelanggan/", d),
    {
      sukses: "Pelanggan disimpan.",
      setelah: (p) => {
        ubah(false);
        setelah?.(p);
      },
    },
  );

  return (
    <Dialog open={buka} onOpenChange={ubah}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{awal ? "Ubah pelanggan" : "Pelanggan baru"}</DialogTitle>
        </DialogHeader>
        <form
          id="form-pelanggan"
          className="grid gap-3"
          onSubmit={form.handleSubmit((d) => simpan.mutate(d))}
        >
          <Medan label="Nama" galat={form.formState.errors.nama?.message}>
            <Input {...form.register("nama")} />
          </Medan>
          <Medan label="Telepon">
            <Input inputMode="tel" {...form.register("telepon")} />
          </Medan>
          <Medan label="Alamat">
            <Textarea {...form.register("alamat")} />
          </Medan>
          <Medan label="Catatan">
            <Textarea {...form.register("catatan")} />
          </Medan>
        </form>
        <DialogFooter>
          <Button type="submit" form="form-pelanggan" disabled={simpan.isPending}>
            Simpan
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
