export type Rincian = unknown;

export class ApiError extends Error {
  constructor(
    public status: number,
    public kode: string,
    pesan: string,
    public rincian: Rincian = null,
  ) {
    super(pesan);
  }
}

function tokenCsrf(): string {
  const baris = document.cookie.split("; ").find((c) => c.startsWith("csrftoken="));
  return baris ? decodeURIComponent(baris.split("=")[1]) : "";
}

type Param = Record<string, string | number | undefined | null>;

export function denganParam(url: string, param?: Param): string {
  if (!param) return url;
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(param)) {
    if (v !== undefined && v !== null && v !== "") q.set(k, String(v));
  }
  const teks = q.toString();
  return teks ? `${url}?${teks}` : url;
}

async function minta<T>(metode: string, url: string, body?: unknown, param?: Param): Promise<T> {
  const berkas = body instanceof FormData;
  const respons = await fetch(denganParam(url, param), {
    method: metode,
    credentials: "same-origin",
    headers: {
      ...(body && !berkas ? { "Content-Type": "application/json" } : {}),
      ...(metode !== "GET" ? { "X-CSRFToken": tokenCsrf() } : {}),
    },
    body: berkas ? body : body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (respons.status === 204) return undefined as T;
  const data = await respons.json().catch(() => null);
  if (respons.ok) return data as T;

  if (respons.status === 401 && !location.pathname.startsWith("/login")) {
    location.href = "/login/";
  }
  if (data?.kode === "wajib_2fa" && !location.pathname.startsWith("/keamanan")) {
    location.href = "/keamanan/";
  }
  throw new ApiError(
    respons.status,
    data?.kode ?? "galat",
    data?.pesan ?? "Terjadi kesalahan di server. Coba lagi.",
    data?.rincian ?? null,
  );
}

export const api = {
  get: <T>(url: string, param?: Param) => minta<T>("GET", url, undefined, param),
  post: <T>(url: string, body?: unknown) => minta<T>("POST", url, body ?? {}),
  patch: <T>(url: string, body: unknown) => minta<T>("PATCH", url, body),
};

export function pesanGalat(galat: unknown): string {
  if (!(galat instanceof ApiError)) return "Tidak bisa menghubungi server.";
  if (galat.kode === "stok_tidak_cukup" && Array.isArray(galat.rincian)) {
    const daftar = galat.rincian as { nama: string; diminta: number; tersedia: number }[];
    return daftar
      .map((r) => `Stok ${r.nama} kurang: diminta ${r.diminta}, tersedia ${r.tersedia} botol.`)
      .join(" ");
  }
  if (galat.kode === "validasi" && galat.rincian && typeof galat.rincian === "object") {
    const pesan = Object.values(galat.rincian as Record<string, unknown>).flat(3);
    const teks = pesan.filter((p) => typeof p === "string");
    if (teks.length) return teks.join(" ");
  }
  return galat.message;
}

// allauth headless memakai format balasan sendiri, dan 401 di sini bagian normal alur login.
const BASIS_AUTH = "/api/_allauth/browser/v1";

export type BalasanAuth = {
  status: number;
  data?: Record<string, unknown>;
  meta?: Record<string, unknown>;
  errors?: { message: string; param?: string }[];
};

export async function panggilAuth(
  metode: string,
  jalur: string,
  body?: unknown,
): Promise<BalasanAuth> {
  const respons = await fetch(`${BASIS_AUTH}${jalur}`, {
    method: metode,
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": tokenCsrf(),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const isi = await respons.json().catch(() => ({}));
  return { ...isi, status: respons.status };
}
