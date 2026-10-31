const uang = new Intl.NumberFormat("id-ID", { maximumFractionDigits: 2 });
const tanggalPendek = new Intl.DateTimeFormat("id-ID", {
  day: "2-digit",
  month: "short",
  year: "numeric",
  timeZone: "Asia/Jakarta",
});
const tanggalJam = new Intl.DateTimeFormat("id-ID", {
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "Asia/Jakarta",
});

export const rupiah = (nilai: string | number | null | undefined) =>
  `Rp ${uang.format(Number(nilai ?? 0))}`;

export const angka = (nilai: number) => uang.format(nilai);

export const tanggal = (nilai: string | null | undefined) =>
  nilai ? tanggalPendek.format(new Date(nilai)) : "-";

export const waktu = (nilai: string | null | undefined) =>
  nilai ? tanggalJam.format(new Date(nilai)) : "-";

export function hariIni(selisih = 0): string {
  const d = new Date(Date.now() + selisih * 86_400_000);
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jakarta" }).format(d);
}
